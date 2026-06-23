import os
from datetime import datetime, time
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from werkzeug.utils import secure_filename
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

import banco_dados as db  # Toda a lógica de usuários, senhas e privilégios
                           # de Admin vive em banco_dados/ — não aqui.

# Carrega o arquivo .env (se existir) para dentro de os.environ, ANTES de
# qualquer os.environ.get() abaixo. Sem essa linha, o .env não tem efeito
# nenhum — ele é só um arquivo de texto até alguém ler ele.
load_dotenv()

app = Flask(__name__)

CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": "*"
    }
})

# ID do cliente OAuth do Google Workspace. Não é um segredo (é o mesmo
# valor que já fica visível no front-end), mas fica mais fácil de trocar
# sem editar código se algum dia mudar — definido no .env como
# GOOGLE_CLIENT_ID. O valor abaixo é só o padrão, caso o .env não exista.
GOOGLE_CLIENT_ID = os.environ.get(
    "GOOGLE_CLIENT_ID",
    "314763396953-7imem6nh7na48ujfnbnb1ni79rvpcbn6.apps.googleusercontent.com"
)

# Chave secreta que só o agente de impressão (rodando no computador do
# colégio) conhece. Protege as rotas /api/agente/* — sem essa chave, elas
# nunca respondem nada de útil, mesmo se alguém descobrir a URL.
AGENTE_API_KEY = os.environ.get("AGENTE_API_KEY", "")

# Horário em que a impressora "aceita" trabalhos. Fora dessa faixa, os
# pedidos ficam represados como Pendente normalmente — o agente local que
# decide não imprimir fora do expediente (ver agente_impressora.py).
FUSO_HORARIO = ZoneInfo("America/Sao_Paulo")
HORARIO_INICIO_IMPRESSAO = time(8, 30)
HORARIO_FIM_IMPRESSAO = time(17, 30)

db.init_db()


def dentro_do_horario_de_impressao():
    agora = datetime.now(FUSO_HORARIO).time()
    return HORARIO_INICIO_IMPRESSAO <= agora <= HORARIO_FIM_IMPRESSAO


def mensagem_para_envio():
    if dentro_do_horario_de_impressao():
        return "Pedido enviado para a fila de impressão com sucesso!"
    return (
        "Pedido recebido! Fora do horário de impressão (08:30–17:30), "
        "ele vai entrar na fila e será impresso a partir das 08:30, "
        "respeitando a ordem de chegada."
    )


def verificar_chave_agente():
    """Confere se a requisição trouxe a chave secreta correta do agente
    de impressão. Sem AGENTE_API_KEY configurado no .env, nega tudo —
    nunca libera por padrão."""
    if not AGENTE_API_KEY:
        return False
    return request.headers.get("Authorization", "") == f"Bearer {AGENTE_API_KEY}"

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

    # O PDF vai direto para o banco (como BLOB), não para um caminho em
    # disco — no Discloud não há garantia de que um arquivo salvo em
    # disco sobreviva a um redeploy ou reinício do container.
    nome_original = secure_filename(arquivo.filename)
    conteudo_pdf = arquivo.read()

    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO pedidos (professor_nome, materia, turma, copias, cor, frente_verso, acabamento, arquivo_nome, arquivo_conteudo)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_name, materia, turma, copias, cor, frente_verso, acabamento, nome_original, conteudo_pdf))
    conn.commit()
    conn.close()

    # Note que NÃO chamamos mais a impressão por aqui — quem imprime agora
    # é o agente local, consultando as rotas abaixo.
    return jsonify({"status": "sucesso", "mensagem": mensagem_para_envio()})


# -------------------------------------------------------------------------
# ROTAS DO AGENTE DE IMPRESSÃO (rodando no computador do colégio)
# -------------------------------------------------------------------------
@app.route('/api/agente/pendentes', methods=['GET'])
def agente_pendentes():
    if not verificar_chave_agente():
        return jsonify({"erro": "Não autorizado"}), 401

    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, professor_nome, materia, turma, copias, cor, frente_verso, acabamento
        FROM pedidos WHERE status = 'Pendente' ORDER BY id ASC
    ''')
    pedidos = [dict(linha) for linha in cursor.fetchall()]
    conn.close()

    return jsonify({"pedidos": pedidos})


@app.route('/api/agente/arquivo/<int:pedido_id>', methods=['GET'])
def agente_arquivo(pedido_id):
    if not verificar_chave_agente():
        return jsonify({"erro": "Não autorizado"}), 401

    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT arquivo_conteudo FROM pedidos WHERE id = ?', (pedido_id,))
    linha = cursor.fetchone()
    conn.close()

    if not linha or linha["arquivo_conteudo"] is None:
        return jsonify({"erro": "Arquivo não encontrado"}), 404

    return Response(linha["arquivo_conteudo"], mimetype="application/pdf")


@app.route('/api/agente/status/<int:pedido_id>', methods=['POST'])
def agente_atualizar_status(pedido_id):
    if not verificar_chave_agente():
        return jsonify({"erro": "Não autorizado"}), 401

    dados = request.json or {}
    novo_status = dados.get("status")

    if novo_status not in ("Imprimindo", "Concluído", "Erro"):
        return jsonify({"erro": "Status inválido"}), 400

    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE pedidos SET status = ? WHERE id = ?', (novo_status, pedido_id))
    conn.commit()
    conn.close()

    return jsonify({"status": "sucesso"})


if __name__ == '__main__':
    modo_debug = os.environ.get("ACALANTO_DEBUG", "false").lower() == "true"
    # host="0.0.0.0" faz o Flask escutar em todas as placas de rede —
    # necessário para os professores acessarem pelo IP da máquina servidora.
    app.run(host="0.0.0.0", debug=modo_debug, use_reloader=False, port=8080)
