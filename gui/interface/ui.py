import customtkinter as ctk
import tkinter as tk
from PIL import Image
from tkinter import filedialog
from typing import Tuple
import sys
import os
from datetime import datetime

def resource_path(relative_path):
    #Obtem o caminho absoluto para recursos
    try:
        # PyInstaller cria uma pasta temporária e armazena o caminho em _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

try:
    import backend.rko_gui_start as rko_gui_start
except ImportError:
    print("ERRO: 'rko_gui_start.py' não encontrado.") #debug
    rko_gui_start = None

# DESIGN/PERFUMARIA
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

#Variavel Global para guardar a referencia do terminal (widget de texto)
ESCRITOR_TERMINAL_GLOBAL = None

#Variavel global para o START button (para evitar multiplos cliques)
START_BUTTON_GLOBAL = None

#Classe para Redirecionamento Seguro de Texto 
class RedirecionadorTextoThreadSeguro(object):
    def __init__(self, widget_texto):
        self.widget_texto = widget_texto

    def write(self, texto):
        # Agenda a escrita para a thread principal do Tkinter para evitar travamentos
        try:
            # O método .after(0, ...) coloca a tarefa na fila da interface gráfica
            self.widget_texto.after(0, lambda: self.escrita_segura(texto))
        except Exception:
            # Ignora erros caso a janela já tenha sido fechada durante o processo
            pass 

    def escrita_segura(self, texto):
        try:
            self.widget_texto.configure(state="normal")
            self.widget_texto.insert("end", texto)
            self.widget_texto.see("end") # Rola automaticamente para o final
            self.widget_texto.configure(state="disabled")
        except Exception:
            pass

    def flush(self):
        # Método necessário para compatibilidade com sys.stdout
        pass

#Callback 
def manipulador_retorno_interface(dados):
    """
    Função global que recebe dados do solver e escreve no terminal da interface.
    """
    global ESCRITOR_TERMINAL_GLOBAL, START_BUTTON_GLOBAL
    
    # Se o terminal não estiver inicializado, aborta para evitar erros
    if ESCRITOR_TERMINAL_GLOBAL is None:
        return

    mensagem_formatada = ""
    tipo_status = dados.get("status")

    if tipo_status == "finished":
        mensagem_extra = dados.get("message", "Processo Finalizado.")
        mensagem_formatada =  "\n" + "="*43 + "\n"
        mensagem_formatada += f"   {mensagem_extra}\n"
        mensagem_formatada += "="*43 + "\n\n"

        # Reabilita botao START
        def _reenable_start():
            try:
                if START_BUTTON_GLOBAL is not None:
                    START_BUTTON_GLOBAL.configure(state="normal", text="START SOLVER")
            except Exception:
                pass

        # usa o widget do terminal para agendar na thread principal
        try:
            ESCRITOR_TERMINAL_GLOBAL.widget_texto.after(0, _reenable_start)
        except Exception:
            pass
    
    elif tipo_status == "error":
        mensagem_erro = dados.get('message', 'Erro desconhecido')
        mensagem_formatada = f"\n!!! ERRO CRÍTICO !!!\n{mensagem_erro}\n"

        # Reabilita botao START de forma thread-safe em caso de erro também
        def _reenable_start_err():
            try:
                if START_BUTTON_GLOBAL is not None:
                    START_BUTTON_GLOBAL.configure(state="normal", text="START SOLVER")
            except Exception:
                pass

        try:
            ESCRITOR_TERMINAL_GLOBAL.widget_texto.after(0, _reenable_start_err)
        except Exception:
            pass
    
    elif tipo_status == "running":
        mensagem_status = dados.get('message', 'Rodando')
        mensagem_formatada = f"{mensagem_status}\n"
    
    elif tipo_status == "log":
        texto_log = dados.get("message", "")
        mensagem_formatada = f"{texto_log}\n"

    # Escreve no terminal se houver mensagem
    if mensagem_formatada:
        ESCRITOR_TERMINAL_GLOBAL.write(mensagem_formatada)

# UTILITARIOS E CONSTRUCAO DE INTERFACE

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
    
    # 1. Coleta Hyper-Parameters
    if hasattr(aba_parametros, 'widgets_armazenados'):
        dados_compilados["hyper_parameters"] = {
            "decoder": aba_parametros.widgets_armazenados["decoder"].get(),
            "time_limit": aba_parametros.widgets_armazenados["time_limit"].get(),
            # Captura o novo campo
            "execution_times": aba_parametros.widgets_armazenados["execution_times"].get()
        }
    
    # 2. Coleta Parâmetros dos Agentes (O resto continua igual)
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
    
    # 3. Coleta Caminhos de I/O
    dados_compilados["io"] = {}
    if hasattr(aba_entrada_saida, 'widgets_armazenados'):
        for chave, widget_entrada in aba_entrada_saida.widgets_armazenados.items():
            dados_compilados["io"][chave] = widget_entrada.get()
            
    return dados_compilados

def construir_aplicacao() -> Tuple[ctk.CTk, callable, ctk.CTkFrame, ctk.CTkFrame, ctk.CTkFrame, ctk.CTkFrame]:
    janela_principal = ctk.CTk()
    janela_principal.title("RKO-SOLVER")
    centralizar_janela(janela_principal, LARGURA_JANELA, ALTURA_JANELA)
    janela_principal.resizable(False, False)
    ctk.set_appearance_mode('dark')

    # Configuração do Grid Principal
    for malha in range(10):
        janela_principal.grid_rowconfigure(malha, minsize=20)
        janela_principal.grid_columnconfigure(malha, minsize=20)

    # Frame Principal que segura as abas
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

    # Criação das Abas
    aba_parametros = criar_aba_base(frame_principal)
    aba_agentes = criar_aba_base(frame_principal)
    aba_entrada_saida = criar_aba_base(frame_principal)
    aba_execucao = criar_aba_base(frame_principal)

    def mostrar_aba(aba_selecionada):
        for aba in (aba_parametros, aba_agentes, aba_entrada_saida, aba_execucao):
            aba.grid_forget()
        aba_selecionada.grid(row=0, column=0, sticky="nsew")

    # Configuração do Conteúdo de cada Aba
    configurar_aba_parametros(aba_parametros)
    configurar_aba_agentes(aba_agentes)
    configurar_aba_entrada_saida(aba_entrada_saida)
    configurar_aba_execucao(aba_execucao, aba_parametros, aba_agentes, aba_entrada_saida)

    # Inicia mostrando a primeira aba
    mostrar_aba(aba_parametros)
    
    return janela_principal, mostrar_aba, aba_parametros, aba_agentes, aba_entrada_saida, aba_execucao

# CONFIGURACAO DE CADA ABA
def configurar_aba_parametros(aba):
    aba.widgets_armazenados = {} 
    
    rotulo_titulo = ctk.CTkLabel(aba, text="HYPER-PARAMETERS", text_color=CORES["destaque"], font=FONTES["titulo"])
    rotulo_titulo.grid(row=0, column=1, sticky="e", columnspan=3)
    
    # --- COLUNA 1: DECODER ---
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
    
    # --- COLUNA 2: TIME LIMIT ---
    rotulo_tempo = ctk.CTkLabel(aba, text="TIME LIMIT (S)", font=FONTES["subtitulo"], text_color=CORES["texto"])
    rotulo_tempo.grid(row=1, column=2, sticky="s") # Ajustado para sticky="s" para alinhar
    
    entrada_tempo = ctk.CTkEntry(aba, width=90, corner_radius=0, border_color=CORES["primaria"], border_width=2)
    entrada_tempo.insert(0,"60")
    entrada_tempo.grid(row=2, column=2, padx=15, sticky="n", pady=5)
    aba.widgets_armazenados["time_limit"] = entrada_tempo 

    # --- COLUNA 3: EXECUTION TIMES ---
    rotulo_execucoes = ctk.CTkLabel(aba, text="EXECUTION TIMES", font=FONTES["subtitulo"], text_color=CORES["texto"])
    rotulo_execucoes.grid(row=1, column=3, sticky="s")
    
    entrada_execucoes = ctk.CTkEntry(aba, width=90, corner_radius=0, border_color=CORES["primaria"], border_width=2)
    entrada_execucoes.insert(0, "1") # Valor padrão 1
    entrada_execucoes.grid(row=2, column=3, padx=15, sticky="n", pady=5)
    aba.widgets_armazenados["execution_times"] = entrada_execucoes
    
def configurar_aba_agentes(aba):
    # Area de rolagem para caber todos os agentes
    area_rolagem = ctk.CTkScrollableFrame(aba, width=1160, height=860, fg_color="transparent")
    area_rolagem.grid(row=0, column=0, columnspan=10, rowspan=10, padx=10, pady=10, sticky="nsew")
    
    for i in range(3): 
        area_rolagem.grid_columnconfigure(i, weight=1, minsize=360)
    
    aba.parametros_agentes = {} 
    
    cabecalho = ctk.CTkLabel(area_rolagem, text="AGENTS PARAMETERS", font=FONTES["titulo"], text_color=CORES["destaque"])
    cabecalho.grid(row=0, column=0, columnspan=3, sticky="ew", padx=12, pady=(8,12))
    
    # dicionario de configuracao
    configuracao_agentes = {
        "BRKGA": {
            "linha": 1, "coluna": 0, "titulo": "BIASED RANDOM KEY GENETIC ALGORITHM (BRKGA)", 
            "campos": [("Population", "100"), ("Elite set", "0.20"), ("Mutant set", "0.10"), ("Elite parent inheritance prob", "0.70")]
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
            "campos": [("PSize", "100"), ("c1", "2.05"), ("betaMin", "2.05"), ("betaMax", "0.73")]
        },
        "GA1": {
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
    """Cria o cartão visual (Frame) para um agente específico"""
    frame_agente = ctk.CTkFrame(
        conteiner_pai, 
        fg_color=CORES["fundo_cartao"], 
        width=LARGURA_CARTAO_AGENTE, 
        height=ALTURA_CARTAO_AGENTE, 
        border_width=1, 
        border_color=CORES["borda"]
    )
    frame_agente.grid(row=config["linha"], column=config["coluna"], padx=8, pady=8, sticky="n")
    frame_agente.grid_propagate(False) # Impede que o frame encolha ou cresça
    
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
        
        # Ajuste fino de layout se não for a primeira coluna
        coluna_grid = 1 if "coluna" in config and config["coluna"] != 0 else 0
        entrada_valor.grid(row=indice, column=coluna_grid, sticky="e", padx=10 if config["coluna"] != 0 else 0, pady=6)
        
        widgets_do_agente[texto_rotulo] = entrada_valor
        
    return widgets_do_agente

def configurar_aba_entrada_saida(aba):
    """Configura a aba de caminhos de arquivos (IO)"""
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
            frame_secao, 
            text="" if imagem_pontos else "...", 
            width=30, 
            image=imagem_pontos, 
            fg_color="transparent", 
            hover_color=CORES["destaque"], 
            command=lambda ent=entrada_caminho: selecionar_diretorio(ent)
        )
        botao_busca.grid(row=1, column=1, pady=10)

def configurar_aba_execucao(aba, aba_parametros, aba_agentes, aba_entrada_saida):
    """Configura a aba final com o terminal e botao de start"""
    global ESCRITOR_TERMINAL_GLOBAL, START_BUTTON_GLOBAL
    
    def ao_clicar_iniciar():
        if rko_gui_start is None:
            print("ERRO: Middleware 'rko_gui_start' não foi importado.")
            return

        dados_coletados = coletar_dados_interface(aba_parametros, aba_agentes, aba_entrada_saida)
        
        # Limpa o terminal antes de comecar
        if ESCRITOR_TERMINAL_GLOBAL:
            ESCRITOR_TERMINAL_GLOBAL.widget_texto.configure(state="normal")
            ESCRITOR_TERMINAL_GLOBAL.widget_texto.delete("1.0", "end")
            ESCRITOR_TERMINAL_GLOBAL.widget_texto.configure(state="disabled")
        
        print(f"Iniciando otimização com limite de {dados_coletados['hyper_parameters']['time_limit']}s...")
        inicio = datetime.now()
        print("inicio: "+inicio.strftime("%d/%m %H:%M:%S"))
        # Desabilita o botao START apos clicar
        try:
            if START_BUTTON_GLOBAL is not None:
                START_BUTTON_GLOBAL.configure(state="disabled", text="RUNNING...")
        except Exception:
            pass

        # Inicia a computacao e envia a funcao de callback para garantir comunicacao
        rko_gui_start.iniciar_resolucao(dados_coletados, manipulador_retorno_interface)

    # Layout da Aba de Execucao
    rotulo_execucao = ctk.CTkLabel(aba, text="EXECUTION LOG", text_color=CORES["destaque"], font=FONTES["titulo"])
    rotulo_execucao.grid(row=0, column=3, columnspan=3, sticky="ew", padx=7, pady=(8,12))
    
    botao_iniciar = ctk.CTkButton(
        aba, 
        text='START SOLVER', 
        width=200, 
        height=50, 
        command=ao_clicar_iniciar,
        fg_color="#77198f", 
        hover_color="#9c27b0",
        font=("Roboto", 18, "bold")
    )
    botao_iniciar.grid(row=1, column=2, sticky="n", pady=20, padx=20)
    
    terminal_texto = ctk.CTkTextbox(
        aba, 
        width=580, 
        height=600, 
        border_width=2, 
        fg_color="black", 
        text_color="#00FF00",
        border_color="#2D2D35", 
        font=("Consolas", 12)
    )
    terminal_texto.grid(row=1, column=3, sticky="nsew", rowspan=5, padx=10, pady=10)
    terminal_texto.configure(state="disabled")

    # Inicializa o Escritor Global apontando para este terminal
    ESCRITOR_TERMINAL_GLOBAL = RedirecionadorTextoThreadSeguro(terminal_texto)
    
    # Redireciona prints do Python para o terminal da GUI
    sys.stdout = ESCRITOR_TERMINAL_GLOBAL

    # Guarda referencia global do botao START (para bloquear/reabilitar)
    START_BUTTON_GLOBAL = botao_iniciar
