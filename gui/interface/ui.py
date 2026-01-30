import customtkinter as ctk
import tkinter as tk
from PIL import Image
from tkinter import filedialog
from typing import Tuple
import sys
import os
import re
import time
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

# Garante que o Matplotlib use o backend correto para Tkinter
matplotlib.use("TkAgg")

# Tenta importar o backend
try:
    import backend.rko_gui_start as rko_gui_start
except ImportError:
    print("ERRO: 'rko_gui_start.py' não encontrado.")
    rko_gui_start = None

def resource_path(relative_path):
    """Obtem o caminho absoluto para recursos (imagens/assets)"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

CORES = {
    "fundo_principal": "#1A1A1D",
    "fundo_cartao": "#151516",
    "borda": "#2D2D35",
    "destaque": "#5CAEC4",
    "primaria": "#6852A0",
    "texto": "#FFFFFF",
    "texto_escuro": "#413D3D"
}

FONTES = {
    "titulo": ("Roboto", 20, "bold"),
    "subtitulo": ("Roboto", 17, "bold"),
    "corpo_negrito": ("Roboto", 12, "bold"),
    "pequena": ("Roboto", 11)
}

LARGURA_JANELA = 1375
ALTURA_JANELA = 975
LARGURA_CARTAO_AGENTE = 360
ALTURA_CARTAO_AGENTE = 300

ESCRITOR_TERMINAL_GLOBAL = None
START_BUTTON_GLOBAL = None

# Grafico de Linha 
FIG_GLOBAL = None
AX_GLOBAL = None
CANVAS_GLOBAL = None
LINHA_GLOBAL = None
DADOS_X = []
DADOS_Y = []
NOME_INSTANCIA_ATUAL = "Aguardando..."

# Gantt (dinamico)
FIG_GANTT = None
AX_GANTT = None
CANVAS_GANTT = None
MELHOR_MAKESPAN_ATUAL = float('inf')
TEMPO_INICIO_BATERIA = 0

# GLOBAIS DO HISTORICO 
HISTORICO_DATA = {}  # {'NomeInstancia': {'x':[], 'y':[], 'gantt': data}}
FILA_BOTOES_PENDENTES = [] # Fila para o Watchdog
FRAME_LISTA_HISTORICO = None

# Graficos da Aba historico
FIG_HIST_LINHA, AX_HIST_LINHA, CANVAS_HIST_LINHA = None, None, None
FIG_HIST_GANTT, AX_HIST_GANTT, CANVAS_HIST_GANTT = None, None, None

# Cria os botoes do historico 
# Daemon (watchdog) responsavel por verificar constantemente
def iniciar_watchdog_historico():
    global FILA_BOTOES_PENDENTES, FRAME_LISTA_HISTORICO, HISTORICO_DATA
    
    if FILA_BOTOES_PENDENTES and FRAME_LISTA_HISTORICO:
        # Pega o proximo da fila
        nome_instancia = FILA_BOTOES_PENDENTES.pop(0)
        
        if nome_instancia in HISTORICO_DATA:
            try:
                dados = HISTORICO_DATA[nome_instancia]
                melhor_mksp = min(dados['y']) if dados['y'] else "?"
                texto_atualizado = f"{nome_instancia}\n(Make: {melhor_mksp})"
                
                # Procura se o botão já existe
                botao_existente = None
                for widget in FRAME_LISTA_HISTORICO.winfo_children():
                    if isinstance(widget, ctk.CTkButton):
                        # Pega a primeira linha do texto do botão (o nome da instância)
                        nome_botao = widget.cget("text").split('\n')[0]
                        if nome_botao == nome_instancia:
                            botao_existente = widget
                            break
                
                if botao_existente:
                    # ATUALIZA O TEXTO 
                    botao_existente.configure(text=texto_atualizado)
                else:
                    # CRIA NOVO
                    btn = ctk.CTkButton(
                        FRAME_LISTA_HISTORICO, 
                        text=texto_atualizado,
                        fg_color="#333333",
                        hover_color=CORES["destaque"],
                        height=50,
                        command=lambda n=nome_instancia: carregar_instancia_historico(n)
                    )
                    btn.grid(sticky="ew", pady=5, padx=5)
            except Exception as e:
                print(f"Erro Watchdog: {e}")

    # Reagendar verificacao
    if FRAME_LISTA_HISTORICO:
        FRAME_LISTA_HISTORICO.after(500, iniciar_watchdog_historico)

def configurar_aba_grafico(aba):
    global FIG_GLOBAL, AX_GLOBAL, CANVAS_GLOBAL, LINHA_GLOBAL
    frame = ctk.CTkFrame(aba, fg_color="transparent")
    frame.pack(fill="both", expand=True, padx=10, pady=10)

    plt.style.use('dark_background') 
    FIG_GLOBAL, AX_GLOBAL = plt.subplots(figsize=(5, 4), dpi=100)
    FIG_GLOBAL.patch.set_facecolor('#242424') 
    AX_GLOBAL.set_facecolor('#2b2b2b')
    AX_GLOBAL.set_title("Evolução do Makespan (Tempo Real)", fontsize=10, color="white")
    AX_GLOBAL.set_xlabel("Tempo (s)", fontsize=9, color="white")
    AX_GLOBAL.set_ylabel("Makespan (Custo)", fontsize=9, color="white")
    AX_GLOBAL.grid(True, linestyle='--', alpha=0.3)
    
    LINHA_GLOBAL, = AX_GLOBAL.plot([], [], color='#00FF00', linewidth=2, marker='o', markersize=4)
    
    CANVAS_GLOBAL = FigureCanvasTkAgg(FIG_GLOBAL, master=frame)
    CANVAS_GLOBAL.draw()
    CANVAS_GLOBAL.get_tk_widget().pack(fill="both", expand=True)
    NavigationToolbar2Tk(CANVAS_GLOBAL, frame).pack(side="bottom", fill="x")
    return frame

def configurar_aba_gantt_live(aba):
    global FIG_GANTT, AX_GANTT, CANVAS_GANTT
    frame = ctk.CTkFrame(aba, fg_color="transparent")
    frame.pack(fill="both", expand=True, padx=10, pady=10)

    plt.style.use('dark_background') 
    FIG_GANTT, AX_GANTT = plt.subplots(figsize=(5, 4), dpi=100)
    FIG_GANTT.patch.set_facecolor('#242424') 
    AX_GANTT.set_facecolor('#212121')
    AX_GANTT.set_title("Gantt Dinâmico", fontsize=10, color="white")
    AX_GANTT.set_xlabel("Horizonte", fontsize=9, color="white")
    AX_GANTT.set_ylabel("Máquinas", fontsize=9, color="white")
    AX_GANTT.grid(True, linestyle='--', alpha=0.1, color='white')

    CANVAS_GANTT = FigureCanvasTkAgg(FIG_GANTT, master=frame)
    CANVAS_GANTT.draw()
    CANVAS_GANTT.get_tk_widget().pack(fill="both", expand=True)
    NavigationToolbar2Tk(CANVAS_GANTT, frame).pack(side="bottom", fill="x")
    return frame

def configurar_aba_historico(aba):
    global FRAME_LISTA_HISTORICO, FIG_HIST_LINHA, AX_HIST_LINHA, CANVAS_HIST_LINHA, FIG_HIST_GANTT, AX_HIST_GANTT, CANVAS_HIST_GANTT

    aba.grid_columnconfigure(0, weight=1) 
    aba.grid_columnconfigure(1, weight=6) 
    aba.grid_rowconfigure(0, weight=1)

    # Esquerda 
    frame_esq = ctk.CTkFrame(aba, fg_color="transparent")
    frame_esq.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
    frame_esq.grid_rowconfigure(1, weight=1); frame_esq.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(frame_esq, text="FINISHED JOBS", font=("Roboto", 16, "bold"), text_color=CORES["destaque"]).grid(row=0, column=0, pady=(0, 15), padx=(35,0), sticky="ew")
    
    FRAME_LISTA_HISTORICO = ctk.CTkScrollableFrame(frame_esq, width=280, fg_color=CORES["fundo_cartao"], corner_radius=10)
    FRAME_LISTA_HISTORICO.grid(row=1, column=0, sticky="nsew", padx=(30,0))
    FRAME_LISTA_HISTORICO.grid_columnconfigure(0, weight=1)

    # Direita 
    frame_dir = ctk.CTkFrame(aba, fg_color="transparent")
    frame_dir.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
    frame_dir.grid_rowconfigure(0, weight=1); frame_dir.grid_rowconfigure(1, weight=1); frame_dir.grid_columnconfigure(0, weight=1)

    frame_top = ctk.CTkFrame(frame_dir, fg_color="#242424", corner_radius=10, border_width=2, border_color="#333333")
    frame_top.grid(row=0, column=0, sticky="nsew", pady=(40,10), padx=(40,0))
    frame_top.grid_rowconfigure(0, weight=1); frame_top.grid_columnconfigure(0, weight=1)
    
    FIG_HIST_LINHA, AX_HIST_LINHA = plt.subplots(figsize=(12, 7), dpi=100)
    FIG_HIST_LINHA.patch.set_facecolor('#242424'); AX_HIST_LINHA.set_facecolor('#2b2b2b')
    AX_HIST_LINHA.set_title("Convergência", color="white", fontsize=11)
    AX_HIST_LINHA.tick_params(colors='white', labelsize=9)
    for s in AX_HIST_LINHA.spines.values(): s.set_color('white')
    CANVAS_HIST_LINHA = FigureCanvasTkAgg(FIG_HIST_LINHA, master=frame_top)
    CANVAS_HIST_LINHA.draw()
    CANVAS_HIST_LINHA.get_tk_widget().grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

    # Grafico 2
    frame_bot = ctk.CTkFrame(frame_dir, fg_color="#242424", corner_radius=10, border_width=2, border_color="#333333")
    frame_bot.grid(row=1, column=0, sticky="nsew", pady=(60,0), padx=(60,0))
    frame_bot.grid_rowconfigure(0, weight=1); frame_bot.grid_columnconfigure(0, weight=1)
    
    FIG_HIST_GANTT, AX_HIST_GANTT = plt.subplots(figsize=(12, 7), dpi=100)
    FIG_HIST_GANTT.patch.set_facecolor('#242424'); AX_HIST_GANTT.set_facecolor('#212121')
    AX_HIST_GANTT.set_title("Cronograma Final", color="white", fontsize=11)
    AX_HIST_GANTT.tick_params(colors='white', labelsize=9)
    for s in AX_HIST_GANTT.spines.values(): s.set_color('white')
    CANVAS_HIST_GANTT = FigureCanvasTkAgg(FIG_HIST_GANTT, master=frame_bot)
    CANVAS_HIST_GANTT.draw()
    CANVAS_HIST_GANTT.get_tk_widget().grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

    # invoca o 'daemon' local
    iniciar_watchdog_historico()

def carregar_instancia_historico(nome_instancia):
    dados = HISTORICO_DATA.get(nome_instancia)
    if not dados: return

    # Plota Linha
    AX_HIST_LINHA.clear()
    AX_HIST_LINHA.plot(dados['x'], dados['y'], color='#00FF00', linewidth=2, marker='o', markersize=4)
    AX_HIST_LINHA.set_title(f"Convergência: {nome_instancia} (Melhor: {min(dados['y']) if dados['y'] else 0})", color="white", fontsize=10)
    AX_HIST_LINHA.set_facecolor('#2b2b2b'); AX_HIST_LINHA.grid(True, linestyle='--', alpha=0.3)
    AX_HIST_LINHA.tick_params(colors='white')
    CANVAS_HIST_LINHA.draw()

    # Plota Gantt
    AX_HIST_GANTT.clear()
    gantt = dados['gantt']
    if gantt:
        M, p, X, C = gantt["M"], gantt["p"], gantt["X"], gantt["C"]
        import matplotlib.cm as cm
        max_id = max([k[1] for k in C.keys()]) if C else 10
        colors = cm.get_cmap("tab20", max_id + 1)
        max_makespan = 0
        for i in M:
            jobs = [j for (m, k, j), v in X.items() if m == i and v > 0.5]
            for j in jobs:
                comp = C.get((i, j), 0); proc = p.get((i, j), 0); start = comp - proc
                if comp > max_makespan: max_makespan = comp
                AX_HIST_GANTT.barh(y=f'M{i}', width=proc, left=start, height=0.6, color=colors(j), edgecolor='black')
                if proc > 0: AX_HIST_GANTT.text(start + proc/2, f'M{i}', f'{j}', ha='center', va='center', color='white', fontsize=6, fontweight='bold')
    
    AX_HIST_GANTT.set_facecolor('#212121'); AX_HIST_GANTT.invert_yaxis()
    AX_HIST_GANTT.set_title(f"Cronograma | Makespan: {max_makespan}", color="white", fontsize=10)
    AX_HIST_GANTT.tick_params(colors='white')
    for s in AX_HIST_GANTT.spines.values(): s.set_color('white')
    CANVAS_HIST_GANTT.draw()

def atualizar_desenho_gantt(dados_gantt, nome_instancia, tempo_decorrido):
    if not AX_GANTT or not dados_gantt: return
    AX_GANTT.clear()
    M, p, X, C = dados_gantt["M"], dados_gantt["p"], dados_gantt["X"], dados_gantt["C"]
    import matplotlib.cm as cm
    max_id = max([k[1] for k in C.keys()]) if C else 10
    colors = cm.get_cmap("tab20", max_id + 1)
    max_completion_time = 0
    for i in M:
        jobs = [j for (m, k, j), v in X.items() if m == i and v > 0.5]
        for j in jobs:
            comp = C.get((i, j), 0); proc = p.get((i, j), 0); start = comp - proc
            if comp > max_completion_time: max_completion_time = comp
            AX_GANTT.barh(y=f'M{i}', width=proc, left=start, height=0.6, color=colors(j), edgecolor='black', alpha=0.9)
            if proc > 0: AX_GANTT.text(start + proc/2, f'M{i}', f'{j}', ha='center', va='center', color='white', fontsize=7, fontweight='bold')
    AX_GANTT.set_facecolor('#212121'); AX_GANTT.invert_yaxis()
    AX_GANTT.set_title(f"Instância: {nome_instancia}  |  Makespan: {max_completion_time}  |  Tempo: {tempo_decorrido:.2f}s", color="white", fontsize=11, fontweight="bold")
    AX_GANTT.set_xlabel("Horizonte", fontsize=9, color="white")
    AX_GANTT.set_ylabel("Máquinas", fontsize=9, color="white")
    AX_GANTT.tick_params(axis='x', colors='white', labelsize=8); AX_GANTT.tick_params(axis='y', colors='white', labelsize=8)
    for s in AX_GANTT.spines.values(): s.set_color('white')
    AX_GANTT.grid(axis='x', linestyle='--', alpha=0.2, color='white')
    CANVAS_GANTT.draw()

class RedirecionadorTextoThreadSeguro(object):
    def __init__(self, widget_texto): self.widget_texto = widget_texto
    def write(self, texto): 
        try: self.widget_texto.after(0, lambda: self.escrita_segura(texto))
        except: pass 
    def escrita_segura(self, texto):
        try: self.widget_texto.configure(state="normal"); self.widget_texto.insert("end", texto); self.widget_texto.see("end"); self.widget_texto.configure(state="disabled")
        except: pass
    def flush(self): pass

def manipulador_retorno_interface(dados):
    global ESCRITOR_TERMINAL_GLOBAL, START_BUTTON_GLOBAL, DADOS_X, DADOS_Y, NOME_INSTANCIA_ATUAL
    global CANVAS_GANTT, MELHOR_MAKESPAN_ATUAL, TEMPO_INICIO_BATERIA, HISTORICO_DATA, FILA_BOTOES_PENDENTES
    global CANVAS_GLOBAL, AX_GLOBAL, LINHA_GLOBAL, AX_GANTT

    if ESCRITOR_TERMINAL_GLOBAL is None: return

    tipo_status = dados.get("status")
    texto_log = dados.get("message", "")
    nome_pacote = dados.get("instancia") 

    # INICIO DE JOB 
    if tipo_status == "running":
        if nome_pacote: NOME_INSTANCIA_ATUAL = nome_pacote
        MELHOR_MAKESPAN_ATUAL = float('inf'); TEMPO_INICIO_BATERIA = time.time(); DADOS_X.clear(); DADOS_Y.clear()
        ESCRITOR_TERMINAL_GLOBAL.write(f"{texto_log}\n")
        
        # Limpa Visual
        if CANVAS_GLOBAL:
            LINHA_GLOBAL.set_data([], [])
            AX_GLOBAL.set_title(f"{NOME_INSTANCIA_ATUAL}...", fontsize=10, color="white")
            AX_GLOBAL.relim(); AX_GLOBAL.autoscale_view(); CANVAS_GLOBAL.draw()
        if AX_GANTT: AX_GANTT.clear(); CANVAS_GANTT.draw()

    # UPDATE VISUAL 
    elif tipo_status == "update":
        makespan = dados.get("makespan"); gantt_data = dados.get("gantt_data")
        
        if nome_pacote == NOME_INSTANCIA_ATUAL:
            
            # So atualiza se for melhor ou igual
            if makespan <= MELHOR_MAKESPAN_ATUAL:
                tempo_atual = time.time() - TEMPO_INICIO_BATERIA
                
                # Atualiza dados da linha
                if makespan < MELHOR_MAKESPAN_ATUAL:
                    MELHOR_MAKESPAN_ATUAL = makespan
                    DADOS_X.append(tempo_atual)
                    DADOS_Y.append(makespan)

                    if CANVAS_GLOBAL: 
                        LINHA_GLOBAL.set_data(DADOS_X, DADOS_Y)
                        AX_GLOBAL.set_title(f"{NOME_INSTANCIA_ATUAL}  |  Melhor: {MELHOR_MAKESPAN_ATUAL}", fontsize=10, color="#00FF00", fontweight="bold")
                        AX_GLOBAL.relim(); AX_GLOBAL.autoscale_view(); CANVAS_GLOBAL.draw()

                # Atualiza Gantt Visual
                if gantt_data and CANVAS_GANTT: 
                    CANVAS_GANTT.get_tk_widget().after(0, lambda: atualizar_desenho_gantt(gantt_data, nome_pacote, tempo_atual))

    # 3. PACOTE BLINDADO DE HISTORICO
    elif tipo_status == "instancia_concluida":
        nome_final = dados.get("instancia")
        hist_curve = dados.get("history_curve", []) 
        gantt_final = dados.get("gantt_data")

        if nome_final:
            lista_x = [p[0] for p in hist_curve]
            lista_y = [p[1] for p in hist_curve]
            
            HISTORICO_DATA[nome_final] = {
                'x': lista_x, 'y': lista_y, 'gantt': gantt_final
            }
            # Sempre joga na fila, o Watchdog decide se cria ou atualiza
            if nome_final not in FILA_BOTOES_PENDENTES:
                FILA_BOTOES_PENDENTES.append(nome_final)

    # 4. LOGS E ERROS
    elif tipo_status == "finished": 
        ESCRITOR_TERMINAL_GLOBAL.write(f"\n{'='*40}\n{texto_log}\n{'='*40}\n")
        if "ABORTADO" in texto_log:
             try: START_BUTTON_GLOBAL.resetar_estado()
             except: pass

    elif tipo_status == "log": ESCRITOR_TERMINAL_GLOBAL.write(f"{texto_log}\n")
    
    elif tipo_status == "error": 
        ESCRITOR_TERMINAL_GLOBAL.write(f"ERRO: {texto_log}\n")
        try: START_BUTTON_GLOBAL.resetar_estado()
        except: pass
        
    elif tipo_status == "completed_all":
        ESCRITOR_TERMINAL_GLOBAL.write(f"\n>>> {texto_log} <<<\n")
        try: START_BUTTON_GLOBAL.resetar_estado()
        except: pass

    if tipo_status == "finished" and "Execução finalizada" in texto_log:
         try: START_BUTTON_GLOBAL.resetar_estado()
         except: pass

#  CONFIGURAÇOES DAS ABAS DE PARAMETROS E EXECUCAO

def configurar_aba_parametros(aba):
    aba.widgets_armazenados = {} 
    
    rotulo_titulo = ctk.CTkLabel(aba, text="HYPER-PARAMETERS", text_color=CORES["destaque"], font=FONTES["titulo"])
    rotulo_titulo.grid(row=0, column=1, sticky="e", columnspan=3)
    
    rotulo_decoder = ctk.CTkLabel(aba, text="SELECT DECODER", font=FONTES["subtitulo"], text_color=CORES["texto"])
    rotulo_decoder.grid(row=1, column=1, padx=10, sticky="s")
    
    combo_decoder = ctk.CTkComboBox(
        aba, values=["ECT", "KSTS", "M3LAW", "INCREMENTAL", "CHEAPEST"], 
        border_color=CORES["primaria"], border_width=2, corner_radius=0, 
        dropdown_fg_color="lavender", dropdown_text_color=CORES["texto_escuro"], dropdown_hover_color=CORES["destaque"]
    )
    combo_decoder.grid(row=2, column=1, padx=10, sticky="n", pady=5)
    aba.widgets_armazenados["decoder"] = combo_decoder 
    
    rotulo_tempo = ctk.CTkLabel(aba, text="TIME LIMIT (S)", font=FONTES["subtitulo"], text_color=CORES["texto"])
    rotulo_tempo.grid(row=1, column=2, sticky="s") 
    
    entrada_tempo = ctk.CTkEntry(aba, width=90, corner_radius=0, border_color=CORES["primaria"], border_width=2)
    entrada_tempo.insert(0,"60")
    entrada_tempo.grid(row=2, column=2, padx=15, sticky="n", pady=5)
    aba.widgets_armazenados["time_limit"] = entrada_tempo 

    rotulo_execucoes = ctk.CTkLabel(aba, text="EXECUTION TIMES", font=FONTES["subtitulo"], text_color=CORES["texto"])
    rotulo_execucoes.grid(row=1, column=3, sticky="s")
    
    entrada_execucoes = ctk.CTkEntry(aba, width=90, corner_radius=0, border_color=CORES["primaria"], border_width=2)
    entrada_execucoes.insert(0, "1")
    entrada_execucoes.grid(row=2, column=3, padx=15, sticky="n", pady=5)
    aba.widgets_armazenados["execution_times"] = entrada_execucoes
    
def configurar_aba_agentes(aba):
    area_rolagem = ctk.CTkScrollableFrame(aba, width=1160, height=860, fg_color="transparent")
    area_rolagem.grid(row=0, column=0, columnspan=10, rowspan=10, padx=10, pady=10, sticky="nsew")
    for i in range(3): area_rolagem.grid_columnconfigure(i, weight=1, minsize=360)
    aba.parametros_agentes = {} 
    
    ctk.CTkLabel(area_rolagem, text="AGENTS PARAMETERS", font=FONTES["titulo"], text_color=CORES["destaque"]).grid(row=0, column=0, columnspan=3, sticky="ew", padx=12, pady=(8,12))
    
    configuracao_agentes = {
        "BRKGA": {"linha": 1, "coluna": 0, "titulo": "BIASED RANDOM KEY GENETIC ALGORITHM (BRKGA)", "campos": [("Population", "100"), ("Elite set %", "0.20"), ("Mutant set %", "0.10"), ("Inheritance Prob", "0.70")]},
        "SA": {"linha": 1, "coluna": 1, "titulo": "SIMULATED ANNEALING (SA)", "campos": [("Iterations", "50"), ("alphaSA", "0.99"), ("betaMin", "0.05"), ("betaMax", "0.25"), ("Initial Temperature", "10000")]},
        "ILS": {"linha": 1, "coluna": 2, "titulo": "ITERATED LOCAL SEARCH (ILS)", "campos": [("betaMin", "0.1"), ("betaMax", "0.20")]},
        "VNS": {"linha": 2, "coluna": 0, "titulo": "VARIABLE NEIGHBORHOOD SEARCH (VNS)", "campos": [("kMax", "5"), ("betaMin", "0.05")]},
        "PSO": {"linha": 2, "coluna": 1, "titulo": "PARTICLE SWARM OPTIMIZATION (PSO)", "campos": [("PSize", "100"), ("c1", "2.05"), ("c2", "2.05"), ("w", "0.73")]},
        "GA": {"linha": 3, "coluna": 0, "titulo": "GENETIC ALGORITHM (GA)", "campos": [("Population", "100"), ("CrosProb", "0.98"), ("MutProb", "0.005")]},
        "LNS": {"linha": 3, "coluna": 1, "titulo": "LARGE NEIGHBORHOOD SEARCH (LNS)", "campos": [("betaMin", "0.10"), ("betaMax", "0.30"), ("T0", "1000"), ("alphaLNS", "0.95")]},
    }
    for nome, config in configuracao_agentes.items():
        aba.parametros_agentes[nome] = criar_cartao_agente(area_rolagem, config)

def criar_cartao_agente(conteiner_pai, config):
    frame = ctk.CTkFrame(conteiner_pai, fg_color=CORES["fundo_cartao"], width=LARGURA_CARTAO_AGENTE, height=ALTURA_CARTAO_AGENTE, border_width=1, border_color=CORES["borda"])
    frame.grid(row=config["linha"], column=config["coluna"], padx=8, pady=8, sticky="n")
    frame.grid_propagate(False)
    
    ctk.CTkLabel(frame, text=config["titulo"], font=FONTES["corpo_negrito"], text_color=CORES["destaque"]).grid(row=0, column=0, sticky="w", padx=10, pady=(8,4))
    var_chk = tk.BooleanVar(value=True)
    ctk.CTkCheckBox(frame, text="", variable=var_chk).grid(row=0, column=1, sticky="e", padx=10, pady=(8,4))
    
    widgets = {"frame_conteiner": frame, "variavel_controle": var_chk}
    for i, (txt, val) in enumerate(config["campos"], start=1):
        ctk.CTkLabel(frame, text=txt, anchor="w", font=FONTES["pequena"]).grid(row=i, column=0, sticky="w", padx=10, pady=6)
        ent = ctk.CTkEntry(frame, width=90); ent.insert(0, val)
        col = 1 if config.get("coluna", 0) != 0 else 0
        ent.grid(row=i, column=col, sticky="e", padx=10 if config.get("coluna",0) != 0 else 0, pady=6)
        widgets[txt] = ent
    return widgets

def configurar_aba_entrada_saida(aba):
    aba.widgets_armazenados = {} 
    def sel_dir(w):
        p = filedialog.askdirectory()
        if p: w.delete(0, "end"); w.insert(0, p)
            
    ctk.CTkLabel(aba, text="IO CONFIGURATION", text_color=CORES["destaque"], font=FONTES["titulo"]).grid(row=0, column=1, columnspan=10, sticky="w", pady=(8,12), padx=70)
    try: img = ctk.CTkImage(Image.open(resource_path("assets/dots.png")), size=(16, 16))
    except: img = None 
        
    for k, txt, row in [("output_path", "Output Path", 1), ("instance_path", "Instance Folder Path", 2), ("gantt_path", "Gantt Chart Path", 3)]:
        fr = ctk.CTkFrame(aba, fg_color="transparent")
        fr.grid(row=row, column=0, padx=8, pady=8, sticky="n")
        ctk.CTkLabel(fr, text=txt, font=FONTES["subtitulo"]).grid(row=0, column=0, padx=8, sticky="w")
        ent = ctk.CTkEntry(fr, border_color=CORES["primaria"], border_width=2, width=350)
        ent.grid(row=1, column=0, padx=10, pady=3)
        aba.widgets_armazenados[k] = ent 
        ctk.CTkButton(fr, text="" if img else "...", width=30, image=img, fg_color="transparent", hover_color=CORES["destaque"], command=lambda e=ent: sel_dir(e)).grid(row=1, column=1, pady=10)

def configurar_aba_execucao(aba, aba_p, aba_a, aba_io):
    global ESCRITOR_TERMINAL_GLOBAL, START_BUTTON_GLOBAL
    estado_execucao = {"rodando": False}

    def resetar_botao():
        estado_execucao["rodando"] = False
        try: START_BUTTON_GLOBAL.configure(state="normal", text='START SOLVER', fg_color="#77198f", hover_color="#9c27b0", border_width=0, text_color="white")
        except: pass

    def ao_passar(e): 
        if estado_execucao["rodando"]: START_BUTTON_GLOBAL.configure(text="STOP", fg_color="#C0392B", hover_color="#E74C3C", text_color="white")
    def ao_sair(e):
        if estado_execucao["rodando"]: START_BUTTON_GLOBAL.configure(text="Running...", fg_color="transparent", border_width=2, border_color="#555555", text_color=("gray10", "gray90"))

    def acao():
        if rko_gui_start is None: print("ERRO: Middleware ausente."); return
        if not estado_execucao["rodando"]:
            data = coletar_dados_interface(aba_p, aba_a, aba_io)
            if not data: return 
            if ESCRITOR_TERMINAL_GLOBAL:
                ESCRITOR_TERMINAL_GLOBAL.widget_texto.configure(state="normal"); ESCRITOR_TERMINAL_GLOBAL.widget_texto.delete("1.0", "end"); ESCRITOR_TERMINAL_GLOBAL.widget_texto.configure(state="disabled")
            estado_execucao["rodando"] = True
            START_BUTTON_GLOBAL.configure(text="Running...", fg_color="#555555", border_width=2, border_color="#555555", text_color=("gray10", "gray90"))
            rko_gui_start.iniciar_resolucao(data, manipulador_retorno_interface)
        else:
            rko_gui_start.solicitar_parada()

    rotulo = ctk.CTkLabel(aba, text="EXECUTION LOG", text_color=CORES["destaque"], font=FONTES["titulo"])
    rotulo.grid(row=0, column=0, columnspan=10, sticky="ew", padx=7, pady=(8,0))
    
    botao = ctk.CTkButton(aba, text='START SOLVER', width=200, height=50, command=acao, fg_color="#77198f", hover_color="#9c27b0", font=("Roboto", 18, "bold"))
    botao.grid(row=1, column=0, columnspan=10, pady=0, padx=20)
    botao.bind("<Enter>", ao_passar); botao.bind("<Leave>", ao_sair)

    term = ctk.CTkTextbox(aba, border_width=2, fg_color="black", text_color="#00FF00", border_color="#2D2D35", font=("Consolas", 13))
    term.grid(row=2, column=0, columnspan=10, rowspan=8, sticky="nsew", padx=45, pady=(0,45))
    term.configure(state="disabled")

    ESCRITOR_TERMINAL_GLOBAL = RedirecionadorTextoThreadSeguro(term)
    START_BUTTON_GLOBAL = botao
    START_BUTTON_GLOBAL.resetar_estado = resetar_botao
    sys.stdout = ESCRITOR_TERMINAL_GLOBAL

#  FUNCOES BASE

def centralizar_janela(janela, w, h):
    ws = janela.winfo_screenwidth(); hs = janela.winfo_screenheight()
    x = (ws - w) // 2; y = (hs - h) // 2
    janela.geometry(f"{w}x{h}+{x}+{y}")

def criar_aba_base(pai):
    f = ctk.CTkFrame(pai, width=1200, height=900, border_width=5, border_color=CORES["borda"])
    for i in range(10): f.grid_rowconfigure(i, weight=1, minsize=20); f.grid_columnconfigure(i, weight=1, minsize=20)
    return f

def coletar_dados_interface(aba_p, aba_a, aba_io):

    data = {}
    if hasattr(aba_p, 'widgets_armazenados'):
        data["hyper_parameters"] = {k: w.get() for k, w in aba_p.widgets_armazenados.items()}
    data["agents"] = {}
    if hasattr(aba_a, 'parametros_agentes'):
        for n, w in aba_a.parametros_agentes.items():
            if w["variavel_controle"].get():
                data["agents"][n] = {k: v.get() for k, v in w.items() if k not in ("frame_conteiner", "variavel_controle")}
    data["io"] = {k: w.get() for k, w in aba_io.widgets_armazenados.items()} if hasattr(aba_io, 'widgets_armazenados') else {}
    return data

def construir_aplicacao():
    janela = ctk.CTk(); janela.title("RKO-SOLVER"); centralizar_janela(janela, LARGURA_JANELA, ALTURA_JANELA)
    janela.resizable(False, False); ctk.set_appearance_mode('dark')
    for i in range(10): janela.grid_rowconfigure(i, minsize=20); janela.grid_columnconfigure(i, minsize=20)

    frame_main = ctk.CTkFrame(janela, fg_color=CORES["fundo_principal"], width=1200, height=900, border_width=5, border_color=CORES["borda"])
    frame_main.grid(row=2, column=2, columnspan=20, sticky="nsew", padx=10)
    frame_main.grid_rowconfigure(0, weight=1); frame_main.grid_columnconfigure(0, weight=1); frame_main.grid_propagate(False)

    abas = [criar_aba_base(frame_main) for _ in range(7)]
    aba_p, aba_a, aba_io, aba_exe, aba_gra, aba_gan, aba_hist = abas

    def show(a_sel):
        for a in abas: a.grid_forget()
        a_sel.grid(row=0, column=0, sticky="nsew")

    configurar_aba_parametros(aba_p)
    configurar_aba_agentes(aba_a)
    configurar_aba_entrada_saida(aba_io)
    configurar_aba_execucao(aba_exe, aba_p, aba_a, aba_io)
    configurar_aba_grafico(aba_gra)
    configurar_aba_gantt_live(aba_gan)
    configurar_aba_historico(aba_hist) # <--- Agora chama a nova

    show(aba_p)
    janela.protocol("WM_DELETE_WINDOW", lambda: (janela.destroy(), sys.exit(0)))
    
    return janela, show, aba_p, aba_a, aba_io, aba_exe, aba_gra, aba_gan, aba_hist