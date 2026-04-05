import tkinter as tk
from tkinter import ttk, messagebox
from database import get_config, save_viagem, cadastrar_usuario, verificar_login 

class MainInterface:
    def __init__(self, root, calculator):
        self.root = root
        self.calc = calculator
        self.root.title("Co-Piloto")
        self.root.geometry("600x800")
        
        self.container = tk.Frame(self.root)
        self.container.pack(fill="both", expand=True)

        self.usuario_logado = None
        self.mostrar_login()

    def limpar_tela(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    def mostrar_login(self):
        self.limpar_tela()

        frame = tk.Frame(self.container, pady=50)
        frame.pack()

        tk.Label(frame, text=" Login Co-Piloto", font=("Arial", 18, "bold")).pack(pady=20)

        tk.Label(frame, text="E-mail:").pack(anchor="w")
        self.ent_email_login = ttk.Entry(frame, width=30)
        self.ent_email_login.pack(pady=5)

        tk.Label(frame, text="Senha:").pack(anchor="w")
        self.ent_senha_login = ttk.Entry(frame, show="*", width=30)
        self.ent_senha_login.pack(pady=5)

        ttk.Button(frame, text="Entrar", command=self.executar_login).pack(pady=15)
        
        tk.Label(frame, text="Ainda não tem conta?").pack(pady=(20, 0))
        ttk.Button(frame, text="Criar Conta", command=self.mostrar_cadastro).pack(pady=5)

    def executar_login(self):
        email = self.ent_email_login.get()
        senha = self.ent_senha_login.get()
        
        user = verificar_login(email, senha)
        
        if user:
            self.usuario_logado = user
            self.setup_ui() 
        else:
            messagebox.showerror("Erro", "E-mail ou senha incorretos.")

    def mostrar_cadastro(self):
        self.limpar_tela()
        
        frame = tk.Frame(self.container, pady=30)
        frame.pack()

        tk.Label(frame, text="📝 Criar Nova Conta", font=("Arial", 18, "bold")).pack(pady=20)

        campos = ["Nome", "E-mail", "Senha", "Cidade Base", "Consumo Cidade (km/L)", "Consumo Estrada (km/L)"]
        self.ents_cadastro = {}

        for campo in campos:
            tk.Label(frame, text=f"{campo}:").pack(anchor="w")
            ent = ttk.Entry(frame, width=35)
            if campo == "Senha":
                ent.config(show="*")
            ent.pack(pady=5)
            self.ents_cadastro[campo] = ent

        ttk.Button(frame, text="Salvar Cadastro", command=self.executar_cadastro).pack(pady=20)
        ttk.Button(frame, text="Voltar para Login", command=self.mostrar_login).pack()

    def executar_cadastro(self):
        try:
            nome = self.ents_cadastro["Nome"].get()
            email = self.ents_cadastro["E-mail"].get()
            senha = self.ents_cadastro["Senha"].get()
            cidade = self.ents_cadastro["Cidade Base"].get()
            cons_c = float(self.ents_cadastro["Consumo Cidade (km/L)"].get().replace(",", "."))
            cons_e = float(self.ents_cadastro["Consumo Estrada (km/L)"].get().replace(",", "."))
            
            if cadastrar_usuario(nome, email, senha, cidade, cons_c, cons_e):
                messagebox.showinfo("Sucesso", "Conta criada com sucesso! Faça seu login.")
                self.mostrar_login()
            else:
                messagebox.showerror("Erro", "Este e-mail já está cadastrado.")
        except ValueError:
            messagebox.showerror("Erro", "Os campos de consumo devem ser numéricos.")

    def setup_ui(self):
        self.limpar_tela() 
        self.cidade = self.usuario_logado[2]
        self.consumo_padrao = self.usuario_logado[3]

        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        menu_gestao = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Gestão", menu=menu_gestao)
        menu_gestao.add_command(label="Passageiros/Grupos", command=lambda: messagebox.showinfo("Breve", "Tela de Grupos"))
        menu_gestao.add_command(label="Histórico de Pagamentos", command=lambda: messagebox.showinfo("Breve", "Tela Financeira"))
        menu_gestao.add_separator()
        menu_gestao.add_command(label="Sair (Logout)", command=self.mostrar_login)

        self.lbl_status = tk.Label(self.container, text=f"📍 Bem-vindo, {self.usuario_logado[1]} | {self.cidade}", bg="#333", fg="white", pady=5)
        self.lbl_status.pack(fill="x")

        frame_rotas = ttk.LabelFrame(self.container, text="Planejamento Geral")
        frame_rotas.pack(padx=10, pady=5, fill="x")

        ttk.Label(frame_rotas, text="Origem:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.ent_origem = ttk.Entry(frame_rotas, width=40)
        self.ent_origem.grid(row=0, column=1, columnspan=3, pady=5, sticky="w")

        ttk.Label(frame_rotas, text="Destino Final:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.ent_destino = ttk.Entry(frame_rotas, width=40)
        self.ent_destino.grid(row=1, column=1, columnspan=3, pady=5, sticky="w")

        ttk.Label(frame_rotas, text="Consumo do Dia (km/L):").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        self.ent_consumo = ttk.Entry(frame_rotas, width=10)
        self.ent_consumo.insert(0, str(self.consumo_padrao))
        self.ent_consumo.grid(row=2, column=1, pady=5, sticky="w")

        ttk.Label(frame_rotas, text="Tipo de Rateio:").grid(row=2, column=2, padx=5, pady=5, sticky="e")
        self.combo_rateio = ttk.Combobox(frame_rotas, values=["Divisão Justa (Desvio)", "Dividir Igual", "Cobrar Integral"], state="readonly", width=20)
        self.combo_rateio.current(0)
        self.combo_rateio.grid(row=2, column=3, pady=5, sticky="w")

        ttk.Label(frame_rotas, text="Preço Gasolina (R$):").grid(row=3, column=0, padx=5, pady=5, sticky="e")
        self.ent_gasolina = ttk.Entry(frame_rotas, width=10)
        self.ent_gasolina.grid(row=3, column=1, pady=5, sticky="w")

        self.frame_paradas = ttk.LabelFrame(self.container, text="Paradas (Passageiros)")
        self.frame_paradas.pack(padx=10, pady=5, fill="x")
        
        self.lista_paradas_widgets = [] 
        ttk.Button(self.frame_paradas, text="➕ Adicionar Parada", command=self.adicionar_campo_parada).pack(pady=5)
        
        self.adicionar_campo_parada()

        frame_botoes = tk.Frame(self.container)
        frame_botoes.pack(pady=10)
        ttk.Button(frame_botoes, text="🚀 Calcular Preço Justo", command=self.executar_calculo).pack(side="left", padx=5)
        ttk.Button(frame_botoes, text="🌍 Abrir Mapa Visual", command=self.calc.abrir_mapa_visual).pack(side="left", padx=5)

        self.txt_out = tk.Text(self.container, height=12, bg="#f9f9f9")
        self.txt_out.pack(padx=10, pady=10, fill="both", expand=True)

    def adicionar_campo_parada(self):
        linha = ttk.Frame(self.frame_paradas, style="Card.TFrame")
        linha.pack(pady=2)
        
        ent_nome = ttk.Entry(linha, width=12)
        ent_nome.insert(0, "Nome")
        ent_nome.pack(side="left", padx=2)
        
        ent_end = ttk.Entry(linha, width=22)
        ent_end.insert(0, "Rua X, 10, Campinas")
        ent_end.pack(side="left", padx=2)
        
        combo_acao = ttk.Combobox(linha, values=["Embarca", "Desembarca"], state="readonly", width=12)
        combo_acao.current(0)
        combo_acao.pack(side="left", padx=2)
        
        self.lista_paradas_widgets.append({"nome": ent_nome, "endereco": ent_end, "acao": combo_acao})

    def executar_calculo(self):
        origem = self.ent_origem.get()
        destino = self.ent_destino.get()
        
        try:
            consumo_atual = float(self.ent_consumo.get().replace(",", "."))
            preco_gasolina = float(self.ent_gasolina.get().replace(",", "."))
        except ValueError:
            messagebox.showerror("Erro", "Por favor, preencha Consumo e Preço Gasolina com números válidos!")
            return

        custo_km = preco_gasolina / consumo_atual
        tipo_rateio = self.combo_rateio.get()

        paradas_formatadas = []
        for p in self.lista_paradas_widgets:
            nome = p["nome"].get()
            endereco = p["endereco"].get()
            acao = p["acao"].get()
            if nome and endereco: 
                paradas_formatadas.append({"nome": nome, "endereco": endereco, "acao": acao})

        res = self.calc.calcular(origem, destino, paradas_formatadas, self.cidade, custo_km, tipo_rateio)
        
        if res:
            self.txt_out.delete(1.0, tk.END)
            self.txt_out.insert(tk.END, res['texto'])
            if messagebox.askyesno("Salvar", "Deseja registrar essa viagem no histórico?"):
                save_viagem(paradas_formatadas, res['valor_total'], self.usuario_logado[0]) 
                messagebox.showinfo("Sucesso", "Registrado no Histórico!")