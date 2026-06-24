"""
Camada de acesso ao banco de dados do Sistema de Impressão do Instituto Acalanto.

Este módulo é o ÚNICO lugar do projeto que conhece usuários, senhas e
privilégios de administrador. O app.py NUNCA deve declarar credenciais ou
papéis (roles) diretamente — apenas chamar as funções daqui.

O arquivo .db físico é criado DENTRO desta pasta (banco_dados/), separado
do resto do código. Isso facilita:
  1) Restringir o acesso ao arquivo (permissões de pasta) sem afetar o app.
  2) Excluir a pasta inteira do controle de versão (ver .gitignore ao lado).
  3) Trocar a forma de autenticação no futuro sem tocar nas rotas do Flask.
"""

import os
import re
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo
from werkzeug.security import generate_password_hash, check_password_hash

# -------------------------------------------------------------------------
# LOCALIZAÇÃO DO BANCO DE DADOS
# -------------------------------------------------------------------------
_PASTA_ATUAL = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(_PASTA_ATUAL, "acalanto_print.db")

# Papéis (roles) reconhecidos pelo sistema
ROLE_TI = "TI"
ROLE_COORDENADOR = "COORDENADOR"

# Fuso usado para CARIMBAR os pedidos. Guardamos a data/hora já no horário
# de Brasília (e não em UTC) porque todo relatório do colégio é pensado em
# "mês de outubro", "ontem", etc. — sempre no horário local. Assim o dia
# que aparece no banco é exatamente o dia que a pessoa enviou/imprimiu.
FUSO_HORARIO = ZoneInfo("America/Sao_Paulo")


def agora_iso():
    """Data/hora atual no fuso de São Paulo, em texto ISO 8601 com segundos
    (ex.: '2026-06-23T14:35:09-03:00'). É o carimbo único usado em todo o
    sistema para registrar QUANDO um pedido foi enviado, impresso ou falhou."""
    return datetime.now(FUSO_HORARIO).isoformat(timespec="seconds")


# -------------------------------------------------------------------------
# CONEXÃO
# -------------------------------------------------------------------------
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# -------------------------------------------------------------------------
# CRIAÇÃO DAS TABELAS E SEED INICIAL
# -------------------------------------------------------------------------
def init_db():
    os.makedirs(_PASTA_ATUAL, exist_ok=True)
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            professor_nome TEXT NOT NULL,
            materia TEXT NOT NULL,
            turma TEXT NOT NULL,
            copias INTEGER NOT NULL,
            cor TEXT NOT NULL,
            frente_verso TEXT NOT NULL,
            acabamento TEXT NOT NULL,
            arquivo_nome TEXT NOT NULL,
            arquivo_conteudo BLOB NOT NULL,
            status TEXT DEFAULT 'Pendente',
            criado_em TEXT,
            impresso_em TEXT,
            erro_em TEXT
        )
    ''')

    # HISTÓRICO PERMANENTE E LEVE.
    # A tabela 'pedidos' guarda o PDF inteiro (BLOB pesado) e é a fila de
    # trabalho do dia a dia. Já 'historico_impressoes' guarda só os DADOS
    # (quem, o quê, quando, quantas cópias) — nunca o arquivo. Quando um
    # pedido termina, copiamos esses dados para cá. Depois o PDF pesado pode
    # ser apagado de 'pedidos' (ver limpar_pdfs_antigos) sem perder o
    # registro: o histórico continua respondendo "o professor X mandou tal
    # arquivo no dia tal" por meses, sem fazer o banco crescer sem limite.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historico_impressoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pedido_id INTEGER NOT NULL UNIQUE,
            professor_nome TEXT NOT NULL,
            materia TEXT,
            turma TEXT,
            copias INTEGER NOT NULL,
            cor TEXT,
            frente_verso TEXT,
            acabamento TEXT,
            arquivo_nome TEXT,
            status_final TEXT NOT NULL,
            criado_em TEXT,
            impresso_em TEXT,
            erro_em TEXT,
            registrado_em TEXT NOT NULL
        )
    ''')

    # Contas Google Workspace (login com conta institucional)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios_workspace (
            email TEXT PRIMARY KEY NOT NULL,
            nome_completo TEXT NOT NULL,
            role TEXT NOT NULL,
            super_admin INTEGER NOT NULL DEFAULT 0
        )
    ''')

    # Contas locais (usuário/senha do servidor). É AQUI, e só aqui, que
    # moram as credenciais e o privilégio de administrador (super_admin).
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios_locais (
            username TEXT PRIMARY KEY NOT NULL,
            senha_hash TEXT NOT NULL,
            nome_completo TEXT NOT NULL,
            role TEXT NOT NULL,
            super_admin INTEGER NOT NULL DEFAULT 0
        )
    ''')

    conn.commit()
    _migrar_colunas_pedidos(cursor, conn)
    _seed_usuarios_locais(cursor, conn)
    _seed_usuarios_workspace(cursor, conn)
    conn.close()


def _migrar_colunas_pedidos(cursor, conn):
    """Garante que um banco JÁ EXISTENTE (criado antes destas colunas)
    ganhe os campos de data/hora sem perder nenhum dado. O 'CREATE TABLE IF
    NOT EXISTS' acima só vale para bancos novos — em bancos antigos a tabela
    já existe, então precisamos adicionar as colunas com ALTER TABLE.
    Rodar isto várias vezes é seguro: só adiciona o que ainda falta."""
    cursor.execute("PRAGMA table_info(pedidos)")
    colunas_existentes = {linha["name"] for linha in cursor.fetchall()}

    for coluna in ("criado_em", "impresso_em", "erro_em"):
        if coluna not in colunas_existentes:
            cursor.execute(f"ALTER TABLE pedidos ADD COLUMN {coluna} TEXT")

    conn.commit()


def _seed_usuarios_locais(cursor, conn):
    cursor.execute("SELECT COUNT(*) FROM usuarios_locais")
    if cursor.fetchone()[0] > 0:
        return

    # ------------------------------------------------------------------
    # ÚNICO lugar do projeto onde contas locais e privilégios existem.
    # super_admin = 1  ->  pode alternar livremente entre os modos
    #                      Professor e Departamento de T.I. na interface.
    # ------------------------------------------------------------------
    contas_iniciais = [
        # username,      senha,           nome_completo,                role,              super_admin
        ("admin",        "575859",        "Administrador",              ROLE_TI,           1),
        ("ti",           "123",           "Ranieri Alencar da Silva",    ROLE_TI,           0),
        ("ranieri",      "123",           "Ranieri Alencar da Silva",    ROLE_TI,           0),
        ("coordenador",  "acalanto2024",  "Juliana Ferreira",            ROLE_COORDENADOR,  0),
    ]

    for username, senha, nome, role, super_admin in contas_iniciais:
        cursor.execute('''
            INSERT INTO usuarios_locais (username, senha_hash, nome_completo, role, super_admin)
            VALUES (?, ?, ?, ?, ?)
        ''', (username, generate_password_hash(senha), nome, role, super_admin))

    conn.commit()


def _seed_usuarios_workspace(cursor, conn):
    cursor.execute("SELECT COUNT(*) FROM usuarios_workspace")
    if cursor.fetchone()[0] > 0:
        return

    usuarios_seeding = [
        ("ranieri.alencar@institutoacalanto.com", "Ranieri Alencar da Silva", ROLE_TI, 0),
        ("carlos.ti@institutoacalanto.com", "Carlos Eduardo (T.I.)", ROLE_TI, 0),
        ("juliana.ferreira@institutoacalanto.com", "Juliana Ferreira", ROLE_COORDENADOR, 0),
    ]
    cursor.executemany('''
        INSERT INTO usuarios_workspace (email, nome_completo, role, super_admin)
        VALUES (?, ?, ?, ?)
    ''', usuarios_seeding)
    conn.commit()


# -------------------------------------------------------------------------
# AUTENTICAÇÃO LOCAL
# -------------------------------------------------------------------------
def autenticar_local(username, senha):
    """Confere usuário/senha contra usuarios_locais.
    Retorna {name, role, isSuperAdmin} ou None se inválido."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT senha_hash, nome_completo, role, super_admin FROM usuarios_locais WHERE username = ?",
        (username.lower(),)
    )
    linha = cursor.fetchone()
    conn.close()

    if not linha or not check_password_hash(linha["senha_hash"], senha):
        return None

    return {
        "name": linha["nome_completo"],
        "role": linha["role"],
        "isSuperAdmin": bool(linha["super_admin"]),
    }


# -------------------------------------------------------------------------
# CADASTRO E GESTÃO DE CONTAS LOCAIS
# -------------------------------------------------------------------------
# Regra de ouro de segurança: quem cria a PRÓPRIA conta entra SEMPRE como
# COORDENADOR (sem poder de administrador). Tornar alguém T.I. é uma decisão
# deliberada do próprio Departamento de T.I., feita no painel de gestão —
# nunca uma opção livre de quem se cadastra. Assim ninguém se autopromove a
# administrador só preenchendo um formulário.
_MIN_TAMANHO_SENHA = 4
_PADRAO_USERNAME = re.compile(r"^[a-z0-9._-]{3,40}$")


def registrar_usuario_local(username, senha, nome_completo):
    """Cria uma conta local nova, SEMPRE como COORDENADOR. Devolve:
      {"ok": True,  "usuario": {name, role, isSuperAdmin}}  em caso de sucesso
      {"ok": False, "erro": "mensagem amigável"}            se algo impedir
    """
    username = (username or "").strip().lower()
    senha = senha or ""
    nome_completo = (nome_completo or "").strip()

    if not nome_completo:
        return {"ok": False, "erro": "Informe o seu nome completo."}
    if not _PADRAO_USERNAME.match(username):
        return {"ok": False, "erro": (
            "Usuário inválido: use 3 a 40 caracteres, apenas letras "
            "minúsculas, números, ponto, hífen ou underline."
        )}
    if len(senha) < _MIN_TAMANHO_SENHA:
        return {"ok": False, "erro": f"A senha precisa ter pelo menos {_MIN_TAMANHO_SENHA} caracteres."}

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM usuarios_locais WHERE username = ?", (username,))
    if cursor.fetchone():
        conn.close()
        return {"ok": False, "erro": "Esse usuário já existe. Escolha outro."}

    cursor.execute('''
        INSERT INTO usuarios_locais (username, senha_hash, nome_completo, role, super_admin)
        VALUES (?, ?, ?, ?, 0)
    ''', (username, generate_password_hash(senha), nome_completo, ROLE_COORDENADOR))
    conn.commit()
    conn.close()

    return {
        "ok": True,
        "usuario": {"name": nome_completo, "role": ROLE_COORDENADOR, "isSuperAdmin": False},
    }


def listar_usuarios_locais():
    """Lista as contas locais para o painel de gestão da T.I. NUNCA devolve o
    hash de senha — só identificação e cargo."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT username, nome_completo, role, super_admin
          FROM usuarios_locais
         ORDER BY super_admin DESC, role DESC, nome_completo ASC
    ''')
    linhas = cursor.fetchall()
    conn.close()
    return [
        {
            "username": linha["username"],
            "name": linha["nome_completo"],
            "role": linha["role"],
            "isSuperAdmin": bool(linha["super_admin"]),
        }
        for linha in linhas
    ]


def definir_cargo_usuario_local(username, novo_role):
    """Promove/rebaixa uma conta local entre COORDENADOR e T.I. A conta de
    administrador (super_admin) é protegida: seu cargo nunca é mexido por
    aqui. Retorna {"ok": bool, "erro": str|None}."""
    username = (username or "").strip().lower()
    if novo_role not in (ROLE_TI, ROLE_COORDENADOR):
        return {"ok": False, "erro": "Cargo inválido."}

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT super_admin FROM usuarios_locais WHERE username = ?", (username,))
    linha = cursor.fetchone()

    if not linha:
        conn.close()
        return {"ok": False, "erro": "Conta não encontrada."}
    if linha["super_admin"]:
        conn.close()
        return {"ok": False, "erro": "A conta de administrador não pode ter o cargo alterado."}

    cursor.execute("UPDATE usuarios_locais SET role = ? WHERE username = ?", (novo_role, username))
    conn.commit()
    conn.close()
    return {"ok": True, "erro": None}


def remover_usuario_local(username):
    """Remove uma conta local. A conta de administrador (super_admin) é
    protegida e nunca pode ser apagada por aqui. Retorna
    {"ok": bool, "erro": str|None}."""
    username = (username or "").strip().lower()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT super_admin FROM usuarios_locais WHERE username = ?", (username,))
    linha = cursor.fetchone()

    if not linha:
        conn.close()
        return {"ok": False, "erro": "Conta não encontrada."}
    if linha["super_admin"]:
        conn.close()
        return {"ok": False, "erro": "A conta de administrador não pode ser removida."}

    cursor.execute("DELETE FROM usuarios_locais WHERE username = ?", (username,))
    conn.commit()
    conn.close()
    return {"ok": True, "erro": None}


# -------------------------------------------------------------------------
# GOOGLE WORKSPACE
# -------------------------------------------------------------------------
def obter_ou_cadastrar_workspace(email, nome_sugerido):
    """Busca um usuário Google Workspace; se não existir, cadastra
    automaticamente como COORDENADOR (sem privilégio de admin)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT nome_completo, role, super_admin FROM usuarios_workspace WHERE email = ?",
        (email,)
    )
    linha = cursor.fetchone()

    if linha:
        resultado = {
            "name": linha["nome_completo"],
            "role": linha["role"],
            "isSuperAdmin": bool(linha["super_admin"]),
        }
        conn.close()
        return resultado

    cursor.execute('''
        INSERT INTO usuarios_workspace (email, nome_completo, role, super_admin)
        VALUES (?, ?, ?, 0)
    ''', (email, nome_sugerido, ROLE_COORDENADOR))
    conn.commit()
    conn.close()

    return {"name": nome_sugerido, "role": ROLE_COORDENADOR, "isSuperAdmin": False}


# -------------------------------------------------------------------------
# PAPEL REAL (evita que o front-end "se promova" sozinho a TI)
# -------------------------------------------------------------------------
def papel_real_e_super_admin(nome_completo):
    """Procura o papel (role) e o privilégio super_admin reais de uma
    pessoa pelo nome completo. Usado para validar o que o front-end envia
    em /api/fila, já que o nome/role chegam por query string e não por
    uma sessão de servidor (decisão de arquitetura para evitar problemas
    de cookies entre IPs diferentes na rede do colégio)."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT role, super_admin FROM usuarios_locais WHERE nome_completo = ?",
        (nome_completo,)
    )
    linha = cursor.fetchone()

    if not linha:
        cursor.execute(
            "SELECT role, super_admin FROM usuarios_workspace WHERE nome_completo = ?",
            (nome_completo,)
        )
        linha = cursor.fetchone()

    conn.close()

    if not linha:
        return None, False

    return linha["role"], bool(linha["super_admin"])


# -------------------------------------------------------------------------
# PEDIDOS DE IMPRESSÃO (criação, status e o registro de "quem pediu o quê
# e quando" que protege o Departamento em qualquer questionamento)
# -------------------------------------------------------------------------
# Estados possíveis de um pedido. Os três últimos são "finais": ao chegar
# em Concluído ou Erro, o pedido é gravado no histórico permanente.
STATUS_PENDENTE = "Pendente"
STATUS_IMPRIMINDO = "Imprimindo"
STATUS_CONCLUIDO = "Concluído"
STATUS_ERRO = "Erro"
STATUS_FINAIS = (STATUS_CONCLUIDO, STATUS_ERRO)


def criar_pedido(professor_nome, materia, turma, copias, cor,
                 frente_verso, acabamento, arquivo_nome, arquivo_conteudo):
    """Registra um novo pedido na fila, JÁ carimbando a data/hora de envio
    (criado_em). É esse carimbo que permite responder depois 'você mandou às
    14h32 de ontem' em vez de só 'não sei se chegou'. Retorna o id criado."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO pedidos
            (professor_nome, materia, turma, copias, cor, frente_verso,
             acabamento, arquivo_nome, arquivo_conteudo, status, criado_em)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (professor_nome, materia, turma, copias, cor, frente_verso,
          acabamento, arquivo_nome, arquivo_conteudo, STATUS_PENDENTE,
          agora_iso()))
    pedido_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return pedido_id


def atualizar_status_pedido(pedido_id, novo_status):
    """Muda o status de um pedido e carimba a data/hora do que aconteceu:
      - 'Imprimindo' -> só muda o status.
      - 'Concluído'  -> grava impresso_em e copia o pedido para o histórico.
      - 'Erro'       -> grava erro_em e copia o pedido para o histórico.

    Retorna True se o pedido existia, False caso contrário. Idempotente: se
    o agente reenviar 'Concluído' duas vezes, o histórico não duplica
    (a linha é atualizada, não inserida de novo)."""
    momento = agora_iso()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pedidos WHERE id = ?", (pedido_id,))
    pedido = cursor.fetchone()

    if not pedido:
        conn.close()
        return False

    if novo_status == STATUS_CONCLUIDO:
        cursor.execute(
            "UPDATE pedidos SET status = ?, impresso_em = ? WHERE id = ?",
            (novo_status, momento, pedido_id)
        )
        _registrar_no_historico(cursor, pedido, STATUS_CONCLUIDO,
                                impresso_em=momento, erro_em=None,
                                registrado_em=momento)
    elif novo_status == STATUS_ERRO:
        cursor.execute(
            "UPDATE pedidos SET status = ?, erro_em = ? WHERE id = ?",
            (novo_status, momento, pedido_id)
        )
        _registrar_no_historico(cursor, pedido, STATUS_ERRO,
                                impresso_em=None, erro_em=momento,
                                registrado_em=momento)
    else:
        # Imprimindo (ou qualquer outro estado não-final): só atualiza.
        cursor.execute(
            "UPDATE pedidos SET status = ? WHERE id = ?",
            (novo_status, pedido_id)
        )

    conn.commit()
    conn.close()
    return True


def _registrar_no_historico(cursor, pedido, status_final, impresso_em,
                            erro_em, registrado_em):
    """Copia os dados LEVES do pedido para o histórico permanente (sem o
    PDF). Usa o mesmo cursor/transação de quem chamou. Se o pedido já estiver
    no histórico (ex.: reenvio de status), atualiza a linha existente em vez
    de criar outra — evitando contagem dobrada nos relatórios."""
    pedido_id = pedido["id"]

    cursor.execute(
        "SELECT id FROM historico_impressoes WHERE pedido_id = ?",
        (pedido_id,)
    )
    ja_existe = cursor.fetchone()

    if ja_existe:
        cursor.execute('''
            UPDATE historico_impressoes
               SET status_final = ?,
                   impresso_em = COALESCE(?, impresso_em),
                   erro_em = COALESCE(?, erro_em),
                   registrado_em = ?
             WHERE pedido_id = ?
        ''', (status_final, impresso_em, erro_em, registrado_em, pedido_id))
        return

    cursor.execute('''
        INSERT INTO historico_impressoes
            (pedido_id, professor_nome, materia, turma, copias, cor,
             frente_verso, acabamento, arquivo_nome, status_final,
             criado_em, impresso_em, erro_em, registrado_em)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        pedido_id, pedido["professor_nome"], pedido["materia"],
        pedido["turma"], pedido["copias"], pedido["cor"],
        pedido["frente_verso"], pedido["acabamento"], pedido["arquivo_nome"],
        status_final, pedido["criado_em"], impresso_em, erro_em,
        registrado_em
    ))


# -------------------------------------------------------------------------
# RELATÓRIOS (contagem por professor / período) E LIMPEZA DE PDFs
# -------------------------------------------------------------------------
def relatorio_contagem(inicio=None, fim=None, base="criado"):
    """Conta cópias e número de pedidos por professor, lendo o histórico
    permanente. Responde perguntas do tipo 'quantas cópias o professor X
    mandou esse mês?' ou 'quanto a escola imprimiu em outubro?'.

    inicio / fim : datas no formato 'AAAA-MM-DD' (inclusivas). Qualquer um
                   pode ser omitido (None) para não limitar aquele lado.
    base         : 'criado'   -> conta pela data de ENVIO (quem mandou).
                   'impresso' -> conta pela data de IMPRESSÃO (o que saiu).

    Retorna um dict com:
      por_professor : lista de {professor, pedidos, copias}, do maior p/ menor.
      total_pedidos : soma de todos os pedidos no período.
      total_copias  : soma de todas as cópias no período.
    """
    # Whitelist explícita: a coluna NUNCA vem de entrada do usuário, evitando
    # qualquer injeção via o nome do campo.
    coluna = "impresso_em" if base == "impresso" else "criado_em"

    filtros = [f"{coluna} IS NOT NULL"]
    params = []
    # Comparamos só os 10 primeiros caracteres (AAAA-MM-DD) do carimbo ISO.
    # Como ele já está no horário de Brasília, o dia comparado é o dia local,
    # sem surpresa de fuso ao virar a meia-noite.
    if inicio:
        filtros.append(f"substr({coluna}, 1, 10) >= ?")
        params.append(inicio)
    if fim:
        filtros.append(f"substr({coluna}, 1, 10) <= ?")
        params.append(fim)

    where = "WHERE " + " AND ".join(filtros)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f'''
        SELECT professor_nome,
               COUNT(*) AS pedidos,
               COALESCE(SUM(copias), 0) AS copias
          FROM historico_impressoes
          {where}
         GROUP BY professor_nome
         ORDER BY copias DESC, pedidos DESC
    ''', params)
    linhas = cursor.fetchall()
    conn.close()

    por_professor = [
        {
            "professor": linha["professor_nome"],
            "pedidos": linha["pedidos"],
            "copias": linha["copias"],
        }
        for linha in linhas
    ]

    return {
        "por_professor": por_professor,
        "total_pedidos": sum(p["pedidos"] for p in por_professor),
        "total_copias": sum(p["copias"] for p in por_professor),
    }


def limpar_pdfs_antigos(dias=7):
    """Apaga o PDF pesado (arquivo_conteudo) dos pedidos que já terminaram e
    já estão no histórico há mais de `dias` dias. O registro leve continua
    intacto no histórico — só o arquivo grande some, segurando o tamanho do
    banco. Não remove a linha de 'pedidos' (a fila continua mostrando o
    status), apenas esvazia o conteúdo do arquivo.

    Retorna quantos pedidos tiveram o PDF apagado."""
    limite = datetime.now(FUSO_HORARIO).timestamp() - dias * 86400

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.id, h.registrado_em
          FROM pedidos p
          JOIN historico_impressoes h ON h.pedido_id = p.id
         WHERE length(p.arquivo_conteudo) > 0
    ''')

    ids_para_limpar = []
    for linha in cursor.fetchall():
        registrado_em = linha["registrado_em"]
        try:
            quando = datetime.fromisoformat(registrado_em).timestamp()
        except (TypeError, ValueError):
            # Sem data confiável: por segurança, não apaga ainda.
            continue
        if quando <= limite:
            ids_para_limpar.append(linha["id"])

    for pedido_id in ids_para_limpar:
        # X'' é um BLOB de tamanho zero: satisfaz o NOT NULL da coluna e ao
        # mesmo tempo libera todo o espaço que o PDF ocupava.
        cursor.execute(
            "UPDATE pedidos SET arquivo_conteudo = X'' WHERE id = ?",
            (pedido_id,)
        )

    conn.commit()
    conn.close()
    return len(ids_para_limpar)
