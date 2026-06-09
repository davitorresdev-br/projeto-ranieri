import win32print
import win32api

def enviar_para_impressora(arquivo_caminho, copias, cor, frente_verso, acabamento):
    """
    Se comunica com o spooler do Windows e altera as propriedades do driver em tempo de execução.
    """
    # 1. Captura a impressora padrão do sistema do TI
    nome_impressora = win32print.GetDefaultPrinter()
    
    # 2. Abre a conexão com a impressora para modificar propriedades do Driver (DEVMODE)
    handle_impressora = win32print.OpenPrinter(nome_impressora)
    propriedades = win32print.GetPrinter(handle_impressora, 2)
    devmode = propriedades['pDevMode']
    
    # 3. Injeta os parâmetros passados pelo formulário do professor no Driver
    devmode.Copies = copias
    
    # Configuração de Cor vs P/B no driver
    if cor == "PB":
        devmode.Color = 1 # 1 costuma ser Monocromático na maioria dos drivers
    else:
        devmode.Color = 2 # 2 para Colorido

    # Configuração de Frente e Verso (Duplex)
    if frente_verso == "Frente e Verso":
        devmode.Duplex = 2 # 2 = Duplex pelo lado longo (Vertical/Padrão)
    else:
        devmode.Duplex = 1 # 1 = Simplex (Apenas frente)

    # 4. Atualiza o spooler com as novas configurações do Job atual
    win32print.SetPrinter(handle_impressora, 2, propriedades, 0)
    
    # 5. Executa a ação de impressão silenciosa via Shell do Windows utilizando o Driver modificado
    try:
        # O verbo "printto" envia direto para a impressora especificada sem abrir o Adobe Reader
        win32api.ShellExecute(
            0, 
            "printto", 
            arquivo_caminho, 
            f'"{nome_impressora}"', 
            ".", 
            0
        )
        print(f"Sucesso: {copias} cópias enviadas para {nome_impressora} (Turma: {acabamento}).")
    except Exception as e:
        print(f"Erro ao conversar com o driver da impressora: {e}")
    finally:
        win32print.ClosePrinter(handle_impressora)