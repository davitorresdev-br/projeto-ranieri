from flask import Flask, render_template_string, request, redirect, url_for
import sqlite3
import os
from werkzeug.utils import secure_filename
from automacao_impressora import enviar_para_impressora

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Template HTML inline aplicando a paleta do Instituto Acalanto (Azul, Vermelho, Amarelo)
HTML_FORMULARIO = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <title>Instituto Acalanto - Sistema de Impressão</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100">
    <header class="bg-[#1E3A8A] text-white p-4 shadow-md border-b-4 border-[#DC2626]">
        <div class="container mx-auto flex justify-between items-center">
            <h1 class="text-2xl font-bold tracking-wider">INSTITUTO ACALANTO DE ENSINO</h1>
            <span class="bg-[#FBBF24] text-gray-900 font-bold px-3 py-1 rounded text-sm">Ranieri</span>
        </div>
    </header>

    <main class="container mx-auto mt-10 max-w-lg bg-white p-8 rounded-lg shadow-xl border-t-4 border-[#1E3A8A]">
        <h2 class="text-xl font-bold mb-6 text-gray-800 text-center border-b pb-2">Solicitação de Impressão (TI)</h2>
        
        <form action="/enviar" method="POST" enctype="multipart/form-data" class="space-y-4">
            <div>
                <label class="block text-gray-700 font-medium">1. Qual a Turma?</label>
                <input type="text" name="turma" required class="w-full p-2 border rounded focus:outline-none focus:border-[#1E3A8A]">
            </div>
            
            <div>
                <label class="block text-gray-700 font-medium">2. Número de Cópias?</label>
                <input type="number" name="copias" min="1" required class="w-full p-2 border rounded focus:outline-none focus:border-[#1E3A8A]">
            </div>
            
            <div>
                <label class="block text-gray-700 font-medium">3. Tipo de Cor</label>
                <select name="cor" class="w-full p-2 border rounded">
                    <option value="PB">Preto e Branco (P/B)</option>
                    <option value="Colorida">Colorida</option>
                </select>
            </div>

            <div>
                <label class="block text-gray-700 font-medium">4. Modo de Página</label>
                <select name="frente_verso" class="w-full p-2 border rounded">
                    <option value="Apenas Frente">Apenas Frente</option>
                    <option value="Frente e Verso">Frente e Verso</option>
                </select>
            </div>

            <div>
                <label class="block text-gray-700 font-medium">5. Acabamento</label>
                <select name="acabamento" class="w-full p-2 border rounded">
                    <option value="Normal">Normal</option>
                    <option value="Grampeada">Grampeada</option>
                </select>
            </div>

            <div>
                <label class="block text-gray-700 font-medium">6. Anexo da Prova (Apenas PDF)</label>
                <input type="file" name="arquivo" accept=".pdf" required class="w-full p-2 border rounded bg-gray-50">
            </div>

            <button type="submit" class="w-full bg-[#1E3A8A] hover:bg-[#152a66] text-white font-bold py-3 rounded transition-colors border-b-4 border-[#DC2626]">
                Enviar para o TI & Impressora
            </button>
        </form>
    </main>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_FORMULARIO)

@app.route('/enviar', methods=['POST'])
def enviar():
    turma = request.form['turma']
    copias = int(request.form['copias'])
    cor = request.form['cor']
    frente_verso = request.form['frente_verso']
    acabamento = request.form['acabamento']
    arquivo = request.files['arquivo']
    
    if arquivo:
        filename = secure_filename(arquivo.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        arquivo.save(filepath)
        
        # Salva no Banco de Dados
        conn = sqlite3.connect('acalanto_print.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO pedidos (turma, copias, cor, frente_verso, acabamento, arquivo_path)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (turma, copias, cor, frente_verso, acabamento, filepath))
        conn.commit()
        conn.close()
        
        # Dispara o Gatilho de Automação do Driver da Impressora
        enviar_para_impressora(filepath, copias, cor, frente_verso, acabamento)
        
        return "<h1>Pedido registrado e enviado para a fila da impressora com sucesso!</h1><a href='/'>Voltar</a>"

if __name__ == '__main__':
    app.run(debug=True, port=5000)