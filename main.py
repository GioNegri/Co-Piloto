import requests
from geopy.geocoders import Nominatim
from geopy.distance import geodesic # A MÁGICA ENTRA AQUI!
import folium
import webbrowser
import os
import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import Calendar
import sqlite3
import urllib.parse
from database import init_db, cadastrar_usuario, verificar_login, save_viagem
import threading
import time

class CaronaEngine:
    def __init__(self):
        self.geolocator = Nominatim(user_agent="Copiloto_Giovanne_App_Final")
        self.rota_coords = []
        self.pontos_para_marcar = []
    
    def pegar_coordenadas(self, endereco):
        time.sleep(1.1) 
        try:
            local = self.geolocator.geocode(endereco, timeout=10)
            if local: return local.longitude, local.latitude
            
            local_br = self.geolocator.geocode(f"{endereco}, Brasil", timeout=10)
            if local_br: return local_br.longitude, local_br.latitude
            
            if "-" in endereco:
                endereco_limpo = endereco.split("-")[0].strip()
                local_limpo = self.geolocator.geocode(f"{endereco_limpo}, Brasil", timeout=10)
                if local_limpo: return local_limpo.longitude, local_limpo.latitude

            partes = endereco.split(",")
            if len(partes) >= 3:
                endereco_curto = f"{partes[0].strip()}, {partes[-1].replace('-', '').strip()}, Brasil"
                local_curto = self.geolocator.geocode(endereco_curto, timeout=10)
                if local_curto: return local_curto.longitude, local_curto.latitude

            return None
        except Exception as e:
            print(f"Erro ao geocodificar: {e}")
            return None
        
    def calcular(self, origem, destino, paradas_formatadas, cidade, custo_km, tipo_rateio):
        coords_origem = self.pegar_coordenadas(f"{origem}, {cidade}")
        coords_destino = self.pegar_coordenadas(f"{destino}, {cidade}")

        if not coords_origem or not coords_destino:
            raise ValueError("Não encontrei a Origem ou o Destino. Verifique a digitação.")

        self.pontos_para_marcar = [
            {"nome": "Início: " + origem, "coords": [coords_origem[1], coords_origem[0]], "cor": "green"}
        ]
        self.rota_coords = [[coords_origem[1], coords_origem[0]]]

        dist_solo = geodesic((coords_origem[1], coords_origem[0]), (coords_destino[1], coords_destino[0])).km * 1.3

        pontos_roteiro = [{"nome": "Origem", "coords": coords_origem, "acao": "Embarca"}]
        for p in paradas_formatadas:
            coords = self.pegar_coordenadas(f"{p['endereco']}, {cidade}")
            if coords:
                pontos_roteiro.append({"nome": p['nome'], "coords": coords, "acao": p['acao']})
                self.pontos_para_marcar.append({
                    "nome": f"Parada: {p['nome']} ({p['acao']})",
                    "coords": [coords[1], coords[0]],
                    "cor": "blue"
                })
                self.rota_coords.append([coords[1], coords[0]]) # Adiciona linha pro mapa
                
        pontos_roteiro.append({"nome": "Destino Final", "coords": coords_destino, "acao": "Desembarca"})
        self.pontos_para_marcar.append({"nome": "Fim: " + destino, "coords": [coords_destino[1], coords_destino[0]], "cor": "red"})
        self.rota_coords.append([coords_destino[1], coords_destino[0]]) # Termina a linha no mapa

        dist_total = 0.0
        dividas = {p['nome']: 0.0 for p in paradas_formatadas}
        passageiros_no_carro = set([p['nome'] for p in paradas_formatadas if p['acao'] == 'Desembarca'])

        texto_saida = f"🛣️ === RESUMO DO ROTEIRO === 🛣️\n"
        texto_saida += f"Rateio: {tipo_rateio} | Custo: R$ {custo_km:.2f}/km\n\n"

        # --- CÁLCULO DOS TRECHOS (MATEMÁTICO) ---
        for i in range(len(pontos_roteiro) - 1):
            p_atual = pontos_roteiro[i]
            p_prox = pontos_roteiro[i+1]

            if p_atual["acao"] == "Embarca" and p_atual["nome"] != "Origem":
                passageiros_no_carro.add(p_atual["nome"])
            elif p_atual["acao"] == "Desembarca" and p_atual["nome"] != "Destino Final":
                if p_atual["nome"] in passageiros_no_carro:
                    passageiros_no_carro.remove(p_atual["nome"])

            # Distância matemática (linha reta * 1.3 fator rua)
            dist_trecho = geodesic((p_atual['coords'][1], p_atual['coords'][0]), (p_prox['coords'][1], p_prox['coords'][0])).km * 1.3
            dist_total += dist_trecho
            custo_trecho = dist_trecho * custo_km

            texto_saida += f"➡️ {p_atual['nome']} até {p_prox['nome']} ({dist_trecho:.2f} km)\n"
            texto_saida += f"   A bordo: {', '.join(passageiros_no_carro) if passageiros_no_carro else 'Só Motorista'}\n"

            if len(passageiros_no_carro) > 0:
                if tipo_rateio == "Dividir Igual":
                    fatia = custo_trecho / (len(passageiros_no_carro) + 1)
                    for nome in passageiros_no_carro: 
                        dividas[nome] += fatia
                elif tipo_rateio == "Cobrar Integral":
                    fatia = custo_trecho / len(passageiros_no_carro)
                    for nome in passageiros_no_carro: 
                        dividas[nome] += fatia

        if tipo_rateio == "Divisão Justa (Desvio)":
            desvio = max(0, dist_total - dist_solo)
            custo_desvio = desvio * custo_km
            custo_comum = dist_solo * custo_km
            if len(dividas) > 0:
                fatia_desvio = custo_desvio / len(dividas)
                fatia_comum = custo_comum / (len(dividas) + 1)
                for nome in dividas: 
                    dividas[nome] = fatia_desvio + fatia_comum

        texto_saida += f"\n💰 === FECHAMENTO FINAL === 💰\n"
        texto_saida += f"Rota Solo: {dist_solo:.2f} km | Rota Real: {dist_total:.2f} km\n\n"

        valor_total_arrecadado = 0
        for nome, valor in dividas.items():
            texto_saida += f"🔹 {nome} paga: R$ {valor:.2f}\n"
            valor_total_arrecadado += valor

        return {"texto": texto_saida, "valor_total": valor_total_arrecadado, "dividas": dividas}

    def abrir_mapa(self):
        if hasattr(self, 'rota_coords') and self.rota_coords and len(self.rota_coords) > 0:
            try:
                m = folium.Map(location=self.rota_coords[0], zoom_start=13, tiles='cartodbdark_matter')
                
                if len(self.rota_coords) > 1:
                    # Agora a linha liga os pontos diretamente
                    folium.PolyLine(self.rota_coords, color="#3b82f6", weight=5, opacity=0.8).add_to(m)
                
                for ponto in self.pontos_para_marcar:
                    folium.Marker(
                        location=ponto["coords"],
                        popup=ponto["nome"],
                        icon=folium.Icon(color=ponto["cor"], icon="info-sign")
                    ).add_to(m)
                
                m.save("mapa_intermunicipal.html")
                webbrowser.open('file://' + os.path.realpath("mapa_intermunicipal.html"))
            except Exception as e:
                print(f"Erro ao abrir mapa: {e}")
                messagebox.showwarning("Aviso", "Não foi possível gerar o mapa visual.")
            
    def abrir_mapa_visual(self):
        self.abrir_mapa()

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
        
        ttk.Label(frame, text="E-mail:").pack(anchor="w")
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

        self.ent_nome.delete(0, tk.END)
        self.ent_email.delete(0, tk.END)

        messagebox.showinfo("Sucesso", f"{nome} adicionado ao grupo {grupo}!")

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

        ttk.Button(frame_dir, text="✅ Registrar Carona", command=self.registrar_carona).pack(side="bottom", pady=10)

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
            messagebox.showwarning("Erro", "Marque pelo menos uma pessoa.")
            return

        valor_por_pessoa = valor_total / len(ids_presentes)
        conn = sqlite3.connect('copiloto.db')
        c = conn.cursor()
        emails_para_notificar = []

        for pid in ids_presentes:
            c.execute("INSERT INTO viagens_diarias (data, id_passageiro, valor, pago) VALUES (?, ?, ?, 0)", 
                    (data, pid, valor_por_pessoa))
            c.execute("SELECT email, nome FROM passageiros WHERE id=?", (pid,))
            resultado = c.fetchone()
            if resultado and resultado[0]: 
                emails_para_notificar.append({"email": resultado[0], "nome": resultado[1]})

        conn.commit()
        conn.close()

        messagebox.showinfo("Sucesso", f"Registrado! R$ {valor_por_pessoa:.2f} na conta de cada um.")
        self.carregar_pendencias() 

        if emails_para_notificar:
            self.mostrar_janela_email_resumo(data, valor_por_pessoa, emails_para_notificar)

    def setup_cobranca(self):
        frame = ttk.Frame(self.aba_cobranca, padding=10)
        frame.pack(fill="both", expand=True)

        ttk.Button(frame, text="🔄 Atualizar Lista", command=self.carregar_pendencias).pack(pady=5)

        colunas = ("ID", "Nome", "Grupo", "Total Devido (R$)", "E-mail")
        style = ttk.Style()
        style.configure("Treeview", rowheight=28, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
        
        self.tree = ttk.Treeview(frame, columns=colunas, show="headings", height=10)
        for col in colunas:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120, anchor="center")
        self.tree.pack(fill="both", expand=True, pady=10)

        frame_botoes = ttk.Frame(frame)
        frame_botoes.pack(fill="x", pady=10)

        ttk.Button(frame_botoes, text="✉️ Enviar E-mail de Pendências", command=self.enviar_email_pendencia).pack(side="left", padx=10)
        ttk.Button(frame_botoes, text="💸 Marcar como Pago", command=self.marcar_pago).pack(side="right", padx=10)

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
            texto_lista += f"  • Dia {data}: R$ {valor:.2f}\n"
            total_geral += valor

        self.mostrar_janela_email_pendencia(nome, email, texto_lista, total_geral)

    def marcar_pago(self):
        selecionado = self.tree.selection()
        if not selecionado: return
        
        id_pass = self.tree.item(selecionado[0])['values'][0]
        nome = self.tree.item(selecionado[0])['values'][1]

        if messagebox.askyesno("Confirmar", f"Zerar a dívida de {nome}?"):
            conn = sqlite3.connect('copiloto.db')
            c = conn.cursor()
            c.execute("UPDATE viagens_diarias SET pago = 1 WHERE id_passageiro = ?", (id_pass,))
            conn.commit()
            conn.close()
            self.carregar_pendencias()

    def mostrar_janela_email_resumo(self, data, valor_por_pessoa, emails_para_notificar):
        janela_email = tk.Toplevel(self.win)
        janela_email.title("📧 Enviar Email - Copie e Cole")
        janela_email.geometry("750x650")
        janela_email.configure(bg="#0f172a")
    
        frame = ttk.Frame(janela_email, padding=20)
        frame.pack(fill="both", expand=True)
    
        ttk.Label(frame, text="✉️ Texto do Email para os Passageiros", 
                font=("Segoe UI", 14, "bold")).pack(pady=10)
    
        destinatarios = ", ".join([p["email"] for p in emails_para_notificar])
        ttk.Label(frame, text=f"📧 Destinatários:", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(10,0))
    
        dest_area = tk.Text(frame, height=3, width=80, bg="#1e293b", fg="#3b82f6", 
                            insertbackground="white", wrap=tk.WORD, font=("Consolas", 10))
        dest_area.pack(fill="x", pady=5)
        dest_area.insert("1.0", destinatarios)
        dest_area.config(state="normal")
    
        assunto = f"Resumo da Carona - {data}"
        ttk.Label(frame, text=f"📝 Assunto:", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(10,0))
    
        assunto_area = tk.Text(frame, height=2, width=80, bg="#1e293b", fg="#e2e8f0", 
                               insertbackground="white", wrap=tk.WORD, font=("Consolas", 10))
        assunto_area.pack(fill="x", pady=5)
        assunto_area.insert("1.0", assunto)
        assunto_area.config(state="normal")
    
        # Corpo do email
        corpo = f"""Olá pessoal!

    A carona de hoje ({data}) deu um total de R$ {valor_por_pessoa:.2f} para cada passageiro.

    O valor já foi adicionado na conta de vocês no aplicativo.

    Atenciosamente, """
    
        ttk.Label(frame, text="📄 Corpo do Email (selecione e copie abaixo):", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(10,0))
    
        text_area = tk.Text(frame, height=12, width=80, bg="#1e293b", fg="#e2e8f0", 
                        insertbackground="white", wrap=tk.WORD, font=("Consolas", 10))
        text_area.pack(fill="both", expand=True, pady=10)
        text_area.insert("1.0", corpo)
        text_area.config(state="normal")

        botoes_frame = ttk.Frame(frame)
        botoes_frame.pack(fill="x", pady=10)
    

        def copiar_destinatarios():
            janela_email.clipboard_clear()
            janela_email.clipboard_append(destinatarios)
            messagebox.showinfo("Copiado!", "Destinatários copiados para a área de transferência!")
    
        ttk.Button(botoes_frame, text="📋 Copiar Destinatários", 
                   command=copiar_destinatarios).pack(side="left", padx=5)
    

        def copiar_assunto():
            janela_email.clipboard_clear()
            janela_email.clipboard_append(assunto)
            messagebox.showinfo("Copiado!", "Assunto copiado para a área de transferência!")
    
        ttk.Button(botoes_frame, text="📋 Copiar Assunto", 
                   command=copiar_assunto).pack(side="left", padx=5)
    

        def copiar_corpo():
            janela_email.clipboard_clear()
            janela_email.clipboard_append(corpo)
            messagebox.showinfo("Copiado!", "Corpo do email copiado para a área de transferência!")
    
        ttk.Button(botoes_frame, text="📋 Copiar Corpo do Email", 
                   command=copiar_corpo).pack(side="left", padx=5)
    

        def selecionar_tudo():
            text_area.tag_add("sel", "1.0", "end")
            text_area.focus()
    
        ttk.Button(botoes_frame, text="🔍 Selecionar Tudo no Corpo", 
               command=selecionar_tudo).pack(side="left", padx=5)

        ttk.Button(botoes_frame, text="❌ Fechar", command=janela_email.destroy).pack(side="right", padx=5)
    
        
        ttk.Label(frame, text="💡 Dica: Use os botões para copiar cada campo separadamente, ou selecione o texto manualmente.", 
                  font=("Segoe UI", 9), foreground="#94a3b8").pack(pady=5)

    def mostrar_janela_email_pendencia(self, nome, email, texto_lista, total_geral):
    
        janela_email = tk.Toplevel(self.win)
        janela_email.title("📧 Enviar Email de Pendência - Copie e Cole")
        janela_email.geometry("750x700")
        janela_email.configure(bg="#0f172a")
    

        frame = ttk.Frame(janela_email, padding=20)
        frame.pack(fill="both", expand=True)
    
        ttk.Label(frame, text="✉️ Email de Cobrança", 
                  font=("Segoe UI", 14, "bold")).pack(pady=10)

        ttk.Label(frame, text=f"📧 Para:", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(10,0))
    
        dest_area = tk.Text(frame, height=2, width=80, bg="#1e293b", fg="#3b82f6", 
                            insertbackground="white", wrap=tk.WORD, font=("Consolas", 10))
        dest_area.pack(fill="x", pady=5)
        dest_area.insert("1.0", email)
        dest_area.config(state="normal")
    
        assunto = f"Pendências de Carona - {nome}"
        ttk.Label(frame, text=f"📝 Assunto:", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(10,0))
    
        assunto_area = tk.Text(frame, height=2, width=80, bg="#1e293b", fg="#e2e8f0", 
                               insertbackground="white", wrap=tk.WORD, font=("Consolas", 10))
        assunto_area.pack(fill="x", pady=5)
        assunto_area.insert("1.0", assunto)
        assunto_area.config(state="normal")
    
        corpo = f"""Olá {nome}!

    Estou passando para enviar o resumo das suas caronas pendentes:

    {texto_lista}
    Total acumulado: R$ {total_geral:.2f}

    Qualquer dúvida me avisa!

    Atenciosamente,
    Co-Piloto 🚗"""
    
        ttk.Label(frame, text="📄 Corpo do Email (selecione e copie abaixo):", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(10,0))
    
        text_area = tk.Text(frame, height=15, width=80, bg="#1e293b", fg="#e2e8f0", 
                            insertbackground="white", wrap=tk.WORD, font=("Consolas", 10))
        text_area.pack(fill="both", expand=True, pady=10)
        text_area.insert("1.0", corpo)
        text_area.config(state="normal")

        botoes_frame = ttk.Frame(frame)
        botoes_frame.pack(fill="x", pady=10)
    
        def copiar_destinatario():
            janela_email.clipboard_clear()
            janela_email.clipboard_append(email)
            messagebox.showinfo("Copiado!", "Destinatário copiado para a área de transferência!")
    
        ttk.Button(botoes_frame, text="📋 Copiar Destinatário", 
                command=copiar_destinatario).pack(side="left", padx=5)
    
    # Botão para copiar assunto
        def copiar_assunto():
            janela_email.clipboard_clear()
            janela_email.clipboard_append(assunto)
            messagebox.showinfo("Copiado!", "Assunto copiado para a área de transferência!")
    
        ttk.Button(botoes_frame, text="📋 Copiar Assunto", 
                command=copiar_assunto).pack(side="left", padx=5)
    
    # Botão para copiar corpo do email
        def copiar_corpo():
            janela_email.clipboard_clear()
            janela_email.clipboard_append(corpo)
            messagebox.showinfo("Copiado!", "Corpo do email copiado para a área de transferência!")
    
        ttk.Button(botoes_frame, text="📋 Copiar Corpo do Email", 
                command=copiar_corpo).pack(side="left", padx=5)
    
    # Botão para selecionar tudo no corpo
        def selecionar_tudo():
            text_area.tag_add("sel", "1.0", "end")
            text_area.focus()
    
        ttk.Button(botoes_frame, text="🔍 Selecionar Tudo no Corpo", 
                command=selecionar_tudo).pack(side="left", padx=5)
    
        # Botão para fechar
        ttk.Button(botoes_frame, text="❌ Fechar", command=janela_email.destroy).pack(side="right", padx=5)
    
    # Instrução
        ttk.Label(frame, text="💡 Dica: Use os botões azuis para copiar cada campo automaticamente!", 
                font=("Segoe UI", 9), foreground="#94a3b8").pack(pady=5)

BG = "#0f172a"        
CARD = "#1e293b"      
PRIMARY = "#3b82f6"   
TEXT = "#f1f5f9"      

class CoPilotoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Co-Piloto - Gestão de Caronas")
        self.root.geometry("560x850") 
        self.root.resizable(False, False)
        
        style = ttk.Style()
        style.theme_use('clam')
        
        self.root.configure(bg=BG)
        style.configure("TFrame", background=BG)
        style.configure("Card.TFrame", background=CARD, relief="flat")
        style.configure("Title.TLabel", font=("Segoe UI", 20, "bold"), foreground=TEXT, background=BG)
        style.configure("Text.TLabel", font=("Segoe UI", 10), foreground=TEXT, background=CARD)
        style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"), padding=10)
        style.map("Primary.TButton", background=[("!active", PRIMARY), ("active", "#2563eb")], foreground=[("!active", "white")])
        style.configure("TEntry", padding=8, relief="flat")

        self.engine = CaronaEngine()
        self.usuario_logado = None 
        
        self.container = ttk.Frame(self.root)
        self.container.pack(fill="both", expand=True)

        self.mostrar_login()

    def limpar_tela(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    def mostrar_login(self):
        self.limpar_tela()
        card = ttk.Frame(self.container, style="Card.TFrame", padding=40)
        card.place(relx=0.5, rely=0.5, anchor="center")

        ttk.Label(card, text="🚗 Co-Piloto", style="Title.TLabel").pack(pady=(0,20))
        ttk.Label(card, text="E-mail", style="Text.TLabel").pack(anchor="w")
        self.ent_email = ttk.Entry(card, width=30); self.ent_email.pack(pady=5)
        ttk.Label(card, text="Senha", style="Text.TLabel").pack(anchor="w")
        self.ent_senha = ttk.Entry(card, width=30, show="*"); self.ent_senha.pack(pady=5)

        ttk.Button(card, text="Entrar", style="Primary.TButton", command=self.logar).pack(pady=20)
        ttk.Button(card, text="Criar Conta", command=self.mostrar_cadastro).pack()

    def logar(self):
        user = verificar_login(self.ent_email.get(), self.ent_senha.get())
        if user:
            self.usuario_logado = user
            self.mostrar_principal()
        else:
            messagebox.showerror("Erro", "Login inválido!")

    def mostrar_cadastro(self):
        self.limpar_tela()
        frame = ttk.Frame(self.container, style="Card.TFrame", padding=25)
        frame.pack(expand=True)

        ttk.Label(frame, text="Novo Motorista", font=("Segoe UI", 16, "bold"), background=CARD, foreground=TEXT).pack(pady=10)
        
        self.entries = {}
        campos = ["Nome", "Email", "Senha", "Cidade Base (Ex: Campinas)", "Km/L (Cidade)", "Km/L (Estrada)"]
        
        for campo in campos:
            ttk.Label(frame, text=f"{campo}:", style="Text.TLabel").pack(anchor="w")
            ent = ttk.Entry(frame, width=35)
            if campo == "Senha": ent.config(show="*")
            ent.pack(pady=2)
            self.entries[campo] = ent
            
        ttk.Button(frame, text="Cadastrar", command=self.cadastrar).pack(pady=15)
        ttk.Button(frame, text="Voltar", command=self.mostrar_login).pack()

    def cadastrar(self):
        try:
            cons_c = float(self.entries["Km/L (Cidade)"].get().replace(",", "."))
            cons_e = float(self.entries["Km/L (Estrada)"].get().replace(",", "."))
            
            if cadastrar_usuario(self.entries["Nome"].get(), self.entries["Email"].get(), self.entries["Senha"].get(),
                                 self.entries["Cidade Base (Ex: Campinas)"].get(), cons_c, cons_e):
                messagebox.showinfo("Sucesso", "Conta criada!")
                self.mostrar_login()
            else:
                messagebox.showerror("Erro", "Email já existe.")
        except:
            messagebox.showerror("Erro", "Consumo deve ser número.")

    def mostrar_principal(self):
        self.limpar_tela()
        card = ttk.Frame(self.container, style="Card.TFrame", padding=30)
        card.place(relx=0.5, rely=0.5, anchor="center")

        nome = self.usuario_logado[1]
        cidade = self.usuario_logado[2]
        consumo_padrao = self.usuario_logado[3]

        ttk.Label(card, text="🚗 Co-Piloto", style="Title.TLabel").grid(row=0, column=0, columnspan=2, pady=(0,5))
        ttk.Label(card, text=f"Bem-vindo, {nome} • Base: {cidade}", style="Text.TLabel").grid(row=1, column=0, columnspan=2, pady=(0,20))

        ttk.Label(card, text="Origem (Ex: Rua X, 123, Campinas):", style="Text.TLabel").grid(row=2, column=0, sticky="w", pady=2)
        self.ent_origem = ttk.Entry(card, width=35); self.ent_origem.grid(row=2, column=1, pady=2)

        ttk.Label(card, text="Destino Final (Ex: Av. Y, 50, Campinas):", style="Text.TLabel").grid(row=3, column=0, sticky="w", pady=2)
        self.ent_destino = ttk.Entry(card, width=35); self.ent_destino.grid(row=3, column=1, pady=2)

        ttk.Label(card, text="Consumo (km/L):", style="Text.TLabel").grid(row=4, column=0, sticky="w", pady=2)
        self.ent_consumo = ttk.Entry(card, width=35)
        self.ent_consumo.insert(0, str(consumo_padrao))
        self.ent_consumo.grid(row=4, column=1, pady=2)

        ttk.Label(card, text="Preço Gasolina (R$):", style="Text.TLabel").grid(row=5, column=0, sticky="w", pady=2)
        self.ent_gasolina = ttk.Entry(card, width=35)
        self.ent_gasolina.grid(row=5, column=1, pady=2)

        ttk.Label(card, text="Regra de Rateio:", style="Text.TLabel").grid(row=6, column=0, sticky="w", pady=2)
        self.combo_rateio = ttk.Combobox(card, values=["Divisão Justa (Desvio)", "Dividir Igual", "Cobrar Integral"], state="readonly", width=32)
        self.combo_rateio.current(0)
        self.combo_rateio.grid(row=6, column=1, pady=2)

        self.frame_paradas = ttk.Frame(card, style="Card.TFrame")
        self.frame_paradas.grid(row=7, column=0, columnspan=2, pady=10)
        self.lista_paradas_widgets = []
        ttk.Button(self.frame_paradas, text="➕ Adicionar Parada", command=self.adicionar_campo_parada).pack(pady=5)
        self.adicionar_campo_parada()

        self.txt_res = tk.Text(card, height=10, width=50, bg="#020617", fg="#e2e8f0", insertbackground="white", relief="flat", font=("Consolas", 10), padx=10, pady=10)
        self.txt_res.grid(row=10, column=0, columnspan=2, pady=15)

        ttk.Button(card, text=" Calcular Preço Justo", style="Primary.TButton", command=self.acionar_calculo).grid(row=8, column=0, columnspan=2, pady=10)
        ttk.Button(card, text=" Abrir Mapa", command=self.engine.abrir_mapa).grid(row=9, column=0, columnspan=2, pady=5)
        
        ttk.Button(card, text="Abrir Gestão", command=lambda: TelaGestao(self.root)).grid(row=11, column=0, pady=5)
        ttk.Button(card, text="Sair", command=self.mostrar_login).grid(row=11, column=1, pady=5)

    def adicionar_campo_parada(self):
        linha = ttk.Frame(self.frame_paradas, style="Card.TFrame")
        linha.pack(pady=2)
        
        ent_nome = ttk.Entry(linha, width=12)
        ent_nome.insert(0, "Nome")
        ent_nome.pack(side="left", padx=2)
        
        ent_end = ttk.Entry(linha, width=18)
        ent_end.insert(0, "Endereço")
        ent_end.pack(side="left", padx=2)
        
        combo_acao = ttk.Combobox(linha, values=["Embarca", "Desembarca"], state="readonly", width=12)
        combo_acao.current(0)
        combo_acao.pack(side="left", padx=2)
        
        self.lista_paradas_widgets.append({"nome": ent_nome, "endereco": ent_end, "acao": combo_acao})

    def acionar_calculo(self):
        self.txt_res.delete(1.0, tk.END)
        self.txt_res.insert(tk.END, " ⏳ Calculando com IA ...")
        self.root.update()

        try:
            consumo_atual = float(self.ent_consumo.get().replace(",", "."))
            preco_gasolina = float(self.ent_gasolina.get().replace(",", "."))
        except ValueError:
            self.txt_res.delete(1.0, tk.END)
            self.txt_res.insert(tk.END, "Erro: Preencha Consumo e Preço Gasolina com números válidos!")
            return

        custo_km = preco_gasolina / consumo_atual
        tipo_rateio = self.combo_rateio.get()

        paradas_formatadas = []
        for p in self.lista_paradas_widgets:
            n = p["nome"].get()
            e = p["endereco"].get()
            a = p["acao"].get()
            if n and n != "Nome" and e and e != "Endereço": 
                paradas_formatadas.append({"nome": n, "endereco": e, "acao": a})

        origem = self.ent_origem.get()
        destino = self.ent_destino.get()
        cidade = self.usuario_logado[2]
        id_usuario = self.usuario_logado[0]

        thread = threading.Thread(target=self._processar_calculo_thread, args=(origem, destino, paradas_formatadas, cidade, custo_km, tipo_rateio, id_usuario))
        thread.start()

    def _processar_calculo_thread(self, origem, destino, paradas_formatadas, cidade, custo_km, tipo_rateio, id_usuario):
        try:
            res = self.engine.calcular(origem, destino, paradas_formatadas, cidade, custo_km, tipo_rateio)
            self.root.after(0, self._mostrar_resultado, res, paradas_formatadas, id_usuario)
        except Exception as e:
            self.root.after(0, self._mostrar_erro, str(e))

    def _mostrar_resultado(self, res, paradas_formatadas, id_usuario):
        self.txt_res.delete(1.0, tk.END)
        self.txt_res.insert(tk.END, res['texto'])
        
        if messagebox.askyesno("Salvar", "Deseja registrar essa viagem no histórico?"):
            save_viagem(paradas_formatadas, res['valor_total'], id_usuario) 
            messagebox.showinfo("Sucesso", "Registrado no Histórico!")

    def _mostrar_erro(self, erro_msg):
        self.txt_res.delete(1.0, tk.END)
        self.txt_res.insert(tk.END, f"Erro: {erro_msg}")

if __name__ == "__main__":
    init_db()
    root = tk.Tk()
    app = CoPilotoApp(root)
    root.mainloop()