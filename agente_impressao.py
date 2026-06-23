"""
agente_impressao.py

Este script roda NO COMPUTADOR DO COLÉGIO — não na nuvem (Discloud).
Ele é o único componente do sistema com acesso à impressora física.

O que ele faz, em loop:
  1. Pergunta ao site (hospedado no Discloud) se existe algum pedido
     "Pendente" — só faz isso dentro do horário permitido (08:30–17:30).
  2. Para cada pedido encontrado, baixa o PDF e dispara a impressão usando
     o automacao_impressora.py já existente.
  3. Avisa o site se deu certo ("Concluído") ou se falhou ("Erro").

Fora do horário de impressão, ele simplesmente não faz nada no ciclo —
os pedidos continuam aparecendo como "Pendente" até o horário abrir de
novo, e são processados na ordem de chegada.
"""

import os
import time as time_module
from datetime import datetime, time
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv

from automacao_impressora import disparar_impressao_windows

# Carrega especificamente "agente.env" (não ".env") — assim, se este script
# e o app.py estiverem na mesma pasta durante testes locais, os dois
# arquivos de configuração nunca se confundem.
load_dotenv("agente.env")

# ---------------------------------------------------------------------
# CONFIGURAÇÃO (vem do .env deste mesmo computador — ver agente.env.example)
# ---------------------------------------------------------------------
CLOUD_URL = os.environ.get("CLOUD_URL", "").rstrip("/")
AGENTE_API_KEY = os.environ.get("AGENTE_API_KEY", "")
INTERVALO_SEGUNDOS = int(os.environ.get("AGENTE_INTERVALO_SEGUNDOS", "15"))

FUSO_HORARIO = ZoneInfo("America/Sao_Paulo")
HORARIO_INICIO = time(8, 30)
HORARIO_FIM = time(17, 30)

PASTA_TEMPORARIA = "temp_impressao"


def cabecalhos():
    return {"Authorization": f"Bearer {AGENTE_API_KEY}"}


def dentro_do_horario_de_impressao():
    agora = datetime.now(FUSO_HORARIO).time()
    return HORARIO_INICIO <= agora <= HORARIO_FIM


def buscar_pendentes():
    resposta = requests.get(f"{CLOUD_URL}/api/agente/pendentes", headers=cabecalhos(), timeout=10)
    resposta.raise_for_status()
    return resposta.json().get("pedidos", [])


def baixar_arquivo(pedido_id):
    resposta = requests.get(f"{CLOUD_URL}/api/agente/arquivo/{pedido_id}", headers=cabecalhos(), timeout=30)
    resposta.raise_for_status()
    return resposta.content


def atualizar_status(pedido_id, novo_status):
    requests.post(
        f"{CLOUD_URL}/api/agente/status/{pedido_id}",
        headers=cabecalhos(),
        json={"status": novo_status},
        timeout=10,
    )


def processar_pedido(pedido):
    pedido_id = pedido["id"]
    print(f"[Agente] Processando pedido #{pedido_id} — {pedido['professor_nome']} ({pedido['materia']})")

    atualizar_status(pedido_id, "Imprimindo")

    try:
        conteudo_pdf = baixar_arquivo(pedido_id)
    except Exception as e:
        print(f"[Agente] Erro ao baixar arquivo do pedido #{pedido_id}: {e}")
        atualizar_status(pedido_id, "Erro")
        return

    os.makedirs(PASTA_TEMPORARIA, exist_ok=True)
    caminho_temporario = os.path.join(PASTA_TEMPORARIA, f"{pedido_id}.pdf")
    with open(caminho_temporario, "wb") as arquivo:
        arquivo.write(conteudo_pdf)

    try:
        sucesso = disparar_impressao_windows(
            pedido["professor_nome"],
            pedido["materia"],
            pedido["turma"],
            caminho_temporario,
            pedido["copias"],
            pedido["cor"],
            pedido["frente_verso"],
            pedido["acabamento"],
        )
    finally:
        if os.path.exists(caminho_temporario):
            os.remove(caminho_temporario)

    if sucesso:
        print(f"[Agente] Pedido #{pedido_id} concluído.")
        atualizar_status(pedido_id, "Concluído")
    else:
        print(f"[Agente] Pedido #{pedido_id} falhou ao imprimir.")
        atualizar_status(pedido_id, "Erro")


def loop_principal():
    print(f"[Agente] Iniciado. Consultando {CLOUD_URL} a cada {INTERVALO_SEGUNDOS}s.")
    print(f"[Agente] Só imprime entre {HORARIO_INICIO.strftime('%H:%M')} e {HORARIO_FIM.strftime('%H:%M')}.")

    while True:
        try:
            if dentro_do_horario_de_impressao():
                for pedido in buscar_pendentes():
                    processar_pedido(pedido)
            else:
                print("[Agente] Fora do horário de impressão — aguardando.")
        except Exception as e:
            print(f"[Agente] Erro no ciclo (tentando de novo no próximo intervalo): {e}")

        time_module.sleep(INTERVALO_SEGUNDOS)


if __name__ == "__main__":
    if not CLOUD_URL:
        raise SystemExit("Defina CLOUD_URL no .env deste computador (veja agente.env.example).")
    if not AGENTE_API_KEY:
        raise SystemExit("Defina AGENTE_API_KEY no .env deste computador (veja agente.env.example).")
    loop_principal()
