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
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

# -------------------------------------------------------------------------
# LOCALIZAÇÃO DO BANCO DE DADOS
# -------------------------------------------------------------------------
_PASTA_ATUAL = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(_PASTA_ATUAL, "acalanto_print.db")

# Papéis (roles) reconhecidos pelo sistema
ROLE_TI = "TI"
ROLE_COORDENADOR = "COORDENADOR"


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
            status TEXT DEFAULT 'Pendente'
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
    _seed_usuarios_locais(cursor, conn)
    _seed_usuarios_workspace(cursor, conn)
    conn.close()


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
