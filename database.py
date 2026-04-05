import sqlite3
from datetime import datetime

def init_db():
    conn = sqlite3.connect('copiloto.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, email TEXT UNIQUE, senha TEXT, cidade_base TEXT, consumo_cidade REAL, consumo_estrada REAL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS historico 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, id_usuario INTEGER, passageiro TEXT, data TEXT, valor REAL, status TEXT)''')
    conn.commit()
    conn.close()

def cadastrar_usuario(nome, email, senha, cidade, cons_cidade, cons_estrada):
    try:
        conn = sqlite3.connect('copiloto.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO usuarios (nome, email, senha, cidade_base, consumo_cidade, consumo_estrada) VALUES (?, ?, ?, ?, ?, ?)", 
                       (nome, email, senha, cidade, cons_cidade, cons_estrada))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

def verificar_login(email, senha):
    conn = sqlite3.connect('copiloto.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome, cidade_base, consumo_cidade, consumo_estrada FROM usuarios WHERE email = ? AND senha = ?", (email, senha))
    user = cursor.fetchone()
    conn.close()
    return user 

def save_viagem(lista_paradas, valor_total, id_usuario):
    """Salva a viagem no histórico, juntando o nome de todos os passageiros"""
    nomes = list(set([p['nome'] for p in lista_paradas]))
    passageiros_str = ", ".join(nomes)
    
    data_atual = datetime.now().strftime("%d/%m/%Y")
    
    conn = sqlite3.connect('copiloto.db')
    cursor = conn.cursor()
    
    cursor.execute("INSERT INTO historico (id_usuario, passageiro, data, valor, status) VALUES (?, ?, ?, ?, ?)",
                   (id_usuario, passageiros_str, data_atual, valor_total, "Pendente"))
    
    conn.commit()
    conn.close()