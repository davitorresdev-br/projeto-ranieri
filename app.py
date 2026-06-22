import os
import secrets
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
from automacao_impressora import disparar_impressao_windows
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

import banco_dados as db  # Toda a lógica de usuários, senhas e privilégios
                           # de Admin vive em banco_dados/ — não aqui.

app = Flask(__name__)
# Chave aleatória gerada a cada início. Se precisar manter o mesmo valor
# entre reinícios do servidor, defina a variável de ambiente abaixo.
app.secret_key = os.environ.get("ACALANTO_SECRET_KEY", secrets.token_hex(32))

CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": "*"
    }
})

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ID do cliente OAuth do Google Workspace. Não é um segredo (é o mesmo
# valor que já fica visível no front-end), por isso pode continuar aqui.
# O Client Secret foi removido: ele não é necessário para validar o token
# de login (fluxo usado pelo @react-oauth/google) e só representava uma
# exposição inútil dentro do código-fonte.
GOOGLE_CLIENT_ID = "314763396953-7imem6nh7na48ujfnbnb1ni79rvpcbn6.apps.googleusercontent.com"

db.init_db()

# -------------------------------------------------------------------------
# ROTAS DE AUTENTICAÇÃO
# -------------------------------------------------------------------------

@app.route('/api/login', methods=['POST'])
def login_credenciais():
    try:
        dados = request.json or {}
        usuario_digitado = dados.get('username', '').strip()
        senha_digitada = dados.get('password', '').strip()

        if not usuario_digitado or not senha_digitada:
            return jsonify({"status": "erro", "erro": "Preencha todos os campos"}), 400

        usuario = db.autenticar_local(usuario_digitado, senha_digitada)

        if not usuario:
            return jsonify({"status": "erro", "erro": "Usuário ou senha incorretos."}), 401

        return jsonify({
            "status": "sucesso",
            "name": usuario["name"],
            "role": usuario["role"],
            "isSuperAdmin": usuario["isSuperAdmin"],
        })

    except Exception:
        return jsonify({"status": "erro", "erro": "Erro interno no servidor."}), 500


@app.route('/api/login/google', methods=['POST'])
def login_google_backend():
    try:
        dados = request.json or {}
        token_jwt = dados.get('token')

        if not token_jwt:
            return jsonify({"status": "erro", "erro": "Token de autenticação ausente."}), 400

        # VALIDAÇÃO GOOGLE: clock_skew=60 previne erros de relógio desincronizado
        id_info = id_token.verify_oauth2_token(
            token_jwt,
            google_requests.Request(),
            GOOGLE_CLIENT_ID,
            clock_skew_in_seconds=60
        )

        email_google = id_info.get('email', '').lower().strip()
        nome_google = id_info.get('name', 'Usuário Workspace')

        usuario = db.obter_ou_cadastrar_workspace(email_google, nome_google)

        return jsonify({
            "status": "sucesso",
            "name": usuario["name"],
            "role": usuario["role"],
            "isSuperAdmin": usuario["isSuperAdmin"],
        })

    except ValueError as e:
        erro_exato = str(e)
        print(f"Motivo real da rejeição do Google: {erro_exato}")
        return jsonify({"status": "erro", "erro": f"Recusado pelo Google: {erro_exato}"}), 401
    except Exception as e:
        print(f"Erro crítico no servidor durante OAuth: {str(e)}")
        return jsonify({"status": "erro", "erro": "Erro interno no servidor."}), 500

# -------------------------------------------------------------------------
# ROTAS DA FILA E UPLOADS
# -------------------------------------------------------------------------
@app.route('/api/fila', methods=['GET'])
def api_fila():
    user_name = request.args.get('user_name', '').strip()
    role_solicitado = request.args.get('user_role', db.ROLE_COORDENADOR).strip().upper()

    if not user_name:
        user_name = "Juliana Ferreira"
        role_solicitado = db.ROLE_COORDENADOR

    role_real, super_admin = db.papel_real_e_super_admin(user_name)

    if role_real is None:
        # Nome não encontrado em nenhuma conta cadastrada: por segurança,
        # nunca concede a visão de TI nesse caso.
        role_em_uso = db.ROLE_COORDENADOR
    elif super_admin and role_solicitado in (db.ROLE_TI, db.ROLE_COORDENADOR):
        # Só o Admin pode escolher livremente qual modo visualizar.
        role_em_uso = role_solicitado
    else:
        # Para qualquer outra pessoa, o papel real cadastrado no banco
        # sempre prevalece — mesmo que o front-end peça outro papel.
        role_em_uso = role_real

    is_ti = (role_em_uso == db.ROLE_TI)

    conn = db.get_connection()
    cursor = conn.cursor()

    if is_ti:
        cursor.execute("SELECT COUNT(*) FROM pedidos WHERE status='Pendente'")
        pendentes = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM pedidos WHERE status='Imprimindo'")
        imprimindo = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM pedidos WHERE status='Concluído'")
        concluidos = cursor.fetchone()[0]

        cursor.execute("SELECT id, professor_nome, materia, turma, arquivo_nome, copias, status FROM pedidos ORDER BY id DESC")
    else:
        cursor.execute("SELECT COUNT(*) FROM pedidos WHERE status='Pendente' AND professor_nome=?", (user_name,))
        pendentes = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM pedidos WHERE status='Imprimindo' AND professor_nome=?", (user_name,))
        imprimindo = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM pedidos WHERE status='Concluído' AND professor_nome=?", (user_name,))
        concluidos = cursor.fetchone()[0]

        cursor.execute("SELECT id, professor_nome, materia, turma, arquivo_nome, copias, status FROM pedidos WHERE professor_nome=? ORDER BY id DESC", (user_name,))

    linhas_banco = cursor.fetchall()
    conn.close()

    pedidos_lista = []
    contador_pendentes = 0

    for linha in linhas_banco:
        status_job = linha[6]
        posicao_fila = "-"
        if status_job == 'Pendente':
            contador_pendentes += 1
            posicao_fila = f"{contador_pendentes}º"

        pedidos_lista.append({
            "id": linha[0],
            "remetente": linha[1],
            "materia_turma": f"{linha[2]} — {linha[3]}",
            "arquivo": linha[4],
            "copias": merge_int_or_str_if_needed(linha[5]),
            "posicao": posicao_fila,
            "status": status_job
        })

    return jsonify({
        "estatisticas": {"pendentes": pendentes, "imprimindo": imprimindo, "concluidos": concluidos},
        "pedidos": pedidos_lista
    })


def merge_int_or_str_if_needed(val):
    try:
        return int(val)
    except (TypeError, ValueError):
        return val


@app.route('/api/enviar', methods=['POST'])
def api_enviar():
    user_name = request.form.get('user_name', 'Juliana Ferreira').strip()

    materia = request.form.get('materia', 'Geral')
    turma = request.form.get('turma')
    cor = request.form.get('cor', '')
    frente_verso = request.form.get('frente_verso', '')
    acabamento = request.form.get('acabamento', '')
    arquivo = request.files.get('arquivo')

    try:
        copias = int(request.form.get('copias', 1))
    except (TypeError, ValueError):
        return jsonify({"erro": "Número de cópias inválido."}), 400

    if not arquivo or not turma:
        return jsonify({"erro": "Campos obrigatórios em falta"}), 400

    # Nome único em disco: evita que dois uploads com o mesmo nome de
    # arquivo se sobrescrevam (o nome ORIGINAL continua sendo exibido na
    # fila normalmente — só o arquivo salvo fisicamente é renomeado).
    nome_original = secure_filename(arquivo.filename)
    nome_em_disco = f"{secrets.token_hex(5)}_{nome_original}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], nome_em_disco)
    arquivo.save(filepath)

    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO pedidos (professor_nome, materia, turma, copias, cor, frente_verso, acabamento, arquivo_nome, arquivo_path)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_name, materia, turma, copias, cor, frente_verso, acabamento, nome_original, filepath))
    conn.commit()
    conn.close()

    disparar_impressao_windows(user_name, materia, turma, filepath, copias, cor, frente_verso, acabamento)

    return jsonify({"status": "sucesso", "mensagem": "Pedido integrado com sucesso!"})


if __name__ == '__main__':
    modo_debug = os.environ.get("ACALANTO_DEBUG", "false").lower() == "true"
    # host="0.0.0.0" faz o Flask escutar em todas as placas de rede —
    # necessário para os professores acessarem pelo IP da máquina servidora.
    app.run(host="0.0.0.0", debug=modo_debug, use_reloader=False, port=8080)
