import sqlite3

def init_db():
    conn = sqlite3.connect('acalanto_print.db')
    cursor = conn.cursor()
    
    # Criando a tabela de pedidos de impressão
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            turma TEXT NOT NULL,
            copias INTEGER NOT NULL,
            cor TEXT NOT NULL,
            frente_verso TEXT NOT NULL,
            acabamento TEXT NOT NULL,
            arquivo_path TEXT NOT NULL,
            status TEXT DEFAULT 'Pendente',
            data_pedido TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Banco de dados do Instituto Acalanto inicializado com sucesso!")

if __name__ == "__main__":
    init_db()