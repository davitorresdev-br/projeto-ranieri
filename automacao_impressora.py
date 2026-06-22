import subprocess

def mapear_fila_impressora(cor, acabamento):
    """
    Cruza as opções escolhidas pelo professor para determinar a fila da Konica Minolta.
    """
    is_colorido = "Colorido" in str(cor)
    is_grampeado = "Grampeada" in str(acabamento)

    if is_colorido:
        return "Konica_Color_Grampo" if is_grampeado else "Konica_Color_Padrao"
    else:
        return "Konica_PB_Grampo" if is_grampeado else "Konica_PB_Padrao"


# CORRIGIDO: a função aceitava só 5 parâmetros, mas o app.py sempre chamou
# com 8 (professor_nome, materia, turma, filepath, copias, cor,
# frente_verso, acabamento). Isso fazia TODO envio de impressão falhar
# com um TypeError antes mesmo de chegar à impressora.
def disparar_impressao_windows(professor_nome, materia, turma, caminho_pdf, copias, cor, frente_verso, acabamento):
    nome_impressora = mapear_fila_impressora(cor, acabamento)

    # Montamos o comando como uma STRING única, com aspas duplas (") ao
    # redor do arquivo e da impressora, exatamente como já validado antes.
    comando = f'PDFtoPrinter.exe "{caminho_pdf}" "{nome_impressora}" /copies={copias}'

    if "Frente e Verso" in str(frente_verso):
        comando += " /duplex"

    print(f"💻 [Pedido] {professor_nome} — {materia} ({turma})")
    print(f"💻 [Terminal Windows] Executando: {comando}")

    try:
        subprocess.run(comando, check=True, shell=True)
        print(f"🖨️ [Sucesso] Enviado para a fila '{nome_impressora}'")
        return True
    except subprocess.CalledProcessError:
        print(f"❌ [Erro] Falha ao comunicar com o driver do Windows. Verifique se a impressora '{nome_impressora}' existe.")
        return False
