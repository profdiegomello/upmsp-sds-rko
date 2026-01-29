import customtkinter as ctk
import tkinter as tk
from PIL import Image
from tkinter import filedialog
from typing import Tuple
import sys
import os
import re  # le os numeros do texto
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

# VARIAVEIS GLOBAIS DE CONTROLE 
ESCRITOR_TERMINAL_GLOBAL = None
START_BUTTON_GLOBAL = None

# GLOBAIS DO GRAFICO DE LINHA
FIG_GLOBAL = None
AX_GLOBAL = None
CANVAS_GLOBAL = None
LINHA_GLOBAL = None
DADOS_X = []
DADOS_Y = []
NOME_INSTANCIA_ATUAL = "Aguardando..."

# GLOBAIS DO GANTT DINAMICO
FIG_GANTT = None
AX_GANTT = None
CANVAS_GANTT = None
MELHOR_MAKESPAN_ATUAL = float('inf')
TEMPO_INICIO_BATERIA = 0


def configurar_aba_grafico(aba):
    global FIG_GLOBAL, AX_GLOBAL, CANVAS_GLOBAL, LINHA_GLOBAL

    frame_grafico = ctk.CTkFrame(aba, fg_color="transparent")
    frame_grafico.pack(fill="both", expand=True, padx=10, pady=10)

    plt.style.use('dark_background') 
    FIG_GLOBAL, AX_GLOBAL = plt.subplots(figsize=(5, 4), dpi=100)
    
    FIG_GLOBAL.patch.set_facecolor('#242424') 
    AX_GLOBAL.set_facecolor('#2b2b2b')

    AX_GLOBAL.set_title("Evolução do Makespan (Tempo Real)", fontsize=10, color="white")
    AX_GLOBAL.set_xlabel("Tempo (s)", fontsize=9, color="white")
    AX_GLOBAL.set_ylabel("Makespan (Custo)", fontsize=9, color="white")
    AX_GLOBAL.grid(True, linestyle='--', alpha=0.3)

    LINHA_GLOBAL, = AX_GLOBAL.plot([], [], color='#00FF00', linewidth=2, marker='o', markersize=4)

    CANVAS_GLOBAL = FigureCanvasTkAgg(FIG_GLOBAL, master=frame_grafico)
    CANVAS_GLOBAL.draw()
    CANVAS_GLOBAL.get_tk_widget().pack(fill="both", expand=True)

    toolbar = NavigationToolbar2Tk(CANVAS_GLOBAL, frame_grafico)
    toolbar.update()
    toolbar.pack(side="bottom", fill="x")

    return frame_grafico

def configurar_aba_gantt_live(aba):
    global FIG_GANTT, AX_GANTT, CANVAS_GANTT

    frame_grafico = ctk.CTkFrame(aba, fg_color="transparent")
    frame_grafico.pack(fill="both", expand=True, padx=10, pady=10)

    plt.style.use('dark_background') 
    FIG_GANTT, AX_GANTT = plt.subplots(figsize=(5, 4), dpi=100)
    
    FIG_GANTT.patch.set_facecolor('#242424') 
    AX_GANTT.set_facecolor('#212121')
    
    AX_GANTT.set_title("Gantt Dinâmico", fontsize=10, color="white")
    AX_GANTT.set_xlabel("Horizonte de sequenciamento", fontsize=9, color="white")
    AX_GANTT.set_ylabel("Máquinas", fontsize=9, color="white")
    AX_GANTT.grid(True, linestyle='--', alpha=0.1, color='white')

    CANVAS_GANTT = FigureCanvasTkAgg(FIG_GANTT, master=frame_grafico)
    CANVAS_GANTT.draw()
    CANVAS_GANTT.get_tk_widget().pack(fill="both", expand=True)

    toolbar = NavigationToolbar2Tk(CANVAS_GANTT, frame_grafico)
    toolbar.update()
    toolbar.pack(side="bottom", fill="x")

    return frame_grafico

def atualizar_desenho_gantt(dados_gantt, nome_instancia, tempo_decorrido):
    global FIG_GANTT, AX_GANTT, CANVAS_GANTT
    
    if not AX_GANTT or not dados_gantt:
        return

    AX_GANTT.clear()
    
    M = dados_gantt["M"]
    p = dados_gantt["p"]
    X = dados_gantt["X"]
    C = dados_gantt["C"]
    
    import matplotlib.cm as cm
    max_job_id = max([k[1] for k in C.keys()]) if C else 10
    colors = cm.get_cmap("tab20", max_job_id + 1)
    max_completion_time = 0

    for i in M:
        jobs_na_maquina = []
        for (m, k, j), val in X.items():
            if m == i and val > 0.5:
                jobs_na_maquina.append(j)
        
        for j in jobs_na_maquina:
            completion_time = C.get((i, j), 0)
            processing_time = p.get((i, j), 0)
            start_time = completion_time - processing_time

            if completion_time > max_completion_time:
                max_completion_time = completion_time

            AX_GANTT.barh(y=f'M{i}', width=processing_time, left=start_time, height=0.6, color=colors(j), edgecolor='black', alpha=0.9)
            
            if processing_time > 0: 
                AX_GANTT.text(start_time + processing_time / 2, f'M{i}', f'{j}', ha='center', va='center', color='white', fontsize=7, fontweight='bold')

    AX_GANTT.set_facecolor('#212121')
    AX_GANTT.invert_yaxis()
    
    titulo = f"Instância: {nome_instancia}  |  Makespan: {max_completion_time}  |  Tempo: {tempo_decorrido:.2f}s"
    AX_GANTT.set_title(titulo, color="white", fontsize=11, fontweight="bold")
    AX_GANTT.set_xlabel("Horizonte de Sequenciamento", fontsize=9, color="white")
    AX_GANTT.set_ylabel("Máquinas", fontsize=9, color="white")
    
    AX_GANTT.tick_params(axis='x', colors='white', labelsize=8)
    AX_GANTT.tick_params(axis='y', colors='white', labelsize=8)
    for spine in AX_GANTT.spines.values(): spine.set_color('white')
    AX_GANTT.grid(axis='x', linestyle='--', alpha=0.2, color='white')

    CANVAS_GANTT.draw()

# REDIRECIONADOR DE TEXTO 
class RedirecionadorTextoThreadSeguro(object):
    def __init__(self, widget_texto):
        self.widget_texto = widget_texto

    def write(self, texto):
        try:
            self.widget_texto.after(0, lambda: self.escrita_segura(texto))
        except Exception:
            pass 

    def escrita_segura(self, texto):
        try:
            self.widget_texto.configure(state="normal")
            self.widget_texto.insert("end", texto)
            self.widget_texto.see("end")
            self.widget_texto.configure(state="disabled")
        except Exception:
            pass

    def flush(self):
        pass

# MANIPULADOR DE EVENTOS DA INTERFACE 
def manipulador_retorno_interface(dados):
    global ESCRITOR_TERMINAL_GLOBAL, START_BUTTON_GLOBAL
    global DADOS_X, DADOS_Y, CANVAS_GLOBAL, AX_GLOBAL, LINHA_GLOBAL, NOME_INSTANCIA_ATUAL
    global CANVAS_GANTT, AX_GANTT
    global MELHOR_MAKESPAN_ATUAL, TEMPO_INICIO_BATERIA

    if ESCRITOR_TERMINAL_GLOBAL is None: return

    tipo_status = dados.get("status")
    texto_log = dados.get("message", "")

    # 1. ATUALIZACAO DO GANTT AO VIVO
    if tipo_status == "update":
        makespan = dados.get("makespan")
        gantt_data = dados.get("gantt_data")
        
        if makespan < MELHOR_MAKESPAN_ATUAL:
            MELHOR_MAKESPAN_ATUAL = makespan
            tempo_decorrido = time.time() - TEMPO_INICIO_BATERIA if TEMPO_INICIO_BATERIA > 0 else 0.0

            if gantt_data and CANVAS_GANTT:
                CANVAS_GANTT.get_tk_widget().after(
                    0, 
                    lambda: atualizar_desenho_gantt(gantt_data, NOME_INSTANCIA_ATUAL, tempo_decorrido)
                )

    # 2. LOGICA DO GRAFICO E LOGS
    elif tipo_status == "log" or tipo_status == "running":
        
        if "Processando (" in texto_log:
            MELHOR_MAKESPAN_ATUAL = float('inf')
            TEMPO_INICIO_BATERIA = time.time()
            
            try:
                partes = texto_log.split(': ')
                NOME_INSTANCIA_ATUAL = partes[1].split(' [')[0] if len(partes) > 1 else "Instância"
            except:
                NOME_INSTANCIA_ATUAL = "Instância"

            DADOS_X.clear(); DADOS_Y.clear()
            
            def _limpar_grafico():
                if CANVAS_GLOBAL and AX_GLOBAL and LINHA_GLOBAL:
                    LINHA_GLOBAL.set_data([], [])
                    AX_GLOBAL.set_title(f"{NOME_INSTANCIA_ATUAL} - Iniciando...", fontsize=10, color="white")
                    AX_GLOBAL.relim(); AX_GLOBAL.autoscale_view(); CANVAS_GLOBAL.draw()
                
                if AX_GANTT and CANVAS_GANTT:
                    AX_GANTT.clear()
                    AX_GANTT.set_title("Aguardando Solução...", color="white", fontsize=10)
                    AX_GANTT.set_facecolor('#212121')
                    CANVAS_GANTT.draw()
            
            if CANVAS_GLOBAL: CANVAS_GLOBAL.get_tk_widget().after(0, _limpar_grafico)

        match = re.search(r"BEST: (\d+\.?\d*) .* Time: (\d+\.?\d*)", texto_log)
        if match:
            try:
                makespan = float(match.group(1))
                tempo = float(match.group(2))
                DADOS_X.append(tempo); DADOS_Y.append(makespan)
                
                if makespan < MELHOR_MAKESPAN_ATUAL: MELHOR_MAKESPAN_ATUAL = makespan

                def _atualizar_grafico_linha():
                    if CANVAS_GLOBAL and AX_GLOBAL and LINHA_GLOBAL:
                        LINHA_GLOBAL.set_data(DADOS_X, DADOS_Y)
                        AX_GLOBAL.set_title(f"{NOME_INSTANCIA_ATUAL}  |  Melhor: {MELHOR_MAKESPAN_ATUAL}", fontsize=10, color="#00FF00", fontweight="bold")
                        AX_GLOBAL.relim(); AX_GLOBAL.autoscale_view(); CANVAS_GLOBAL.draw()

                if CANVAS_GLOBAL: CANVAS_GLOBAL.get_tk_widget().after(0, _atualizar_grafico_linha)
            except: pass

    # 3. TERMINAL E BOTOES
    if tipo_status == "finished":
        ESCRITOR_TERMINAL_GLOBAL.write(f"\n{'='*43}\n   {dados.get('message', 'Fim.')}\n{'='*43}\n\n")
    elif tipo_status == "error":
        ESCRITOR_TERMINAL_GLOBAL.write(f"\n!!! ERRO CRÍTICO !!!\n{dados.get('message', '')}\n")
    elif tipo_status in ["running", "log"]:
        ESCRITOR_TERMINAL_GLOBAL.write(f"{texto_log}\n")

    if tipo_status in ["finished", "error"]:
        def _reset_safe():
            try:
                if START_BUTTON_GLOBAL: START_BUTTON_GLOBAL.resetar_estado()
            except: pass
        try: ESCRITOR_TERMINAL_GLOBAL.widget_texto.after(0, _reset_safe)
        except: pass

#LAYOUT GERAIS 

def centralizar_janela(janela, largura, altura):
    largura_tela = janela.winfo_screenwidth()
    altura_tela = janela.winfo_screenheight()
    posicao_x = (largura_tela - largura) // 2
    posicao_y = (altura_tela - altura) // 2
    janela.geometry(f"{largura}x{altura}+{posicao_x}+{posicao_y}")

def criar_aba_base(container_pai) -> ctk.CTkFrame:
    aba = ctk.CTkFrame(container_pai, width=1200, height=900, border_width=5, border_color=CORES["borda"])
    # Configura malha do grid em 10x10
    for i in range(10):
        aba.grid_rowconfigure(i, weight=1, minsize=20)
        aba.grid_columnconfigure(i, weight=1, minsize=20)
    return aba

def coletar_dados_interface(aba_parametros, aba_agentes, aba_entrada_saida) -> dict:
    dados_compilados = {}
    
    if hasattr(aba_parametros, 'widgets_armazenados'):
        dados_compilados["hyper_parameters"] = {
            "decoder": aba_parametros.widgets_armazenados["decoder"].get(),
            "time_limit": aba_parametros.widgets_armazenados["time_limit"].get(),
            "execution_times": aba_parametros.widgets_armazenados["execution_times"].get()
        }
    
    dados_compilados["agents"] = {}
    if hasattr(aba_agentes, 'parametros_agentes'):
        for nome_agente, widgets in aba_agentes.parametros_agentes.items():
            esta_habilitado = widgets["variavel_controle"].get()
            if esta_habilitado:
                parametros_do_agente = {}
                for chave, widget in widgets.items():
                    if chave not in ("frame_conteiner", "variavel_controle"):
                        parametros_do_agente[chave] = widget.get()
                dados_compilados["agents"][nome_agente] = parametros_do_agente
    
    dados_compilados["io"] = {}
    if hasattr(aba_entrada_saida, 'widgets_armazenados'):
        for chave, widget_entrada in aba_entrada_saida.widgets_armazenados.items():
            dados_compilados["io"][chave] = widget_entrada.get()
            
    return dados_compilados

def construir_aplicacao() -> Tuple[ctk.CTk, callable, ctk.CTkFrame, ctk.CTkFrame, ctk.CTkFrame, ctk.CTkFrame, ctk.CTkFrame, ctk.CTkFrame]:
    janela_principal = ctk.CTk()
    janela_principal.title("RKO-SOLVER")
    centralizar_janela(janela_principal, LARGURA_JANELA, ALTURA_JANELA)
    janela_principal.resizable(False, False)
    ctk.set_appearance_mode('dark')

    for malha in range(10):
        janela_principal.grid_rowconfigure(malha, minsize=20)
        janela_principal.grid_columnconfigure(malha, minsize=20)

    frame_principal = ctk.CTkFrame(
        janela_principal, 
        fg_color=CORES["fundo_principal"], 
        width=1200, 
        height=900, 
        border_width=5, 
        border_color=CORES["borda"]
    )
    frame_principal.grid(row=2, column=2, columnspan=20, sticky="nsew", padx=10)
    frame_principal.grid_rowconfigure(0, weight=1)
    frame_principal.grid_columnconfigure(0, weight=1)
    frame_principal.grid_propagate(False)

    aba_parametros = criar_aba_base(frame_principal)
    aba_agentes = criar_aba_base(frame_principal)
    aba_entrada_saida = criar_aba_base(frame_principal)
    aba_execucao = criar_aba_base(frame_principal)
    aba_grafico = criar_aba_base(frame_principal)
    aba_gantt = criar_aba_base(frame_principal)

    def mostrar_aba(aba_selecionada):
        for aba in (aba_parametros, aba_agentes, aba_entrada_saida, aba_execucao, aba_grafico, aba_gantt):
            aba.grid_forget()
        aba_selecionada.grid(row=0, column=0, sticky="nsew")

    configurar_aba_parametros(aba_parametros)
    configurar_aba_agentes(aba_agentes)
    configurar_aba_entrada_saida(aba_entrada_saida)
    configurar_aba_execucao(aba_execucao, aba_parametros, aba_agentes, aba_entrada_saida)
    configurar_aba_grafico(aba_grafico)
    configurar_aba_gantt_live(aba_gantt)

    mostrar_aba(aba_parametros)

    def ao_fechar_janela():
        print("Encerrando aplicação e matando processos...")
        janela_principal.destroy()
        sys.exit(0)
        
    janela_principal.protocol("WM_DELETE_WINDOW", ao_fechar_janela)

    return janela_principal, mostrar_aba, aba_parametros, aba_agentes, aba_entrada_saida, aba_execucao, aba_grafico, aba_gantt

def configurar_aba_parametros(aba):
    aba.widgets_armazenados = {} 
    
    rotulo_titulo = ctk.CTkLabel(aba, text="HYPER-PARAMETERS", text_color=CORES["destaque"], font=FONTES["titulo"])
    rotulo_titulo.grid(row=0, column=1, sticky="e", columnspan=3)
    
    rotulo_decoder = ctk.CTkLabel(aba, text="SELECT DECODER", font=FONTES["subtitulo"], text_color=CORES["texto"])
    rotulo_decoder.grid(row=1, column=1, padx=10, sticky="s")
    
    combo_decoder = ctk.CTkComboBox(
        aba, 
        values=["ECT", "KSTS", "M3LAW", "INCREMENTAL", "CHEAPEST"], 
        border_color=CORES["primaria"], 
        border_width=2, 
        corner_radius=0, 
        dropdown_fg_color="lavender", 
        dropdown_text_color=CORES["texto_escuro"], 
        dropdown_hover_color=CORES["destaque"]
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
    
    for i in range(3): 
        area_rolagem.grid_columnconfigure(i, weight=1, minsize=360)
    
    aba.parametros_agentes = {} 
    
    cabecalho = ctk.CTkLabel(area_rolagem, text="AGENTS PARAMETERS", font=FONTES["titulo"], text_color=CORES["destaque"])
    cabecalho.grid(row=0, column=0, columnspan=3, sticky="ew", padx=12, pady=(8,12))
    
    configuracao_agentes = {
        "BRKGA": {
            "linha": 1, "coluna": 0, "titulo": "BIASED RANDOM KEY GENETIC ALGORITHM (BRKGA)", 
            "campos": [("Population", "100"), ("Elite set %", "0.20"), ("Mutant set %", "0.10"), ("Inheritance Prob", "0.70")]
        },
        "SA": {
            "linha": 1, "coluna": 1, "titulo": "SIMULATED ANNEALING (SA)", 
            "campos": [("Iterations", "50"), ("alphaSA", "0.99"), ("betaMin", "0.05"), ("betaMax", "0.25"), ("Initial Temperature", "10000")]
        },
        "ILS": {
            "linha": 1, "coluna": 2, "titulo": "ITERATED LOCAL SEARCH (ILS)", 
            "campos": [("betaMin", "0.1"), ("betaMax", "0.20")]
        },
        "VNS": {
            "linha": 2, "coluna": 0, "titulo": "VARIABLE NEIGHBORHOOD SEARCH (VNS)", 
            "campos": [("kMax", "5"), ("betaMin", "0.05")]
        },
        "PSO": {
            "linha": 2, "coluna": 1, "titulo": "PARTICLE SWARM OPTIMIZATION (PSO)", 
            "campos": [("PSize", "100"), ("c1", "2.05"), ("c2", "2.05"), ("w", "0.73")]
        },
        "GA": {
            "linha": 3, "coluna": 0, "titulo": "GENETIC ALGORITHM (GA)", 
            "campos": [("Population", "100"), ("CrosProb", "0.98"), ("MutProb", "0.005")]
        },
        "LNS": {
            "linha": 3, "coluna": 1, "titulo": "LARGE NEIGHBORHOOD SEARCH (LNS)", 
            "campos": [("betaMin", "0.10"), ("betaMax", "0.30"), ("T0", "1000"), ("alphaLNS", "0.95")]
        },
    }
    
    for nome_agente, config in configuracao_agentes.items():
        aba.parametros_agentes[nome_agente] = criar_cartao_agente(area_rolagem, config)

def criar_cartao_agente(conteiner_pai, config):
    frame_agente = ctk.CTkFrame(
        conteiner_pai, fg_color=CORES["fundo_cartao"], width=LARGURA_CARTAO_AGENTE, 
        height=ALTURA_CARTAO_AGENTE, border_width=1, border_color=CORES["borda"]
    )
    frame_agente.grid(row=config["linha"], column=config["coluna"], padx=8, pady=8, sticky="n")
    frame_agente.grid_propagate(False)
    
    rotulo_titulo = ctk.CTkLabel(frame_agente, text=config["titulo"], font=FONTES["corpo_negrito"], text_color=CORES["destaque"])
    rotulo_titulo.grid(row=0, column=0, sticky="w", padx=10, pady=(8,4))
    
    variavel_checkbox = tk.BooleanVar(value=True)
    checkbox = ctk.CTkCheckBox(frame_agente, text="", variable=variavel_checkbox)
    checkbox.grid(row=0, column=1, sticky="e", padx=10, pady=(8,4))
    
    widgets_do_agente = {"frame_conteiner": frame_agente, "variavel_controle": variavel_checkbox}
    
    for indice, (texto_rotulo, valor_padrao) in enumerate(config["campos"], start=1):
        ctk.CTkLabel(frame_agente, text=texto_rotulo, anchor="w", font=FONTES["pequena"]).grid(row=indice, column=0, sticky="w", padx=10, pady=6)
        
        entrada_valor = ctk.CTkEntry(frame_agente, width=90)
        entrada_valor.insert(0, valor_padrao)
        
        coluna_grid = 1 if "coluna" in config and config["coluna"] != 0 else 0
        entrada_valor.grid(row=indice, column=coluna_grid, sticky="e", padx=10 if config["coluna"] != 0 else 0, pady=6)
        
        widgets_do_agente[texto_rotulo] = entrada_valor
        
    return widgets_do_agente

def configurar_aba_entrada_saida(aba):
    aba.widgets_armazenados = {} 
    
    def selecionar_diretorio(widget_entrada):
        pasta_selecionada = filedialog.askdirectory()
        if pasta_selecionada:
            widget_entrada.delete(0, "end")
            widget_entrada.insert(0, pasta_selecionada)
            
    rotulo_titulo = ctk.CTkLabel(aba, text="IO CONFIGURATION", text_color=CORES["destaque"], font=FONTES["titulo"])
    rotulo_titulo.grid(row=0, column=1, columnspan=10, sticky="w", pady=(8,12), padx=70)
    
    try:
        imagem_pontos = ctk.CTkImage(Image.open(resource_path("assets/dots.png")), size=(16, 16))
    except Exception:
        imagem_pontos = None 
        
    secoes_io = [
        ("output_path", "Output Path", 1), 
        ("instance_path", "Instance Folder Path", 2), 
        ("gantt_path", "Gantt Chart Path", 3)
    ]
    
    for chave, texto_rotulo, linha_grid in secoes_io:
        frame_secao = ctk.CTkFrame(aba, fg_color="transparent")
        frame_secao.grid(row=linha_grid, column=0, padx=8, pady=8, sticky="n")
        
        ctk.CTkLabel(frame_secao, text=texto_rotulo, font=FONTES["subtitulo"]).grid(row=0, column=0, padx=8, sticky="w")
        
        entrada_caminho = ctk.CTkEntry(frame_secao, border_color=CORES["primaria"], border_width=2, width=350)
        entrada_caminho.grid(row=1, column=0, padx=10, pady=3)
        aba.widgets_armazenados[chave] = entrada_caminho 
        
        botao_busca = ctk.CTkButton(
            frame_secao, text="" if imagem_pontos else "...", width=30, image=imagem_pontos, 
            fg_color="transparent", hover_color=CORES["destaque"], 
            command=lambda ent=entrada_caminho: selecionar_diretorio(ent)
        )
        botao_busca.grid(row=1, column=1, pady=10)

def configurar_aba_execucao(aba, aba_parametros, aba_agentes, aba_entrada_saida):
    """Configura a aba final com o terminal e lógica de Start/Stop"""
    global ESCRITOR_TERMINAL_GLOBAL, START_BUTTON_GLOBAL
    
    estado_execucao = {"rodando": False}

    def resetar_botao():
        estado_execucao["rodando"] = False
        try:
            if START_BUTTON_GLOBAL:
                START_BUTTON_GLOBAL.configure(state="normal", text='START SOLVER', fg_color="#77198f", hover_color="#9c27b0", border_width=0, text_color="white")
        except Exception: pass

    def ao_passar_mouse(event):
        if estado_execucao["rodando"] and START_BUTTON_GLOBAL:
            START_BUTTON_GLOBAL.configure(text="STOP", fg_color="#C0392B", hover_color="#E74C3C", text_color="white")

    def ao_sair_mouse(event):
        if estado_execucao["rodando"] and START_BUTTON_GLOBAL:
            START_BUTTON_GLOBAL.configure(text="Running...", fg_color="transparent", border_width=2, border_color="#555555", text_color=("gray10", "gray90"))

    def acao_botao():
        if rko_gui_start is None:
            print("ERRO: Middleware 'rko_gui_start' não foi importado.")
            return

        if not estado_execucao["rodando"]:
            dados_coletados = coletar_dados_interface(aba_parametros, aba_agentes, aba_entrada_saida)
            if not dados_coletados: return 

            if ESCRITOR_TERMINAL_GLOBAL:
                ESCRITOR_TERMINAL_GLOBAL.widget_texto.configure(state="normal")
                ESCRITOR_TERMINAL_GLOBAL.widget_texto.delete("1.0", "end")
                ESCRITOR_TERMINAL_GLOBAL.widget_texto.configure(state="disabled")
            
            estado_execucao["rodando"] = True
            START_BUTTON_GLOBAL.configure(text="Running...", fg_color="#555555", border_width=2, border_color="#555555", text_color=("gray10", "gray90"))
            
            print(f"Iniciando otimização com limite de {dados_coletados['hyper_parameters']['time_limit']}s...")
            rko_gui_start.iniciar_resolucao(dados_coletados, manipulador_retorno_interface)

        else:
            print("\n>>> SOLICITANDO PARADA... AGUARDE O FIM DO CICLO ATUAL <<<\n")
            rko_gui_start.solicitar_parada()

    rotulo_execucao = ctk.CTkLabel(aba, text="EXECUTION LOG", text_color=CORES["destaque"], font=FONTES["titulo"])
    rotulo_execucao.grid(row=0, column=0, columnspan=10, sticky="ew", padx=7, pady=(8,0))
    
    botao_iniciar = ctk.CTkButton(
        aba, text='START SOLVER', width=200, height=50, command=acao_botao,
        fg_color="#77198f", hover_color="#9c27b0", font=("Roboto", 18, "bold")
    )
    botao_iniciar.grid(row=1, column=0, columnspan=10, pady=0, padx=20)
    
    botao_iniciar.bind("<Enter>", ao_passar_mouse)
    botao_iniciar.bind("<Leave>", ao_sair_mouse)

    terminal_texto = ctk.CTkTextbox(aba, border_width=2, fg_color="black", text_color="#00FF00", border_color="#2D2D35", font=("Consolas", 13))
    terminal_texto.grid(row=2, column=0, columnspan=10, rowspan=8, sticky="nsew", padx=45, pady=(0,45))
    terminal_texto.configure(state="disabled")

    ESCRITOR_TERMINAL_GLOBAL = RedirecionadorTextoThreadSeguro(terminal_texto)
    START_BUTTON_GLOBAL = botao_iniciar
    START_BUTTON_GLOBAL.resetar_estado = resetar_botao

    sys.stdout = ESCRITOR_TERMINAL_GLOBAL