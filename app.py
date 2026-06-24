import os
import calendar
from datetime import datetime, time
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from werkzeug.utils import secure_filename

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


def limpar_pdfs_no_startup():
    """Ao subir o servidor, opcionalmente apaga o PDF pesado de pedidos
    concluídos antigos — segurando o tamanho do banco sem ninguém precisar
    lembrar. Só age se ACALANTO_RETENCAO_PDF_DIAS for maior que zero; o
    registro leve no histórico nunca é tocado. Falhas aqui não derrubam o
    app (a impressão é mais importante que a faxina do disco)."""
    try:
        dias = int(os.environ.get("ACALANTO_RETENCAO_PDF_DIAS", "0"))
    except (TypeError, ValueError):
        dias = 0

    if dias <= 0:
        return

    try:
        apagados = db.limpar_pdfs_antigos(dias=dias)
        if apagados:
            print(f"[Manutenção] {apagados} PDF(s) com mais de {dias} dias foram apagados (histórico preservado).")
    except Exception as e:
        print(f"[Manutenção] Não foi possível limpar PDFs antigos: {e}")


limpar_pdfs_no_startup()


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


def usuario_eh_ti(nome):
    """Confere, pelo nome, se a pessoa é do Departamento de T.I. (ou Admin).
    Mesma lógica de confiança usada em /api/fila: o papel REAL vem sempre do
    banco, nunca do que o front-end alega. Usado para proteger relatórios e
    a limpeza de PDFs, que são ações do Departamento — não do professor."""
    role_real, super_admin = db.papel_real_e_super_admin(nome)
    return role_real == db.ROLE_TI or super_admin

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


# NOTA: o login com Google Workspace foi removido por enquanto — sem um
# domínio próprio e HTTPS, o OAuth do Google não dá para validar com
# segurança. O acesso é só local (usuário/senha) e auto-cadastro. A camada
# de banco do Workspace (tabela usuarios_workspace e
# db.obter_ou_cadastrar_workspace) foi mantida intacta para reativar fácil
# quando houver domínio/HTTPS: basta restaurar esta rota e o botão no
# front-end.


@app.route('/api/registrar', methods=['POST'])
def api_registrar():
    """Auto-cadastro de conta local. Cria SEMPRE como Coordenador — virar
    T.I. é decisão do Departamento, feita no painel de gestão. Em caso de
    sucesso já devolve os dados de sessão, para a pessoa entrar direto."""
    try:
        dados = request.json or {}
        username = dados.get('username', '')
        senha = dados.get('password', '')
        nome = dados.get('nome_completo') or dados.get('name') or ''

        resultado = db.registrar_usuario_local(username, senha, nome)

        if not resultado["ok"]:
            return jsonify({"status": "erro", "erro": resultado["erro"]}), 400

        usuario = resultado["usuario"]
        return jsonify({
            "status": "sucesso",
            "name": usuario["name"],
            "role": usuario["role"],
            "isSuperAdmin": usuario["isSuperAdmin"],
        })
    except Exception:
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

        cursor.execute("SELECT id, professor_nome, materia, turma, arquivo_nome, copias, status, criado_em, impresso_em, erro_em FROM pedidos ORDER BY id DESC")
    else:
        cursor.execute("SELECT COUNT(*) FROM pedidos WHERE status='Pendente' AND professor_nome=?", (user_name,))
        pendentes = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM pedidos WHERE status='Imprimindo' AND professor_nome=?", (user_name,))
        imprimindo = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM pedidos WHERE status='Concluído' AND professor_nome=?", (user_name,))
        concluidos = cursor.fetchone()[0]

        cursor.execute("SELECT id, professor_nome, materia, turma, arquivo_nome, copias, status, criado_em, impresso_em, erro_em FROM pedidos WHERE professor_nome=? ORDER BY id DESC", (user_name,))

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
            "status": status_job,
            # Carimbos de data/hora (ISO 8601, horário de Brasília). Podem
            # vir nulos em pedidos antigos, anteriores a este recurso.
            "enviado_em": linha[7],
            "impresso_em": linha[8],
            "erro_em": linha[9],
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

    # criar_pedido já carimba a data/hora de ENVIO (criado_em). É esse
    # registro que permite, depois, confirmar "você mandou às 14h32 de
    # ontem" em qualquer questionamento de professor.
    db.criar_pedido(
        user_name, materia, turma, copias, cor, frente_verso,
        acabamento, nome_original, conteudo_pdf
    )

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

    # atualizar_status_pedido carimba a data/hora do que aconteceu
    # (impresso_em ou erro_em) e, quando o pedido termina, grava uma cópia
    # leve e permanente no histórico — mesmo que o PDF seja apagado depois.
    encontrado = db.atualizar_status_pedido(pedido_id, novo_status)

    if not encontrado:
        return jsonify({"erro": "Pedido não encontrado"}), 404

    return jsonify({"status": "sucesso"})


# -------------------------------------------------------------------------
# GESTÃO DE CONTAS LOCAIS (só Departamento de T.I.)
# -------------------------------------------------------------------------
@app.route('/api/usuarios', methods=['GET'])
def api_listar_usuarios():
    """Lista as contas locais para o painel de gestão. Só T.I."""
    user_name = request.args.get('user_name', '').strip()
    if not usuario_eh_ti(user_name):
        return jsonify({"erro": "Acesso restrito ao Departamento de T.I."}), 403
    return jsonify({"usuarios": db.listar_usuarios_locais()})


@app.route('/api/usuarios/cargo', methods=['POST'])
def api_definir_cargo():
    """Promove/rebaixa uma conta entre Coordenador e T.I. Só T.I."""
    dados = request.json or {}
    user_name = (dados.get('user_name') or '').strip()
    if not usuario_eh_ti(user_name):
        return jsonify({"erro": "Acesso restrito ao Departamento de T.I."}), 403

    alvo = dados.get('username', '')
    novo_role = (dados.get('role') or '').strip().upper()

    resultado = db.definir_cargo_usuario_local(alvo, novo_role)
    if not resultado["ok"]:
        return jsonify({"erro": resultado["erro"]}), 400
    return jsonify({"status": "sucesso"})


@app.route('/api/usuarios/remover', methods=['POST'])
def api_remover_usuario():
    """Remove uma conta local. Só T.I."""
    dados = request.json or {}
    user_name = (dados.get('user_name') or '').strip()
    if not usuario_eh_ti(user_name):
        return jsonify({"erro": "Acesso restrito ao Departamento de T.I."}), 403

    alvo = dados.get('username', '')

    resultado = db.remover_usuario_local(alvo)
    if not resultado["ok"]:
        return jsonify({"erro": resultado["erro"]}), 400
    return jsonify({"status": "sucesso"})


# -------------------------------------------------------------------------
# RELATÓRIOS E MANUTENÇÃO (só Departamento de T.I.)
# -------------------------------------------------------------------------
def _intervalo_do_mes(mes):
    """Converte um 'AAAA-MM' (ex.: '2025-10') no primeiro e último dia
    daquele mês ('2025-10-01', '2025-10-31'). Retorna (None, None) se o
    formato for inválido — o relatório simplesmente não filtra por data."""
    try:
        ano, num_mes = mes.split("-")
        ano, num_mes = int(ano), int(num_mes)
        ultimo_dia = calendar.monthrange(ano, num_mes)[1]
        return f"{ano:04d}-{num_mes:02d}-01", f"{ano:04d}-{num_mes:02d}-{ultimo_dia:02d}"
    except (ValueError, AttributeError, calendar.IllegalMonthError):
        return None, None


@app.route('/api/relatorio', methods=['GET'])
def api_relatorio():
    """Contagem de cópias e pedidos por professor num período. Responde
    'quantas cópias o professor X mandou esse mês?' e 'quanto a escola
    imprimiu em outubro?'. Restrito ao Departamento de T.I.

    Parâmetros (query string):
      user_name : nome de quem pede (validado como T.I. no banco).
      mes       : 'AAAA-MM' — atalho que já vira o mês inteiro. Opcional.
      inicio    : 'AAAA-MM-DD' — usado se 'mes' não for informado. Opcional.
      fim       : 'AAAA-MM-DD' — idem. Opcional.
      base      : 'criado' (data de envio, padrão) ou 'impresso'.
    """
    user_name = request.args.get('user_name', '').strip()

    if not usuario_eh_ti(user_name):
        return jsonify({"erro": "Acesso restrito ao Departamento de T.I."}), 403

    mes = request.args.get('mes', '').strip()
    if mes:
        inicio, fim = _intervalo_do_mes(mes)
    else:
        inicio = request.args.get('inicio', '').strip() or None
        fim = request.args.get('fim', '').strip() or None

    base = request.args.get('base', 'criado').strip().lower()
    if base not in ('criado', 'impresso'):
        base = 'criado'

    relatorio = db.relatorio_contagem(inicio=inicio, fim=fim, base=base)
    relatorio["periodo"] = {"inicio": inicio, "fim": fim, "base": base}
    return jsonify(relatorio)


@app.route('/api/admin/limpar-pdfs', methods=['POST'])
def api_limpar_pdfs():
    """Apaga os PDFs pesados de pedidos já concluídos e antigos, preservando
    o registro leve no histórico. Serve para o banco não crescer sem limite.
    Restrito ao Departamento de T.I."""
    dados = request.json or {}
    user_name = (dados.get('user_name') or '').strip()

    if not usuario_eh_ti(user_name):
        return jsonify({"erro": "Acesso restrito ao Departamento de T.I."}), 403

    try:
        dias = int(dados.get('dias', 7))
    except (TypeError, ValueError):
        dias = 7

    quantidade = db.limpar_pdfs_antigos(dias=max(dias, 0))
    return jsonify({"status": "sucesso", "pdfs_apagados": quantidade})


if __name__ == '__main__':
    modo_debug = os.environ.get("ACALANTO_DEBUG", "false").lower() == "true"
    # host="0.0.0.0" faz o Flask escutar em todas as placas de rede —
    # necessário para os professores acessarem pelo IP da máquina servidora.
    app.run(host="0.0.0.0", debug=modo_debug, use_reloader=False, port=8080)
