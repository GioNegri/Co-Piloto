import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import Calendar
import sqlite3
import webbrowser
import urllib.parse

def init_db_gestao():
    conn = sqlite3.connect('copiloto.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS passageiros 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, email TEXT, grupo TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS viagens_diarias 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, id_passageiro INTEGER, valor REAL, pago INTEGER)''')
    conn.commit()
    conn.close()

class TelaGestao:
    def __init__(self, parent_root):
        init_db_gestao()
        self.win = tk.Toplevel(parent_root)
        self.win.title("Gestão de Viagens e Pagamentos")
        self.win.geometry("850x700")
        self.win.configure(bg="#0f172a")
        
        notebook = ttk.Notebook(self.win)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Cria as 3 Abas
        self.aba_cad = ttk.Frame(notebook)
        notebook.add(self.aba_cad, text="👥 1. Cadastrar Pessoas")
        self.setup_cadastro()

        self.aba_lancamento = ttk.Frame(notebook)
        notebook.add(self.aba_lancamento, text="🚗 2. Lançar Carona do Dia")
        self.setup_lancamento()

        self.aba_cobranca = ttk.Frame(notebook)
        notebook.add(self.aba_cobranca, text="💰 3. Cobranças e E-mails")
        self.setup_cobranca()

    def setup_cadastro(self):
        frame = ttk.Frame(self.aba_cad, padding=25)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Adicionar Novo Passageiro", font=("Segoe UI", 16, "bold")).pack(pady=10)
        
        ttk.Label(frame, text="Nome:").pack(anchor="w")
        self.ent_nome = ttk.Entry(frame, width=45); self.ent_nome.pack(pady=5)
        
        ttk.Label(frame, text="E-mail (Para enviar a cobrança depois):").pack(anchor="w")
        self.ent_email = ttk.Entry(frame, width=45); self.ent_email.pack(pady=5)
        
        ttk.Label(frame, text="Grupo:").pack(anchor="w")
        self.combo_grupo_cad = ttk.Combobox(frame, values=["Trabalho", "Faculdade", "Avulso"], width=42)
        self.combo_grupo_cad.pack(pady=5)
        
        ttk.Button(frame, text="Salvar Passageiro", command=self.salvar_passageiro).pack(pady=20)

    def salvar_passageiro(self):
        nome = self.ent_nome.get().strip()
        email = self.ent_email.get().strip()
        grupo = self.combo_grupo_cad.get().strip()

        if not nome or not grupo:
            messagebox.showwarning("Erro", "Nome e Grupo são obrigatórios!")
            return

        conn = sqlite3.connect('copiloto.db')
        c = conn.cursor()
        c.execute("INSERT INTO passageiros (nome, email, grupo) VALUES (?, ?, ?)", (nome, email, grupo))
        conn.commit()
        conn.close()

        messagebox.showinfo("Sucesso", f"{nome} adicionado ao grupo {grupo}!")
        self.ent_nome.delete(0, tk.END)
        self.ent_email.delete(0, tk.END)

    def setup_lancamento(self):
        frame_esq = ttk.Frame(self.aba_lancamento, padding=10)
        frame_esq.pack(side="left", fill="y")

        ttk.Label(frame_esq, text="Data da Carona:").pack()
        self.cal = Calendar(frame_esq, selectmode='day', date_pattern='dd/mm/yyyy')
        self.cal.pack(pady=5)

        ttk.Label(frame_esq, text="Valor total a ser dividido (R$):").pack(pady=(10,0))
        self.ent_valor_dia = ttk.Entry(frame_esq, width=15)
        self.ent_valor_dia.pack()

        frame_dir = ttk.LabelFrame(self.aba_lancamento, text="Quem foi na carona hoje?", padding=10)
        frame_dir.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        ttk.Label(frame_dir, text="Selecione o Grupo:").pack(anchor="w")
        self.combo_grupo_lanc = ttk.Combobox(frame_dir, values=["Trabalho", "Faculdade", "Avulso"])
        self.combo_grupo_lanc.pack(anchor="w", pady=5)
        self.combo_grupo_lanc.bind("<<ComboboxSelected>>", self.carregar_checkboxes)

        self.frame_checks = ttk.Frame(frame_dir)
        self.frame_checks.pack(fill="both", expand=True, pady=10)

        self.vars_passageiros = {} 

        ttk.Button(frame_dir, text="✅ Registrar Carona para os Marcados", command=self.registrar_carona).pack(side="bottom", pady=10)

    def carregar_checkboxes(self, event=None):
        for widget in self.frame_checks.winfo_children():
            widget.destroy()
        self.vars_passageiros.clear()

        grupo = self.combo_grupo_lanc.get()
        conn = sqlite3.connect('copiloto.db')
        c = conn.cursor()
        c.execute("SELECT id, nome FROM passageiros WHERE grupo=?", (grupo,))
        pessoas = c.fetchall()
        conn.close()

        for pid, nome in pessoas:
            var = tk.BooleanVar()
            self.vars_passageiros[pid] = var
            chk = tk.Checkbutton(self.frame_checks, text=nome, variable=var)
            chk.pack(anchor="w")

    def registrar_carona(self):
        data = self.cal.get_date()
        try:
            valor_total = float(self.ent_valor_dia.get().replace(",", "."))
        except:
            messagebox.showerror("Erro", "Digite um valor numérico válido (ex: 15.50).")
            return

        ids_presentes = [pid for pid, var in self.vars_passageiros.items() if var.get()]
        
        if not ids_presentes:
            messagebox.showwarning("Erro", "Marque pelo menos uma pessoa que foi na carona.")
            return

        valor_por_pessoa = valor_total / len(ids_presentes)

        conn = sqlite3.connect('copiloto.db')
        c = conn.cursor()
        
        emails_para_notificar = [] 

        for pid in ids_presentes:
            
            c.execute("INSERT INTO viagens_diarias (data, id_passageiro, valor, pago) VALUES (?, ?, ?, 0)", 
                      (data, pid, valor_por_pessoa))
            
            c.execute("SELECT email FROM passageiros WHERE id=?", (pid,))
            resultado = c.fetchone()
            if resultado and resultado[0]: 
                emails_para_notificar.append(resultado[0])

        conn.commit()
        conn.close()

        messagebox.showinfo("Sucesso", f"Registrado! R$ {valor_por_pessoa:.2f} na conta de cada um.")
        self.carregar_pendencias() 

        if emails_para_notificar:
            destinatarios = ",".join(emails_para_notificar)
            assunto = urllib.parse.quote(f"Resumo da Carona - {data}")
            corpo = urllib.parse.quote(f"Fala pessoal!\n\nA carona de hoje ({data}) deu um total de R$ {valor_por_pessoa:.2f} para cada passageiro.\n\n                         O valor já foi adicionado na conta de vocês no app Co-Piloto.")                      
            link_gmail = f"https://mail.google.com/mail/?view=cm&fs=1&to={destinatarios}&su={assunto}&body={corpo}"
            webbrowser.open(link_gmail)

    def setup_cobranca(self):
        frame = ttk.Frame(self.aba_cobranca, padding=10)
        frame.pack(fill="both", expand=True)

        ttk.Button(frame, text="🔄 Atualizar Lista de Devedores", command=self.carregar_pendencias).pack(pady=5)

        colunas = ("ID", "Nome", "Grupo", "Total Devido (R$)", "E-mail")
        style = ttk.Style()
        style.configure("Treeview",
            rowheight=28,
            font=("Segoe UI", 10)
        )

        style.configure("Treeview.Heading",
        font=("Segoe UI", 10, "bold")
        )
        self.tree = ttk.Treeview(frame, columns=colunas, show="headings", height=10)
        for col in colunas:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120, anchor="center")
        self.tree.pack(fill="both", expand=True, pady=10)

        frame_botoes = ttk.Frame(frame)
        frame_botoes.pack(fill="x", pady=10)

        ttk.Button(frame_botoes, text="Enviar E-mail de Cobrança", command=self.cobrar_selecionado).pack(side="left", padx=10)
        ttk.Button(frame_botoes, text=" Marcar como Pago (Zerar Dívida)", command=self.marcar_pago).pack(side="right", padx=10)

    def carregar_pendencias(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        conn = sqlite3.connect('copiloto.db')
        c = conn.cursor()
        c.execute('''SELECT p.id, p.nome, p.grupo, SUM(v.valor), p.email 
                     FROM passageiros p
                     JOIN viagens_diarias v ON p.id = v.id_passageiro
                     WHERE v.pago = 0
                     GROUP BY p.id''')
        devedores = c.fetchall()
        conn.close()

        for d in devedores:            
            valor_formatado = f"{d[3]:.2f}" if d[3] else "0.00"
            self.tree.insert("", "end", values=(d[0], d[1], d[2], valor_formatado, d[4]))

    def enviar_email_pendencia(self):
        selecionado = self.tree.selection()
        if not selecionado:
            messagebox.showwarning("Aviso", "Selecione uma pessoa na lista.")
            return
        
        item = self.tree.item(selecionado[0])['values']
        id_pass = item[0]
        nome = item[1]
        email = item[4]

        if not email or email == "None":
            messagebox.showerror("Erro", "Esta pessoa não tem e-mail cadastrado.")
            return

        # BUSCA TODAS AS PENDÊNCIAS NO BANCO
        conn = sqlite3.connect('copiloto.db')
        c = conn.cursor()
        c.execute("SELECT data, valor FROM viagens_diarias WHERE id_passageiro = ? AND pago = 0", (id_pass,))
        pendencias = c.fetchall()
        conn.close()

        if not pendencias:
            messagebox.showinfo("Info", "Não há pendências para este passageiro.")
            return


        texto_lista = ""
        total_geral = 0
        for data, valor in pendencias:
            texto_lista += f"- Dia {data}: R$ {valor:.2f}%0A" # %0A é quebra de linha no link
            total_geral += valor

        assunto = urllib.parse.quote(f"Pendências de Carona - {nome} ")
        corpo = urllib.parse.quote(
            f"Olá {nome}!\n\nEstou passando para enviar o resumo das suas caronas pendentes:\n\n"
        ) + texto_lista + urllib.parse.quote(
            f"\nTotal acumulado: R$ {total_geral:.2f}\n\nQualquer dúvida me avisa!"
        )
        
        link_gmail = f"https://mail.google.com/mail/?view=cm&fs=1&to={email}&su={assunto}&body={corpo}"
        webbrowser.open(link_gmail)

    def marcar_pago(self):
        selecionado = self.tree.selection()
        if not selecionado:
            return
        
        id_pass = self.tree.item(selecionado[0])['values'][0]
        nome = self.tree.item(selecionado[0])['values'][1]

        if messagebox.askyesno("Confirmar", f"Tem certeza que deseja zerar a dívida de {nome}?"):
            conn = sqlite3.connect('copiloto.db')
            c = conn.cursor()
        
            c.execute("UPDATE viagens_diarias SET pago = 1 WHERE id_passageiro = ?", (id_pass,))
            conn.commit()
            conn.close()
            self.carregar_pendencias()