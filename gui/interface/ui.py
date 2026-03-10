import customtkinter as ctk
import tkinter as tk
from tkinter import ttk
from PIL import Image
from tkinter import filedialog, messagebox
from typing import Tuple
from datetime import datetime
import sys
import os
import re
import time
import json
import threading
import pickle 
import matplotlib
import math
import statistics
import numpy as np
import io
import base64
import tempfile
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib import ticker
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

try:
    from interface.buttons import create_buttons
except ImportError:
    # Fallback se rodar o arquivo diretamente fora do pacote
    try:
        from buttons import create_buttons
    except:
        print("Erro ao importar buttons.py")

matplotlib.use("TkAgg")

RE_NEW_BEST = re.compile(r"NEW BEST: (\d+\.\d+)")

try:
    import backend.rko_gui_start as rko_gui_start
    pasta_backend_real = os.path.dirname(os.path.abspath(rko_gui_start.__file__))
    CAMINHO_CACHE_IO = os.path.join(pasta_backend_real, "temp_io_paths.txt")
except ImportError:
    print("[ERROR] 'rko_gui_start.py' not found in PATH.") 
    rko_gui_start = None
    CAMINHO_CACHE_IO = "temp_io_paths.txt"

def resource_path(relative_path):
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
    "corpo_negrito": ("Roboto", 10, "bold"),
    "pequena": ("Roboto", 11)
}

SUPPRESS_DELETE_WARNING = False
INSTANCIAS_OCULTAS = set() # Guarda as chaves que não devem aparecer no gráfico
ICONES_UI = {} # Cache para não recarregar imagens toda hora

LARGURA_JANELA = 1375
ALTURA_JANELA = 975
LARGURA_CARTAO_AGENTE = 360
ALTURA_CARTAO_AGENTE = 260

DIRETORIO_BASE = os.path.dirname(os.path.abspath(__file__))

ESCRITOR_TERMINAL_GLOBAL = None
START_BUTTON_GLOBAL = None
PAUSE_BUTTON_GLOBAL = None 
SAVE_BUTTON_GLOBAL = None  
MONOTONIC_FILTER = None 

FIG_GLOBAL = None
AX_GLOBAL = None
CANVAS_GLOBAL = None
LINHA_GLOBAL = None
DADOS_X = []
DADOS_Y = []
NOME_INSTANCIA_ATUAL = "Waiting..."

FIG_GANTT = None
AX_GANTT = None
CANVAS_GANTT = None
MELHOR_MAKESPAN_ATUAL = float('inf')
TEMPO_INICIO_BATERIA = 0

HISTORICO_DATA = {}
FILA_BOTOES_PENDENTES = []
FRAME_LISTA_HISTORICO = None
SETS_CRIADOS = set()

#  GLOBAIS PARA NAVEGAÇÃO DA ANÁLISE 
ABA_ANALISE_GLOBAL = None
FUNCAO_SHOW_TAB_GLOBAL = None

FIG_HIST_LINHA, AX_HIST_LINHA, CANVAS_HIST_LINHA = None, None, None
FIG_HIST_GANTT, AX_HIST_GANTT, CANVAS_HIST_GANTT = None, None, None

VAR_FILTRO_INSTANCIA = None
VAR_FILTRO_DECODER = None
VARS_FILTRO_AGENTES = {}
CHAVE_SELECIONADA_ATUAL = None

LISTA_REF_WORKERS = []
TEMPO_FINAL_CACHE = 0.0

# --- VARIÁVEL GLOBAL DO AUTO-SAVE ---
AUTO_DUMP_ATIVO = False
VAR_PERIODIC_DUMP = None
VAR_DUMP_PREFIX = None

COMBO_INSTANCIAS = None
VAR_ORDENACAO_HISTORICO = None

# Filtro que descarta valores piores do que o melhor atual
class MonotonicFilter:
    def __init__(self, widget_texto):
        self.widget = widget_texto
        self.best_seen = float('inf')
        self.lock = threading.Lock()

    def reset(self):
        with self.lock:
            self.best_seen = float('inf')

    def print_if_better(self, text, makespan_val):
        with self.lock:
            val = float(makespan_val)
            # Ignora valores piores ou iguais ao recorde atual
            if val >= (self.best_seen - 0.0001):
                return 
            
            self.best_seen = val
            self._safe_print(text)

    def print_direct(self, text):
        self._safe_print(text)

    def _safe_print(self, text):
        try:
            self.widget.configure(state="normal")
            self.widget.insert("end", text)
            self.widget.see("end")
            self.widget.configure(state="disabled")
        except: pass

class CTkTooltip:
    """
    Cria uma janela de 'dica' (tooltip) que aparece após um delay
    ao passar o mouse sobre um widget.
    """
    def __init__(self, widget, text, delay=500):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tooltip_window = None
        self.id_after = None
        
        # Adiciona eventos com add="+" para não sobrescrever os binds existentes do card
        self.widget.bind("<Enter>", self.schedule, add="+")
        self.widget.bind("<Leave>", self.hide, add="+")
        self.widget.bind("<ButtonPress>", self.hide, add="+")

    def schedule(self, event=None):
        self.unschedule()
        self.id_after = self.widget.after(self.delay, self.show)

    def unschedule(self):
        if self.id_after:
            self.widget.after_cancel(self.id_after)
            self.id_after = None

    def show(self):
        if not self.text: return
        
        # Cria a janela flutuante
        self.tooltip_window = ctk.CTkToplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True) # Remove barra de título
        self.tooltip_window.wm_attributes("-topmost", True) # Sempre no topo
        
        # Pega posição do mouse
        x = self.widget.winfo_pointerx() + 15
        y = self.widget.winfo_pointery() + 10
        self.tooltip_window.wm_geometry(f"+{x}+{y}")

        # Label dentro do tooltip
        label = ctk.CTkLabel(
            self.tooltip_window, 
            text=self.text, 
            fg_color="#111111",      # Fundo quase preto
            text_color="#E0E0E0",    # Texto claro
            corner_radius=6,
            font=("Roboto", 10),
            padx=10, pady=5
        )
        label.pack()

    def hide(self, event=None):
        self.unschedule()
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

class StdoutRedirector:
    def __init__(self, filtro):
        self.filtro = filtro

    def write(self, text):
        if not text.strip(): return
        
        match = RE_NEW_BEST.search(text)
        if match:
            try:
                val = float(match.group(1))
                self.filtro.print_if_better(text + "\n", val)
                return
            except: pass
        
        self.filtro.print_direct(text)

    def flush(self): pass

class CustomToolbar(NavigationToolbar2Tk):
    def save_figure(self, *args):
        # Descobre qual é a janela atual (Toplevel) onde o gráfico está
        top_level = self.canvas.get_tk_widget().winfo_toplevel()
        
        # Obtém os formatos suportados pelo backend
        filetypes = self.canvas.get_supported_filetypes()
        default_filetype = self.canvas.get_default_filetype()
        
        # Formata para o padrão do Tkinter
        tk_filetypes = []
        for name, ext in filetypes.items():
            tk_filetypes.append((name, ext))
        
        # Abre o diálogo FORÇANDO o parent correto
        fname = filedialog.asksaveasfilename(
            parent=top_level,  
            title="Save the figure",
            filetypes=tk_filetypes,
            defaultextension=default_filetype
        )

        if fname:
            try:
                self.canvas.figure.savefig(fname)
            except Exception as e:
                messagebox.showerror("Error saving file", str(e), parent=top_level)

class ConfirmDeleteDialog(ctk.CTkToplevel):
    def __init__(self, parent, on_confirm_callback):
        super().__init__(parent)
        
        self.on_confirm = on_confirm_callback
        
        # 1. Configurações Iniciais
        self.title("Safety Check")
        self.geometry("350x200") # Aumentei um pouco a altura para caber a imagem confortavelmente
        self.resizable(False, False)
        
        try:
            x = parent.winfo_rootx() + (parent.winfo_width() // 2) - 175
            y = parent.winfo_rooty() + (parent.winfo_height() // 2) - 100
            self.geometry(f"+{x}+{y}")
        except: pass
        
        # 2. CONSTRÓI A INTERFACE
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1) 
        
        frm = ctk.CTkFrame(self, fg_color="transparent")
        frm.pack(fill="both", expand=True, padx=20, pady=20)
        
        # --- ÍCONE DE ALERTA (IMAGEM COM FALLBACK) ---
        try:
            # Tenta carregar a imagem 'warning.png' da pasta assets
            # Defini um tamanho de 48x48, ajuste se necessário.
            img_warning = ctk.CTkImage(Image.open("assets/warning.png"), size=(48, 48))
            
            # Cria o label com a imagem e sem texto
            lbl_icon = ctk.CTkLabel(frm, text="", image=img_warning)
            lbl_icon.pack(pady=(0, 10))
        except Exception as e:
            # Se der erro (ex: arquivo não existe), usa o emoji antigo como fallback
            print(f"Aviso: Não foi possível carregar assets/warning.png: {e}")
            ctk.CTkLabel(frm, text="⚠️", font=("Arial", 35)).pack(pady=(0, 5))
        # -------------------------------------------
        
        # Mensagem
        ctk.CTkLabel(frm, text="Are you sure you want to delete this item?", 
                     font=("Roboto", 13, "bold"), text_color="white").pack(pady=(0, 10))
        
        # Checkbox
        self.var_suppress = ctk.BooleanVar(value=False)
        chk = ctk.CTkCheckBox(frm, text="Don't show this message again", 
                              variable=self.var_suppress, 
                              font=("Roboto", 11), text_color="gray",
                              checkbox_width=18, checkbox_height=18, border_width=2)
        chk.pack(pady=(0, 15))
        
        # Botões
        frm_btns = ctk.CTkFrame(frm, fg_color="transparent")
        frm_btns.pack(fill="x")
        
        btn_cancel = ctk.CTkButton(frm_btns, text="Cancel", fg_color="transparent", 
                                   border_width=1, border_color="gray", 
                                   width=100, command=self.destroy)
        btn_cancel.pack(side="left", padx=(0, 10), expand=True)
        
        btn_delete = ctk.CTkButton(frm_btns, text="Delete", fg_color="#C0392B", 
                                   hover_color="#E74C3C", width=100, 
                                   command=self.acao_confirmar)
        btn_delete.pack(side="right", padx=(0, 0), expand=True)

        # 3. APLICA A MODALIDADE COM SEGURANÇA
        self.transient(parent) 
        self.wait_visibility() 
        self.grab_set() 
        self.focus_force()

    def acao_confirmar(self):
        global SUPPRESS_DELETE_WARNING
        if self.var_suppress.get():
            SUPPRESS_DELETE_WARNING = True
            
        self.on_confirm()
        self.destroy()

def fazer_dump_automatico():
    """Salva um clone do experimento e retorna a string de sucesso para o terminal."""
    import os
    import pickle
    import re
    from datetime import datetime
    
    global HISTORICO_DATA, AUTO_DUMP_ATIVO, DADOS_X, DADOS_Y, MELHOR_MAKESPAN_ATUAL, NOME_INSTANCIA_ATUAL
    global SETS_CRIADOS, SETS_DESCRICOES, VAR_DUMP_PREFIX
    
    if not AUTO_DUMP_ATIVO: return None
    if not HISTORICO_DATA: return None
        
    prefixo_str = ""
    try:
        if VAR_DUMP_PREFIX:
            texto_sujo = VAR_DUMP_PREFIX.get().strip()
            # Remove qualquer caractere que quebre o nome do arquivo no Windows/Linux
            texto_limpo = re.sub(r'[\\/*?:"<>|]', "", texto_sujo)
            if texto_limpo:
                prefixo_str = f"{texto_limpo}-"
    except Exception:
        pass
    # -------------------------------------------------------

    pasta_dumps = os.path.join("backend", "dumps")
    os.makedirs(pasta_dumps, exist_ok=True)
    
    timestamp = datetime.now().strftime("%y-%m-%d-%H-%M-%S")
    # Aplica o prefixo dinamicamente (se estiver vazio, fica o padrão normal)
    nome_arquivo = f"{prefixo_str}dump-{timestamp}.pkl"
    caminho = os.path.join(pasta_dumps, nome_arquivo)
    
    estado_ui = {
        "historico": HISTORICO_DATA, 
        "dados_grafico_x": list(DADOS_X) if 'DADOS_X' in globals() else [], 
        "dados_grafico_y": list(DADOS_Y) if 'DADOS_Y' in globals() else [], 
        "melhor": MELHOR_MAKESPAN_ATUAL if 'MELHOR_MAKESPAN_ATUAL' in globals() else float('inf'), 
        "instancia": NOME_INSTANCIA_ATUAL if 'NOME_INSTANCIA_ATUAL' in globals() else "AutoDump",
        "sets_criados": SETS_CRIADOS if 'SETS_CRIADOS' in globals() else {},
        "sets_descricoes": SETS_DESCRICOES if 'SETS_DESCRICOES' in globals() else {}
    }
    
    estado_backend = {}
    if 'rko_gui_start' in globals() and hasattr(globals()['rko_gui_start'], 'obter_estado_checkpoint'):
        estado_backend = globals()['rko_gui_start'].obter_estado_checkpoint()
    
    dump_completo = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
        "ui": estado_ui, 
        "backend": estado_backend
    }
    
    with open(caminho, 'wb') as f:
        pickle.dump(dump_completo, f)
        
    # Retorna o texto para ser impresso em sincronia perfeita
    return f">>> [Auto-Save] Progress saved: {nome_arquivo}\n\n"

def carregar_cache_caminhos():
    if os.path.exists(CAMINHO_CACHE_IO):
        try:
            with open(CAMINHO_CACHE_IO, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[ERROR] reading IO cache: {e}")
    return {}

def salvar_cache_caminhos(inst_path, out_path, gantt_path):
    dados = {
        "instance_path": inst_path,
        "output_path": out_path,
        "gantt_path": gantt_path
    }
    try:
        with open(CAMINHO_CACHE_IO, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=4)
    except Exception as e:
        print(f"[WARN] writing IO cache: {e}")

def iniciar_watchdog_historico():
    global FILA_BOTOES_PENDENTES, VAR_FILTRO_INSTANCIA
    if FILA_BOTOES_PENDENTES:
        FILA_BOTOES_PENDENTES.clear()
        aplicar_filtros_historico()
    if FRAME_LISTA_HISTORICO:
        FRAME_LISTA_HISTORICO.after(1000, iniciar_watchdog_historico)

def configurar_aba_grafico(aba):
    global FIG_GLOBAL, AX_GLOBAL, CANVAS_GLOBAL, LINHA_GLOBAL
    frame = ctk.CTkFrame(aba, fg_color="transparent")
    frame.pack(fill="both", expand=True, padx=10, pady=10)

    plt.style.use('dark_background') 
    FIG_GLOBAL, AX_GLOBAL = plt.subplots(figsize=(5, 4), dpi=100)
    FIG_GLOBAL.patch.set_facecolor('#242424') 
    AX_GLOBAL.set_facecolor('#2b2b2b')
    AX_GLOBAL.set_title("Convergence of Makespan (updated in real time)", fontsize=10, color="white")
    AX_GLOBAL.set_xlabel("Time (sec)", fontsize=9, color="white")
    AX_GLOBAL.set_ylabel("Makespan (cost)", fontsize=9, color="white")
    AX_GLOBAL.grid(True, linestyle='--', alpha=0.3)
    
    LINHA_GLOBAL, = AX_GLOBAL.plot([], [], color='#00FF00', linewidth=2, marker='o', markersize=4)
    
    CANVAS_GLOBAL = FigureCanvasTkAgg(FIG_GLOBAL, master=frame)
    CANVAS_GLOBAL.draw()
    CANVAS_GLOBAL.get_tk_widget().pack(fill="both", expand=True)
    CustomToolbar(CANVAS_GLOBAL, frame).pack(side="bottom", fill="x")
    return frame

def configurar_aba_gantt_live(aba):
    global FIG_GANTT, AX_GANTT, CANVAS_GANTT
    frame = ctk.CTkFrame(aba, fg_color="transparent")
    frame.pack(fill="both", expand=True, padx=10, pady=10)

    plt.style.use('dark_background') 
    FIG_GANTT, AX_GANTT = plt.subplots(figsize=(5, 4), dpi=100)
    FIG_GANTT.patch.set_facecolor('#242424') 
    AX_GANTT.set_facecolor('#212121')
    AX_GANTT.set_title("Current Schedule (updated in real time)", fontsize=10, color="white")
    AX_GANTT.set_xlabel("Horizon", fontsize=9, color="white")
    AX_GANTT.set_ylabel("Machines", fontsize=9, color="white")
    AX_GANTT.grid(True, linestyle='--', alpha=0.1, color='white')

    CANVAS_GANTT = FigureCanvasTkAgg(FIG_GANTT, master=frame)
    CANVAS_GANTT.draw()
    CANVAS_GANTT.get_tk_widget().pack(fill="both", expand=True)
    CustomToolbar(CANVAS_GANTT, frame).pack(side="bottom", fill="x")
    return frame

def atualizar_grafico_comparativo():
    """
    Redesenha o gráfico de linhas garantindo que a curva seja estritamente decrescente (Monotônica).
    - Selecionado: Cor do Set (se houver) ou Verde. Sólido.
    - Não Selecionado: Cor do Set (se houver) ou Branco. Transparente.
    """
    global AX_HIST_LINHA, CANVAS_HIST_LINHA, HISTORICO_DATA, INSTANCIAS_OCULTAS
    global VAR_FILTRO_INSTANCIA, VAR_FILTRO_DECODER, VARS_FILTRO_AGENTES, CHAVE_SELECIONADA_ATUAL, SETS_CRIADOS

    if not AX_HIST_LINHA: return

    AX_HIST_LINHA.clear()
    
    # --- REAPLICA OS FILTROS ---
    f_inst = VAR_FILTRO_INSTANCIA.get()
    f_dec = VAR_FILTRO_DECODER.get()
    agentes_requeridos = [nome for nome, var in VARS_FILTRO_AGENTES.items() if var.get()]

    plotados = 0
    ocultos_pelo_olho = 0

    for chave, dados in HISTORICO_DATA.items():
        # 1. Filtros Dropdown
        if f_inst != "all" and dados['meta_nome'] != f_inst: continue
        if f_dec != "all" and dados['meta_decoder'].lower() != f_dec.lower(): continue
        
        # 2. Filtro de Agentes
        if agentes_requeridos:
            raw_agentes = dados.get('meta_agentes', [])
            if isinstance(raw_agentes, str):
                lista_no_historico = [x.strip() for x in raw_agentes.split("-") if x.strip()]
            else:
                lista_no_historico = raw_agentes

            nomes_limpos = [item.split("[")[0].strip() for item in lista_no_historico]
            if not all(req in nomes_limpos for req in agentes_requeridos): 
                continue

        # 3. Filtro de Visibilidade
        if chave in INSTANCIAS_OCULTAS:
            ocultos_pelo_olho += 1
            continue

        # 4. Dados
        raw_x, raw_y = dados['x'], dados['y']
        if not raw_x or not raw_y: continue
        
        # Ordena por tempo (Eixo X)
        pares_ordenados = sorted(zip(raw_x, raw_y), key=lambda p: p[0])
        
        # --- NOVO: Filtro Monotônico (Corrige o bug da curva subindo) ---
        mono_x = []
        mono_y = []
        melhor_y_ate_agora = float('inf')
        
        for px, py in pares_ordenados:
            if py < melhor_y_ate_agora:
                melhor_y_ate_agora = py
                mono_x.append(px)
                mono_y.append(py)
            elif py == melhor_y_ate_agora:
                # Mantém platôs (linha reta no final) se o tempo for maior
                if mono_x and px > mono_x[-1]:
                    mono_x.append(px)
                    mono_y.append(py)
                    
        eixo_x, eixo_y = mono_x, mono_y
        # ----------------------------------------------------------------
        
        # --- DEFINIÇÃO DE COR ---
        tem_set = "set_color" in dados and dados["set_color"]
        
        if chave == CHAVE_SELECIONADA_ATUAL:
            # SELECIONADO: Set Color ou Verde (Sólido, Marcadores)
            cor_linha = dados["set_color"] if tem_set else '#00FF00'
            AX_HIST_LINHA.plot(eixo_x, eixo_y, color=cor_linha, linewidth=2.5, 
                               marker='o', markersize=4, label="Selected", zorder=10)
        else:
            # NÃO SELECIONADO: Set Color ou Branco (Transparente, Sem Marcadores)
            cor_linha = dados["set_color"] if tem_set else 'white'
            alpha_val = 0.6 if tem_set else 0.4
            
            AX_HIST_LINHA.plot(eixo_x, eixo_y, color=cor_linha, alpha=alpha_val, linewidth=1.5)
        
        plotados += 1

    # --- TÍTULO ---
    titulo = f"Convergence Curves (Visible: {plotados} | Hidden: {ocultos_pelo_olho})"
    if CHAVE_SELECIONADA_ATUAL and CHAVE_SELECIONADA_ATUAL in HISTORICO_DATA:
        if CHAVE_SELECIONADA_ATUAL not in INSTANCIAS_OCULTAS:
             dados_sel = HISTORICO_DATA[CHAVE_SELECIONADA_ATUAL]
             best_val = min(dados_sel['y']) if dados_sel['y'] else "?"
             
             info_set = ""
             if "set_color" in dados_sel and dados_sel["set_color"]:
                 cor = dados_sel["set_color"]
                 # Garante que SETS_CRIADOS existe (segurança)
                 nome_set = SETS_CRIADOS.get(cor, "Set") if 'SETS_CRIADOS' in globals() and SETS_CRIADOS else "Set"
                 info_set = f" | [{nome_set}]"

             titulo = f"Selected: {dados_sel['meta_nome']} (Best: {best_val}){info_set}"

    AX_HIST_LINHA.set_title(titulo, color="white", fontsize=10)
    AX_HIST_LINHA.grid(True, linestyle='--', alpha=0.3)
    AX_HIST_LINHA.relim()
    AX_HIST_LINHA.autoscale_view()
    CANVAS_HIST_LINHA.draw()

def aplicar_filtros_historico(evento=None):
    global FRAME_LISTA_HISTORICO, HISTORICO_DATA, VAR_FILTRO_INSTANCIA, VAR_FILTRO_DECODER, VARS_FILTRO_AGENTES, CHAVE_SELECIONADA_ATUAL, COMBO_INSTANCIAS, VAR_ORDENACAO_HISTORICO
    global INSTANCIAS_OCULTAS, AX_HIST_LINHA, CANVAS_HIST_LINHA, SUPPRESS_DELETE_WARNING, SETS_CRIADOS, ICONES_UI

    carregar_icones()

    if SETS_CRIADOS is None: SETS_CRIADOS = {}
    
    for v in HISTORICO_DATA.values():
        cor = v.get("set_color")
        if cor and cor not in SETS_CRIADOS:
            SETS_CRIADOS[cor] = f"Set {cor.upper()}"

    for widget in FRAME_LISTA_HISTORICO.winfo_children():
        widget.destroy()

    # --- (FILTROS) ---
    f_inst = VAR_FILTRO_INSTANCIA.get()
    f_dec = VAR_FILTRO_DECODER.get()
    f_sort = VAR_ORDENACAO_HISTORICO.get()
    agentes_requeridos = [nome for nome, var in VARS_FILTRO_AGENTES.items() if var.get()]
    
    if COMBO_INSTANCIAS and HISTORICO_DATA:
        nomes_unicos = sorted(list(set([v['meta_nome'] for v in HISTORICO_DATA.values()])))
        COMBO_INSTANCIAS.configure(values=["all"] + nomes_unicos)

    chaves_filtradas = []
    for chave, dados in HISTORICO_DATA.items():
        if f_inst != "all" and dados['meta_nome'] != f_inst: continue
        if f_dec != "all" and dados['meta_decoder'].lower() != f_dec.lower(): continue
        
        if agentes_requeridos:
            raw_agentes = dados.get('meta_agentes', [])
            if isinstance(raw_agentes, str): lista_no_historico = [x.strip() for x in raw_agentes.split("-") if x.strip()]
            else: lista_no_historico = raw_agentes
            nomes_limpos_no_historico = [item.split("[")[0].strip() for item in lista_no_historico]
            if not all(req in nomes_limpos_no_historico for req in agentes_requeridos): continue

        chaves_filtradas.append(chave)

    def get_mksp(k): return min(HISTORICO_DATA[k]['y']) if HISTORICO_DATA[k]['y'] else float('inf')
    
    if f_sort == "Descending Date/Hour":
        try: chaves_filtradas.sort(key=lambda k: datetime.strptime(HISTORICO_DATA[k]['meta_hora'], "%d/%m/%y %H:%M:%S"), reverse=True)
        except: chaves_filtradas.sort()
    elif f_sort == "Ascending Makespan": chaves_filtradas.sort(key=get_mksp, reverse=False)
    elif f_sort == "Descending Makespan": chaves_filtradas.sort(key=get_mksp, reverse=True)
    elif f_sort == "Ascending Instance": chaves_filtradas.sort(key=lambda k: HISTORICO_DATA[k]['meta_nome'])
    elif f_sort == "Descending Instance": chaves_filtradas.sort(key=lambda k: HISTORICO_DATA[k]['meta_nome'], reverse=True)
    elif f_sort == "Decoder": chaves_filtradas.sort(key=lambda k: HISTORICO_DATA[k]['meta_decoder'])
    else: chaves_filtradas.sort(reverse=True)

    atualizar_grafico_comparativo()

    # --- HELPERS ---
    def ajustar_cor_hover(hex_color):
        if not hex_color or hex_color == "transparent": return "#555555"
        hex_color = hex_color.lstrip('#')
        try: rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        except: return "#555555"
        lum = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
        if lum > 160: 
            fator = 0.8; offset = 0
        else: 
            fator = 1.3; offset = 30 
        new_rgb = tuple(min(255, int(max(0, c * fator + (offset if fator > 1 else 0)))) for c in rgb)
        return f"#{new_rgb[0]:02x}{new_rgb[1]:02x}{new_rgb[2]:02x}"

    def gerar_icone_colorido(nome_base, hex_color):
        if not hex_color or hex_color == "transparent": 
            return ICONES_UI[nome_base]
        try:
            path = resource_path(f"assets/{nome_base}.png")
            img_original = Image.open(path).convert("RGBA")
            img_cor = Image.new("RGBA", img_original.size, hex_color)
            img_final = Image.new("RGBA", img_original.size, (0, 0, 0, 0))
            img_final.paste(img_cor, (0, 0), mask=img_original)
            return ctk.CTkImage(img_final, size=(16, 16))
        except:
            return ICONES_UI[nome_base]

    # --- POPUPS ---
    def abrir_editor_notas(k, widget_origem=None):
        root = FRAME_LISTA_HISTORICO.winfo_toplevel()
        top = ctk.CTkToplevel(root)
        top.title("Notes")
        top.geometry("400x300")
        if widget_origem:
            try: top.geometry(f"+{widget_origem.winfo_rootx()}+{widget_origem.winfo_rooty()}")
            except: pass
        top.transient(root)
        top.focus_force()
        
        ctk.CTkLabel(top, text=f"Notes: {HISTORICO_DATA[k]['meta_nome']}", font=("Roboto", 12, "bold")).pack(pady=10)
        txt = ctk.CTkTextbox(top, width=360, height=180, border_width=2)
        txt.pack(pady=5)
        txt.insert("0.0", HISTORICO_DATA[k].get("user_notes", ""))
        
        def salvar_nota():
            HISTORICO_DATA[k]["user_notes"] = txt.get("0.0", "end").strip()
            top.destroy()
            aplicar_filtros_historico()
            
        ctk.CTkButton(top, text="SAVE", command=salvar_nota, fg_color=CORES["primaria"], width=100).pack(pady=10)

    def abrir_gerenciador_sets(k, widget_origem=None):
        from tkinter.colorchooser import askcolor
        root = FRAME_LISTA_HISTORICO.winfo_toplevel()
        top = ctk.CTkToplevel(root)
        top.title("")
        top.geometry("450x400") 
        top.resizable(False, False)
        
        global SETS_DESCRICOES
        if 'SETS_DESCRICOES' not in globals(): SETS_DESCRICOES = {}
        
        if widget_origem:
            try: top.geometry(f"+{widget_origem.winfo_rootx() - 380}+{widget_origem.winfo_rooty()}")
            except: pass
        
        top.transient(root)
        top.focus_force()

        frm_main = ctk.CTkFrame(top, fg_color="transparent")
        frm_main.pack(fill="both", expand=True, padx=10, pady=10)

        def criar_novo_set():
            cor = askcolor(title="New Set Color", parent=top)[1]
            if cor:
                SETS_CRIADOS[cor] = f"Cluster {len(SETS_CRIADOS) + 1}"
                renderizar_lista_sets()

        btn_add = ctk.CTkButton(frm_main, text="", image=ICONES_UI["add"], width=40, height=30,
                                fg_color=CORES["primaria"], hover_color="#555555", command=criar_novo_set)
        btn_add.pack(anchor="e", pady=(0, 10))

        scroll = ctk.CTkScrollableFrame(frm_main, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        def atribuir_set(cor_hex):
            HISTORICO_DATA[k]["set_color"] = cor_hex
            top.destroy()
            aplicar_filtros_historico()

        def remover_do_set():
            if "set_color" in HISTORICO_DATA[k]:
                del HISTORICO_DATA[k]["set_color"]
            top.destroy()
            aplicar_filtros_historico()
            
        def deletar_set_globalmente(cor_alvo):
            count_uso = 0
            for data in HISTORICO_DATA.values():
                if data.get("set_color") == cor_alvo:
                    count_uso += 1
            if count_uso > 0:
                resp = messagebox.askyesno("Delete Set", 
                                           f"This set contains {count_uso} experiment(s).\n"
                                           "Deleting it will remove the label from all of them.\n\n"
                                           "Are you sure?", parent=top)
                if not resp: return

            if cor_alvo in SETS_CRIADOS: del SETS_CRIADOS[cor_alvo]
            if cor_alvo in SETS_DESCRICOES: del SETS_DESCRICOES[cor_alvo]
            for data in HISTORICO_DATA.values():
                if data.get("set_color") == cor_alvo: del data["set_color"]
            
            renderizar_lista_sets()
            aplicar_filtros_historico()

        def atualizar_nome_set(cor_alvo, novo_nome):
            SETS_CRIADOS[cor_alvo] = novo_nome

        # --- FIX: POP-UP AUMENTADO PARA TEXTBOX DE 250 CARACTERES ---
        def abrir_editor_descricao(cor_alvo, btn_ref):
            top_desc = ctk.CTkToplevel(top)
            top_desc.title("Set Description")
            # Pop-up maior para caber as 3-4 linhas de texto
            top_desc.geometry("350x250")
            top_desc.resizable(False, False)
            top_desc.transient(top)
            top_desc.attributes("-topmost", True)
            
            try:
                # Ajusta a posição para não sair da tela com o tamanho maior
                top_desc.geometry(f"+{btn_ref.winfo_rootx() - 150}+{btn_ref.winfo_rooty() - 100}")
            except: pass
            
            top_desc.focus_force()
            
            ctk.CTkLabel(top_desc, text="Description (Max 250 chars):", font=("Roboto", 11, "bold")).pack(pady=(10,5))
            
            # Textbox permite visão multilinhas
            txt_desc = ctk.CTkTextbox(top_desc, width=310, height=100, border_width=1, fg_color="#2b2b2b")
            txt_desc.pack(pady=0)
            txt_desc.insert("0.0", SETS_DESCRICOES.get(cor_alvo, ""))
            
            lbl_contador = ctk.CTkLabel(top_desc, text="", font=("Roboto", 10), text_color="gray")
            lbl_contador.pack(pady=(2, 5))
            
            def atualizar_contador(*args):
                val = txt_desc.get("0.0", "end-1c")
                tamanho = len(val)
                if tamanho > 250:
                    txt_desc.delete("0.0", "end")
                    txt_desc.insert("0.0", val[:250])
                    tamanho = 250
                lbl_contador.configure(text=f"{tamanho}/250")
                
            txt_desc.bind("<KeyRelease>", atualizar_contador)
            atualizar_contador() # Inicializa o contador com o texto existente
            
            def salvar_desc():
                val = txt_desc.get("0.0", "end-1c").strip()
                if val: SETS_DESCRICOES[cor_alvo] = val
                else: SETS_DESCRICOES.pop(cor_alvo, None)
                top_desc.destroy()
                
            ctk.CTkButton(top_desc, text="Save", height=28, command=salvar_desc, fg_color=CORES["primaria"]).pack(pady=(5, 10))
        # -------------------------------------------------------------

        def renderizar_lista_sets():
            for w in scroll.winfo_children(): w.destroy()
            
            if "set_color" in HISTORICO_DATA[k]:
                btn_clear = ctk.CTkButton(scroll, text="Clear Label", fg_color="transparent", 
                                          border_width=1, border_color="gray", text_color="gray",
                                          hover_color="#333333", height=25, command=remover_do_set)
                btn_clear.pack(fill="x", pady=(0, 10))

            if not SETS_CRIADOS:
                ctk.CTkLabel(scroll, text="No sets.", text_color="gray", font=("Arial", 10)).pack(pady=20)
                return

            ctk.CTkLabel(scroll, text="Existing sets:", font=("Roboto", 11, "bold"), anchor="w").pack(fill="x", pady=(5, 5))

            for cor in sorted(list(SETS_CRIADOS.keys())):
                nome_atual = SETS_CRIADOS[cor]
                row_frame = ctk.CTkFrame(scroll, fg_color="transparent")
                row_frame.pack(fill="x", pady=2)
                cor_hover = ajustar_cor_hover(cor)
                
                btn_select = ctk.CTkButton(row_frame, text="", width=25, height=25, corner_radius=4,
                                           fg_color=cor, hover_color=cor_hover,
                                           command=lambda c=cor: atribuir_set(c))
                btn_select.pack(side="left", padx=(0, 5))

                ent_nome = ctk.CTkEntry(row_frame, height=25, border_width=0, fg_color="#2b2b2b")
                ent_nome.insert(0, nome_atual)
                ent_nome.pack(side="left", fill="x", expand=True, padx=(0, 5))
                ent_nome.bind("<KeyRelease>", lambda e, c=cor, ent=ent_nome: atualizar_nome_set(c, ent.get()))

                btn_del = ctk.CTkButton(row_frame, text="", image=ICONES_UI["cheese"], width=25, height=25,
                                        fg_color="transparent", hover_color="#8B0000",
                                        command=lambda c=cor: deletar_set_globalmente(c))
                btn_del.pack(side="right")
                
                btn_desc = ctk.CTkButton(row_frame, text="", image=ICONES_UI["write"], width=25, height=25,
                                        fg_color="transparent", hover_color="#555555",
                                        command=lambda c=cor, b=btn_del: abrir_editor_descricao(c, b))
                btn_desc.pack(side="right", padx=(0, 2))

        renderizar_lista_sets()
    # -------------------------------------------------------

    estado_hover_global = [] 
    
    def limpar_hover_anterior():
        if estado_hover_global:
            saved = estado_hover_global[0]
            f_ant, b_ant, b_eye, b_trash, b_write, b_label, c_bg_ant, c_txt_ant, k_ant, img_lbl_orig = saved
            try:
                if f_ant.winfo_exists(): f_ant.configure(fg_color=c_bg_ant)
                if b_ant.winfo_exists(): b_ant.configure(text_color=c_txt_ant, hover_color=c_bg_ant)
                if b_trash.winfo_exists(): b_trash.configure(image=ICONES_UI["trash"])
                if b_write.winfo_exists(): b_write.configure(image=ICONES_UI["write"])
                if b_eye.winfo_exists():
                    suf = "eye_closed" if k_ant in INSTANCIAS_OCULTAS else "eye"
                    b_eye.configure(image=ICONES_UI[suf])
                if b_label.winfo_exists():
                    b_label.configure(image=img_lbl_orig)
            except: pass
            estado_hover_global.clear()

    for chave in chaves_filtradas:
        dados = HISTORICO_DATA[chave]
        is_selected = (chave == CHAVE_SELECIONADA_ATUAL)
        
        cor_bg_normal = "#6D28D9" if is_selected else "#333333"
        cor_bg_hover = "#FFFFFF"
        cor_txt_normal = "#FFFFFF"
        cor_txt_hover = "#000000"
        
        cor_set = dados.get("set_color")
        if cor_set:
            img_label_normal = gerar_icone_colorido("label2", cor_set)
            img_label_hover = img_label_normal
        else:
            img_label_normal = ICONES_UI["label"]
            img_label_hover = ICONES_UI["label_black"]

        card_frame = ctk.CTkFrame(FRAME_LISTA_HISTORICO, fg_color=cor_bg_normal, corner_radius=6)
        card_frame.pack(fill="x", pady=4, padx=5)
        card_frame.grid_columnconfigure(0, weight=1)
        card_frame.grid_columnconfigure(1, weight=0)

        # --- PROCESSAMENTO DO TEXTO E DO TOOLTIP (MODIFICADO) ---
        raw_agentes = dados.get('meta_agentes', 'N/A')
        if isinstance(raw_agentes, list): lista_full = raw_agentes
        else: lista_full = [x for x in str(raw_agentes).split("-") if x]
        
        lista_curta = [i.split("[")[0].strip() for i in lista_full]
        
        detalhes = []
        for item in lista_full:
            if "[" in item:
                n, p = item.split("[", 1)
                clean_p = p.rstrip(']').replace("Workers: ", "")
                detalhes.append(f"• {n.strip()} [{clean_p}]")
            else: 
                detalhes.append(f"• {item}")
            
        str_ag = ", ".join(lista_curta)
        if len(str_ag) > 25: str_ag = str_ag[:25] + "..."
        
        tem_nota = "📝 Has Notes" if dados.get("user_notes") else ""
        
        tooltip_txt = f"Instance: {dados['meta_nome']}\nDecoder: {dados['meta_decoder']}\n{tem_nota}\n\nConfig:\n" + "\n".join(detalhes)
        
        melhor = min(dados['y']) if dados['y'] else "?"
        
        # A data completa já vem no formato DD/MM/YY HH:MM:SS direto do salvamento
        data_hora_completa = dados.get('meta_hora', '')
        if " " in data_hora_completa:
            data_str, hora_str = data_hora_completa.split(" ")
        else:
            data_str, hora_str = "??/??/??", data_hora_completa

        # O Time limit é o último ponto do eixo X desenhado pelo backend!
        time_limit = f"{dados['x'][-1]:.0f}s" if dados.get('x') else "?s"
        
        # O texto do card agora usa 4 linhas, melhorando a escaneabilidade visual
        texto_card = (
            f"{dados['meta_nome']}\n"
            f"{data_str} {hora_str} | Limit: {time_limit}\n"
            f"Best: {melhor}\n"
            f"[{str_ag}]"
        )
        # =========================================================================
        
        btn_info = ctk.CTkButton(
            card_frame, text=texto_card, font=("Roboto", 11),
            fg_color="transparent", text_color=cor_txt_normal, hover_color=cor_bg_normal, anchor="w", 
            height=70, # Aumentado de 50 para 70 para comportar as 4 linhas com respiro
            command=lambda k=chave: carregar_instancia_historico(k)
        )
        btn_info.grid(row=0, column=0, sticky="nsew", padx=5)
        CTkTooltip(btn_info, text=tooltip_txt, delay=500)
        # --------------------------------------------------------

        frame_botoes = ctk.CTkFrame(card_frame, fg_color="transparent")
        frame_botoes.grid(row=0, column=1, sticky="ns", padx=2, pady=2)
        
        def toggle_eye(k=chave, btn_ref=None):
            is_black = (estado_hover_global and estado_hover_global[0][0] == card_frame)
            suf = "_black" if is_black else ""
            if k in INSTANCIAS_OCULTAS:
                INSTANCIAS_OCULTAS.remove(k)
                novo = ICONES_UI[f"eye{suf}"]
            else:
                INSTANCIAS_OCULTAS.add(k)
                novo = ICONES_UI[f"eye_closed{suf}"]
            if btn_ref: btn_ref.configure(image=novo)
            atualizar_grafico_comparativo()

        suf_eye = "eye_closed" if chave in INSTANCIAS_OCULTAS else "eye"
        btn_eye = ctk.CTkButton(frame_botoes, text="", image=ICONES_UI[suf_eye], width=20, height=20, 
                                fg_color="transparent", hover_color="#555555")
        btn_eye.configure(command=lambda k=chave, b=btn_eye: toggle_eye(k, b))
        btn_eye.pack(side="top", padx=1, pady=(1, 1))

        btn_write = ctk.CTkButton(frame_botoes, text="", image=ICONES_UI["write"], width=20, height=20, 
                                  fg_color="transparent", hover_color="#555555")
        btn_write.configure(command=lambda k=chave, w=btn_write: abrir_editor_notas(k, w))
        btn_write.pack(side="top", padx=1, pady=(1, 1))

        btn_label = ctk.CTkButton(frame_botoes, text="", image=img_label_normal, width=20, height=20, 
                                  fg_color="transparent", hover_color="#555555")
        btn_label.configure(command=lambda k=chave, w=btn_label: abrir_gerenciador_sets(k, w))
        btn_label.pack(side="top", padx=1, pady=(1, 1))

        def delete_item(k=chave, f=card_frame):
            def real_delete():
                if k in HISTORICO_DATA: del HISTORICO_DATA[k]
                if k in INSTANCIAS_OCULTAS: INSTANCIAS_OCULTAS.remove(k)
                if k == CHAVE_SELECIONADA_ATUAL: 
                    if AX_HIST_GANTT: AX_HIST_GANTT.clear(); CANVAS_HIST_GANTT.draw()
                if estado_hover_global and estado_hover_global[0][0] == f: estado_hover_global.clear()
                f.destroy() 
                atualizar_grafico_comparativo()
            if SUPPRESS_DELETE_WARNING: real_delete()
            else: ConfirmDeleteDialog(f.winfo_toplevel(), real_delete)

        btn_trash = ctk.CTkButton(frame_botoes, text="", image=ICONES_UI["trash"], width=20, height=20, 
                                  fg_color="transparent", hover_color="#8B0000")
        btn_trash.configure(command=lambda k=chave, f=card_frame: delete_item(k, f))
        btn_trash.pack(side="top", padx=1, pady=(1, 1))

        def on_enter(e, f=card_frame, b=btn_info, b_eye=btn_eye, b_trash=btn_trash, b_write=btn_write, b_label=btn_label, 
                     c_bg_norm=cor_bg_normal, c_txt_norm=cor_txt_normal, k=chave, 
                     img_lbl_orig=img_label_normal, img_lbl_hov=img_label_hover):
            
            if estado_hover_global and estado_hover_global[0][0] == f: return
            limpar_hover_anterior()
            
            f.configure(fg_color=cor_bg_hover)
            b.configure(text_color=cor_txt_hover, hover_color=cor_bg_hover)
            
            b_trash.configure(image=ICONES_UI["trash_black"])
            b_write.configure(image=ICONES_UI["write_black"])
            b_label.configure(image=img_lbl_hov)
            
            suf = "eye_closed_black" if k in INSTANCIAS_OCULTAS else "eye_black"
            b_eye.configure(image=ICONES_UI[suf])
            
            estado_hover_global.append([f, b, b_eye, b_trash, b_write, b_label, c_bg_norm, c_txt_norm, k, img_lbl_orig])
            
        def on_leave(e, f=card_frame):
            if estado_hover_global and estado_hover_global[0][0] == f:
                limpar_hover_anterior()

        for w in [btn_info, frame_botoes, card_frame, btn_eye, btn_trash, btn_write, btn_label]:
            w.bind("<Enter>", on_enter)
            
        btn_info.bind("<Leave>", on_leave)
        card_frame.bind("<Leave>", on_leave)

def pedir_nome_analise():
    """Valida se existem sets, abre o pop-up no ponteiro do mouse e pede o nome/comentário da análise."""
    from tkinter import messagebox
    
    tem_set = any(dados.get("set_color") for dados in HISTORICO_DATA.values())
    janela_pai = ABA_ANALISE_GLOBAL.winfo_toplevel()
    
    if not tem_set:
        messagebox.showwarning("No Sets Found", 
                               "Please assign at least one set (label) to your experiments in the History tab first.", 
                               parent=janela_pai)
        return

    popup = ctk.CTkToplevel(janela_pai)
    popup.title("Analysis Session")
    
    # --- POP-UP EXPANDIDO ---
    x_mouse = ABA_ANALISE_GLOBAL.winfo_pointerx()
    y_mouse = ABA_ANALISE_GLOBAL.winfo_pointery()
    # Aumentado para 380x320 para dar bastante espaço ao texto
    popup.geometry(f"380x320+{x_mouse - 190}+{y_mouse - 160}")
    popup.resizable(False, False)

    # NOME DA ANÁLISE
    ctk.CTkLabel(popup, text="Enter a name for this session:", font=("Roboto", 13)).pack(pady=(15, 2))
    entrada_nome = ctk.CTkEntry(popup, width=340, border_color=CORES["primaria"])
    entrada_nome.pack(pady=(0, 10))

    # COMENTÁRIO (TEXTBOX PARA VÁRIAS LINHAS)
    ctk.CTkLabel(popup, text="Comment / Hint (optional):", font=("Roboto", 13)).pack(pady=(5, 2))
    # Usando CTkTextbox para permitir que o usuário escreva "muito"
    entrada_comentario = ctk.CTkTextbox(popup, width=340, height=100, border_color=CORES["primaria"], border_width=2)
    entrada_comentario.pack(pady=(0, 15))

    def confirmar(event=None):
        nome = entrada_nome.get().strip()
        # No Textbox, o texto é extraído da linha 1.0 até o fim (removendo a última quebra de linha com -1c)
        comentario = entrada_comentario.get("1.0", "end-1c").strip()
        
        if not nome:
            messagebox.showerror("Error", "A name must be defined to save this analysis session.", parent=popup)
            return
        
        popup.destroy()
        gerar_nova_analise(nome, comentario) 

    def cancelar():
        popup.destroy()

    frm_botoes = ctk.CTkFrame(popup, fg_color="transparent")
    frm_botoes.pack(fill="x", padx=20)
    
    btn_cancel = ctk.CTkButton(frm_botoes, text="Cancel", width=100, fg_color="#555555", hover_color="#333333", command=cancelar)
    btn_cancel.pack(side="left")
    
    btn_ok = ctk.CTkButton(frm_botoes, text="Ok", width=100, command=confirmar, fg_color=CORES["primaria"], hover_color=CORES["destaque"])
    btn_ok.pack(side="right")

    popup.bind("<Return>", confirmar)

    popup.update_idletasks()
    popup.transient(janela_pai) 
    popup.grab_set() 
    popup.attributes("-topmost", True) 
    
    entrada_nome.focus_set()

def gerar_nova_analise(nome_analise, comentario=""):
    """Cria uma aba na Análise com gráfico de convergência, tabelas, boxplots, IC 95% e Histograma com bordas."""
    
    
    global ABA_ANALISE_GLOBAL, FUNCAO_SHOW_TAB_GLOBAL, INSTANCIAS_OCULTAS
    if not ABA_ANALISE_GLOBAL or not FUNCAO_SHOW_TAB_GLOBAL: return

    grupos = {}
    for chave, dados in HISTORICO_DATA.items():
        if chave in INSTANCIAS_OCULTAS:
            continue

        cor = dados.get("set_color")
        if cor:
            if cor not in grupos:
                nome_set = SETS_CRIADOS.get(cor, f"Set {cor}")
                grupos[cor] = {"nome": nome_set, "exp": []}
            grupos[cor]["exp"].append(dados)

    if not grupos: return

    if not hasattr(ABA_ANALISE_GLOBAL, 'is_setup'):
        for widget in ABA_ANALISE_GLOBAL.winfo_children():
            widget.destroy()

        ctk.CTkLabel(ABA_ANALISE_GLOBAL, text="STATISTICAL ANALYSIS", font=("Roboto", 20, "bold"), text_color=CORES["destaque"]).pack(pady=(20, 5), padx=20, anchor="w")

        ABA_ANALISE_GLOBAL.tab_bar_container = ctk.CTkScrollableFrame(ABA_ANALISE_GLOBAL, height=45, orientation="horizontal", fg_color="transparent", scrollbar_button_color="#2D2D35", scrollbar_button_hover_color="#555")
        ABA_ANALISE_GLOBAL.tab_bar_container.pack(fill="x", padx=20, pady=(10, 0))

        ABA_ANALISE_GLOBAL.content_area = ctk.CTkFrame(ABA_ANALISE_GLOBAL, fg_color=CORES["fundo_cartao"], corner_radius=0)
        ABA_ANALISE_GLOBAL.content_area.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        ABA_ANALISE_GLOBAL.tabs_obj = {}
        ABA_ANALISE_GLOBAL.current_active_tab = [None]
        ABA_ANALISE_GLOBAL.placeholder_label = None 
        ABA_ANALISE_GLOBAL.is_setup = True

    # Calcula a largura da tela do usuário dinamicamente 
    largura_tela_pixels = ABA_ANALISE_GLOBAL.winfo_width()
    if largura_tela_pixels < 100: 
        largura_tela_pixels = 1200 # Medida de segurança caso a tela não tenha carregado
        
    # Desconta as margens laterais e converte para polegadas (DPI padrão do matplotlib é 100)
    largura_dinamica = (largura_tela_pixels - 150) / 100.0

    tab_bar = ABA_ANALISE_GLOBAL.tab_bar_container
    content_area = ABA_ANALISE_GLOBAL.content_area
    tabs_obj = ABA_ANALISE_GLOBAL.tabs_obj
    active_tab = ABA_ANALISE_GLOBAL.current_active_tab

    if getattr(ABA_ANALISE_GLOBAL, 'placeholder_label', None):
        ABA_ANALISE_GLOBAL.placeholder_label.destroy()
        ABA_ANALISE_GLOBAL.placeholder_label = None

    base_nome = nome_analise
    counter = 1
    while nome_analise in tabs_obj:
        nome_analise = f"{base_nome} ({counter})"
        counter += 1

    def selecionar_aba(nome_aba):
        antiga = active_tab[0]
        if antiga and antiga in tabs_obj and antiga != nome_aba:
            tabs_obj[antiga]["btn_frame"].configure(fg_color="#2D2D35")
            tabs_obj[antiga]["content"].pack_forget()

        active_tab[0] = nome_aba
        if nome_aba in tabs_obj:
            tabs_obj[nome_aba]["btn_frame"].configure(fg_color=CORES["primaria"])
            tabs_obj[nome_aba]["content"].pack(fill="both", expand=True)

    def fechar_aba(nome_aba):
        tabs_obj[nome_aba]["content"].pack_forget()
        tabs_obj[nome_aba]["btn_frame"].pack_forget()
        
        tabs_obj[nome_aba]["content"].destroy()
        tabs_obj[nome_aba]["btn_frame"].destroy()
        del tabs_obj[nome_aba]

        if active_tab[0] == nome_aba:
            if tabs_obj:
                primeira_disp = list(tabs_obj.keys())[0]
                selecionar_aba(primeira_disp)
            else:
                active_tab[0] = None
                lbl = ctk.CTkLabel(content_area, text="All analysis tabs closed. Return to History to create a new one.", text_color="gray")
                lbl.pack(pady=50)
                ABA_ANALISE_GLOBAL.placeholder_label = lbl

    tab_btn = ctk.CTkFrame(tab_bar, fg_color="#2D2D35", corner_radius=6, height=35)
    tab_btn.pack(side="left", padx=(0, 5))
    tab_btn.pack_propagate(False)

    largura_texto = len(nome_analise) * 8 + 50
    tab_btn.configure(width=max(130, largura_texto))

    lbl_tab = ctk.CTkLabel(tab_btn, text=nome_analise, font=("Roboto", 11, "bold"), text_color="white")
    lbl_tab.pack(side="left", padx=(10, 5), pady=5)

    btn_close = ctk.CTkButton(tab_btn, text="×", font=("Arial", 16, "bold"), width=20, height=20,
                              fg_color="transparent", hover_color="#C0392B", text_color="#AAAAAA",
                              command=lambda n=nome_analise: fechar_aba(n))
    btn_close.pack(side="right", padx=(5, 5))

    tab_btn.bind("<Button-1>", lambda e, n=nome_analise: selecionar_aba(n))
    lbl_tab.bind("<Button-1>", lambda e, n=nome_analise: selecionar_aba(n))

    def on_enter_hover(e, f=tab_btn, n=nome_analise):
        if active_tab[0] != n: f.configure(fg_color="#3D3D45")
    def on_leave_hover(e, f=tab_btn, n=nome_analise):
        if active_tab[0] != n: f.configure(fg_color="#2D2D35")

    tab_btn.bind("<Enter>", on_enter_hover, add="+")
    tab_btn.bind("<Leave>", on_leave_hover, add="+")
    lbl_tab.bind("<Enter>", on_enter_hover, add="+")
    lbl_tab.bind("<Leave>", on_leave_hover, add="+")

    def criar_tooltip(widget, texto):
        if not texto: return
        tooltip_window = [None]
        timer_id = [None]

        def mostrar_tooltip():
            if tooltip_window[0] is not None: return
            x = widget.winfo_rootx() + 20
            y = widget.winfo_rooty() + widget.winfo_height() + 5
            tw = tk.Toplevel(widget)
            tw.wm_overrideredirect(True)
            tw.wm_geometry(f"+{x}+{y}")
            
            lbl = tk.Label(tw, text=texto, background="#1E1E21", foreground="#DDDDDD",
                           relief="solid", borderwidth=1, highlightbackground="#444", 
                           font=("Roboto", 10), padx=10, pady=8,
                           wraplength=350, justify="left")
            lbl.pack()
            tw.attributes("-topmost", True)
            tooltip_window[0] = tw

        def on_enter(event):
            if timer_id[0]: widget.after_cancel(timer_id[0])
            timer_id[0] = widget.after(500, mostrar_tooltip)

        def on_leave(event):
            if timer_id[0]: 
                widget.after_cancel(timer_id[0])
                timer_id[0] = None
            if tooltip_window[0]:
                tooltip_window[0].destroy()
                tooltip_window[0] = None

        widget.bind("<Enter>", on_enter, add="+")
        widget.bind("<Leave>", on_leave, add="+")

    criar_tooltip(tab_btn, comentario)
    criar_tooltip(lbl_tab, comentario)

    def criar_tooltip_treeview(tree, dict_notas):
        if not dict_notas: return
        tooltip_window = [None]
        current_item = [None]
        timer_id = [None]

        def esconder_tooltip(event=None):
            if tooltip_window[0]:
                tooltip_window[0].destroy()
                tooltip_window[0] = None
            if timer_id[0]:
                tree.after_cancel(timer_id[0])
                timer_id[0] = None
            current_item[0] = None

        def mostrar_tooltip(item, x, y):
            esconder_tooltip() 
            texto = dict_notas.get(item)
            if not texto: return
            
            tw = tk.Toplevel(tree)
            tw.wm_overrideredirect(True)
            tw.wm_geometry(f"+{x+15}+{y+15}")
            
            lbl = tk.Label(tw, text=f"Notes:\n{texto}", background="#1E1E21", foreground="#DDDDDD",
                           relief="solid", borderwidth=1, highlightbackground="#444", 
                           font=("Roboto", 10), padx=10, pady=8,
                           wraplength=350, justify="left")
            lbl.pack()
            tw.attributes("-topmost", True)
            tooltip_window[0] = tw

        def on_motion(event):
            item = tree.identify_row(event.y)
            if item != current_item[0]:
                esconder_tooltip()
                current_item[0] = item
                if item and item in dict_notas:
                    timer_id[0] = tree.after(500, lambda it=item, rx=event.x_root, ry=event.y_root: mostrar_tooltip(it, rx, ry))

        tree.bind("<Motion>", on_motion)
        tree.bind("<Leave>", esconder_tooltip)
        tree.bind("<ButtonPress>", esconder_tooltip) 
        tree.bind("<MouseWheel>", esconder_tooltip)  

    frame_tab_content = ctk.CTkScrollableFrame(content_area, fg_color="transparent")
    
    # Lista global interna para armazenar TODAS as figuras geradas
    figuras_para_exportar = []
    lista_canvases = []
    colunas = ("INSTANCE", "MACHINES", "JOBS", "SETUP", "POLICY", "MAKESPAN", "RUNTIME", "TIME TO BEST", "PARAMETERS", "AGENTS CONFIGS")
    estatisticas_por_grupo = {}

    # ================== BOTÃO DE EXPORTAÇÃO COMPLETA ==================
    def acao_exportar_tudo():
       

        try:
            import pandas as pd
            from fpdf import FPDF
        except ImportError:
            tk.messagebox.showerror(
                "Dependências Ausentes",
                "Para gerar os relatórios, instale as dependências:\npip install pandas tabulate fpdf2",
                parent=ABA_ANALISE_GLOBAL
            )
            return

        caminho_base = filedialog.asksaveasfilename(
            parent=ABA_ANALISE_GLOBAL,
            title="Choose Base Name for Reports",
            initialfile=f"Report_{nome_analise.replace(' ', '_')}",
            filetypes=[("All Files", "*.*")]
        )

        if not caminho_base: return
        caminho_base, _ = os.path.splitext(caminho_base)

        try:
            agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            titulo_principal = f"Statistical Report: {nome_analise} - {agora}"
            titulo_tex_str = f"Statistical Report: {nome_analise.replace('_', r'\_')} - {agora}"

            dict_descricoes = globals().get('SETS_DESCRICOES', {})

            # 1. Separar DataFrames por Grupo e resgatar as Descrições
            dfs_por_grupo = {}
            for cor_set in sorted(grupos.keys()):
                nome_set = grupos[cor_set]["nome"]
                desc_set = dict_descricoes.get(cor_set, "").strip()
                linhas_do_grupo = []
                
                for exp in grupos[cor_set]["exp"]:
                    inst = exp.get("meta_nome", "-")
                    policy = exp.get("meta_decoder", "-")
                    mksp = min(exp['y']) if exp.get('y') else "-"
                    
                    if exp.get('x') and exp.get('y'):
                        runtime = f"{exp['x'][-1]:.2f}"
                        idx_best = exp['y'].index(min(exp['y']))
                        time_to_best = f"{exp['x'][idx_best]:.2f}"
                    else:
                        runtime, time_to_best = "-", "-"

                    gantt = exp.get("gantt")
                    machines, jobs = "-", "-"
                    if gantt:
                        if "M" in gantt: machines = str(len(gantt["M"]))
                        if "C" in gantt: jobs = str(len(set(k[1] for k in gantt["C"].keys())))

                    setup_rng = str(exp.get("meta_setup_range", "N/A"))
                    raw_ag = exp.get('meta_agentes', [])
                    if isinstance(raw_ag, str): raw_ag = [x.strip() for x in raw_ag.split("-") if x.strip()]
                    param_short = ", ".join([a.split("[")[0].strip() for a in raw_ag]).replace('%', '')
                    param_long = " | ".join(raw_ag).replace('%', '')

                    linhas_do_grupo.append([inst, machines, jobs, setup_rng, policy, str(mksp), runtime, time_to_best, param_short, param_long])
                       
                stats_ui = estatisticas_por_grupo[cor_set]
                
                for m in ["Min", "Mean", "Median", "P95", "Max", "Stdev", "Variance", "Count", "CV (%)"]:
                    linhas_do_grupo.append([
                        m, 
                        stats_ui["mac"][m], 
                        stats_ui["job"][m], 
                        "-", "-", 
                        stats_ui["mksp"][m], 
                        stats_ui["rt"][m], 
                        stats_ui["ttb"][m], 
                        "-", "-"
                    ])

                dfs_por_grupo[nome_set] = {"cor": cor_set, "desc": desc_set, "df": pd.DataFrame(linhas_do_grupo, columns=colunas)}

            # --- 2. CÁLCULO DAS 3 MATRIZES ESTATÍSTICAS (MOVIDO PARA CIMA!) ---
            matrizes_exportacao = []
            try:
                import scipy.stats as stats
                import scikit_posthocs as sp
                import numpy as np

                def obter_ast(p_val):
                    if p_val < 0.001: return f"{p_val:.4f} ***"
                    elif p_val < 0.01: return f"{p_val:.4f} **"
                    elif p_val < 0.05: return f"{p_val:.4f} *"
                    else: return f"{p_val:.4f} ns"

                for metrica_loop in ["Makespan", "Time to Best", "Runtime"]:
                    dados_pareados = {}
                    nomes_grupos = []
                    
                    for cor_set in sorted(grupos.keys()):
                        nome_g = grupos[cor_set]["nome"]
                        if nome_g in nomes_grupos: nome_g = f"{nome_g} ({cor_set})"
                        nomes_grupos.append(nome_g)
                        
                        dict_inst = {}
                        contagem_nomes = {} 
                        for exp in grupos[cor_set]["exp"]:
                            nome_bruto = str(exp.get("meta_nome", "Inst")).strip()
                            inst_base = os.path.basename(nome_bruto)
                            if not inst_base or inst_base == "-": inst_base = "Inst"
                            
                            contagem_nomes[inst_base] = contagem_nomes.get(inst_base, 0) + 1
                            inst_id = f"{inst_base}_run{contagem_nomes[inst_base]}"
                            
                            val = None
                            if metrica_loop == "Makespan" and exp.get('y'): val = min(exp['y'])
                            elif metrica_loop == "Time to Best" and exp.get('x') and exp.get('y'): val = exp['x'][exp['y'].index(min(exp['y']))]
                            elif metrica_loop == "Runtime" and exp.get('x'): val = exp['x'][-1]
                            
                            if val is not None: dict_inst[inst_id] = val
                        dados_pareados[nome_g] = dict_inst

                    if len(nomes_grupos) < 2: continue

                    lista_conjuntos = [set(d.keys()) for d in dados_pareados.values()]
                    if not lista_conjuntos: continue
                    insts_comuns = set.intersection(*lista_conjuntos)
                    
                    if len(insts_comuns) < 3: continue

                    insts_comuns = sorted(list(insts_comuns))
                    matriz_dados = np.array([[dados_pareados[g][inst] for inst in insts_comuns] for g in nomes_grupos])

                    if len(nomes_grupos) > 2:
                        _, p_friedman = stats.friedmanchisquare(*matriz_dados)
                        texto_friedman = f"Friedman Test p-value: {obter_ast(p_friedman)}"
                    else:
                        texto_friedman = "Friedman Test: N/A (Only 2 groups)"

                    n_grupos = len(nomes_grupos)
                    if n_grupos > 2:
                        try: matriz_nemenyi = sp.posthoc_nemenyi(matriz_dados.T)
                        except: matriz_nemenyi = None
                    else: matriz_nemenyi = None

                    grade_exportacao = []
                    for i in range(n_grupos):
                        linha_export = []
                        for j in range(n_grupos):
                            texto_celula = "-"
                            tipo_celula = "diag" 
                            if i < j: 
                                tipo_celula = "wilcoxon"
                                try:
                                    _, p_val = stats.wilcoxon(matriz_dados[i], matriz_dados[j], zero_method='zsplit')
                                    texto_celula = obter_ast(p_val)
                                except ValueError: texto_celula = "Tie"
                            elif i > j: 
                                tipo_celula = "nemenyi"
                                if matriz_nemenyi is not None:
                                    p_val = matriz_nemenyi.iloc[i, j]
                                    texto_celula = obter_ast(p_val)
                                else: texto_celula = "N/A"
                            linha_export.append({"texto": texto_celula, "tipo": tipo_celula})
                        grade_exportacao.append(linha_export)

                    matrizes_exportacao.append({
                        "metrica": metrica_loop,
                        "nomes": nomes_grupos,
                        "texto_friedman": texto_friedman,
                        "grade": grade_exportacao
                    })
            except ImportError:
                pass

            # 3. Gerar Markdown
            with open(caminho_base + ".md", "w", encoding="utf-8") as f:
                f.write(f"# {titulo_principal}\n\n")
                
                # --- Tabelas dos Grupos ---
                for nome_set, data in dfs_por_grupo.items():
                    titulo_md = f"Group: {nome_set}" + (f" - *{data['desc']}*" if data['desc'] else "")
                    f.write(f"### {titulo_md}\n")
                    f.write(data["df"].to_markdown(index=False) + "\n\n")
                
                # --- Matrizes Estatísticas em Markdown ---
                if matrizes_exportacao:
                    f.write("## Statistical Significance Matrices\n\n")
                    
                    for dados_stats in matrizes_exportacao:
                        f.write(f"### {dados_stats['metrica']}\n")
                        friedman_esc = dados_stats['texto_friedman'].replace('*', r'\*')
                        f.write(f"__{friedman_esc}__\n\n")
                        
                        # Monta o cabeçalho da tabela Markdown
                        cabecalho = "| | " + " | ".join(dados_stats['nomes']) + " |"
                        separador = "|---|" + "|".join(["---" for _ in dados_stats['nomes']]) + "|"
                        
                        f.write(cabecalho + "\n")
                        f.write(separador + "\n")
                        
                        # Monta as linhas da matriz
                        for i, linha in enumerate(dados_stats['grade']):
                            linha_md = f"| **{dados_stats['nomes'][i]}** | "
                            # Escapar os asteriscos das células
                            valores_celulas = [c['texto'].replace('*', r'\*') for c in linha]
                            linha_md += " | ".join(valores_celulas) + " |"
                            f.write(linha_md + "\n")
                        
                        # Legenda da matriz
                        f.write("\n_Upper Triangle: Wilcoxon Signed-Rank Test | Lower Triangle: Nemenyi Post-hoc Test_\n")
                        f.write("_\\*\\*\\* p<0.001, \\*\\* p<0.01, \\* p<0.05, ns: not significant_\n\n")
            # 4. Gerar LaTeX COMPLETO
            latex_str = "\\documentclass[10pt,a4paper]{article}\n"
            latex_str += "\\usepackage[utf8]{inputenc}\n"
            latex_str += "\\usepackage{geometry}\n"
            latex_str += "\\geometry{margin=1.5cm, landscape}\n" 
            latex_str += "\\usepackage{booktabs}\n"
            latex_str += "\\usepackage{longtable}\n"
            latex_str += "\\usepackage{array}\n"
            latex_str += "\\begin{document}\n\n"
            latex_str += f"\\section*{{{titulo_tex_str}}}\n\n"
            latex_str += "\\scriptsize\n"
            latex_str += "\\setlength{\\tabcolsep}{3pt}\n" 
            
            col_fmt = ("|>{\\centering\\arraybackslash}p{2.5cm}"   
                       "|>{\\centering\\arraybackslash}p{1.2cm}"   
                       "|>{\\centering\\arraybackslash}p{0.8cm}"   
                       "|>{\\centering\\arraybackslash}p{1.2cm}"   
                       "|>{\\centering\\arraybackslash}p{1.0cm}"   
                       "|>{\\centering\\arraybackslash}p{1.5cm}"   
                       "|>{\\centering\\arraybackslash}p{1.5cm}"   
                       "|>{\\centering\\arraybackslash}p{1.5cm}"   
                       "|>{\\centering\\arraybackslash}p{1.8cm}"   
                       "|>{\\raggedright\\arraybackslash}p{9.0cm}|")
            
            for nome_set, data in dfs_por_grupo.items():
                desc_tex = data['desc'].replace('%', r'\%').replace('_', r'\_').replace('&', r'\&').replace('#', r'\#')
                titulo_tex = f"Grupo: {nome_set}" + (f" -- \\textit{{{desc_tex}}}" if desc_tex else "")
                
                latex_str += f"\\subsection*{{{titulo_tex}}}\n"
                
                tex_raw = data["df"].to_latex(index=False, escape=True, longtable=True, column_format=col_fmt)
                tex_raw = tex_raw.replace("\\toprule", "\\hline").replace("\\midrule", "\\hline").replace("\\bottomrule", "\\hline")
                linhas_tex = tex_raw.split("\\\\\n")
                tex_com_bordas = "\\\\\n\\hline\n".join(linhas_tex)
                
                latex_str += tex_com_bordas
                latex_str += "\n\\vspace{1cm}\n"
            
            # --- ADIÇÃO DAS 3 MATRIZES NO LATEX ---
            if matrizes_exportacao:
                latex_str += "\\newpage\n"
                latex_str += "\\section*{Statistical Significance Matrices}\n\n"
                
                for dados_stats in matrizes_exportacao:
                    latex_str += f"\\subsection*{{{dados_stats['metrica']}}}\n"
                    latex_str += f"\\noindent\\textbf{{{dados_stats['texto_friedman']}}}\\\\[0.3cm]\n"
                    
                    n_cols = len(dados_stats['nomes'])
                    col_format = "l" + "c" * n_cols
                    
                    latex_str += f"\\begin{{center}}\n"
                    latex_str += f"\\begin{{tabular}}{{{col_format}}}\n"
                    latex_str += "\\toprule\n"
                    
                    # Nomes escapados para evitar erros com underscore_
                    nomes_escapados = [n.replace('_', r'\_').replace('%', r'\%') for n in dados_stats['nomes']]
                    latex_str += " & " + " & ".join(nomes_escapados) + " \\\\\n"
                    latex_str += "\\midrule\n"
                    
                    for i, linha in enumerate(dados_stats['grade']):
                        nome_linha = nomes_escapados[i]
                        # Substitui > e < pelo formato matemático do LaTeX para evitar erros
                        valores_celulas = [c['texto'].replace('<', '$<$').replace('>', '$>$') for c in linha]
                        latex_str += f"{nome_linha} & " + " & ".join(valores_celulas) + " \\\\\n"
                        
                    latex_str += "\\bottomrule\n"
                    latex_str += "\\end{tabular}\n"
                    latex_str += "\\end{center}\n"
                    
                    latex_str += "\\noindent\\scriptsize{Upper Triangle: Wilcoxon Signed-Rank Test $\\vert$ Lower Triangle: Nemenyi Post-hoc Test} \\\\\n"
                    latex_str += "\\noindent\\scriptsize{*** $p<0.001$, ** $p<0.01$, * $p<0.05$, ns: not significant}\n"
                    latex_str += "\\vspace{1cm}\n\n"

            latex_str += "\\normalsize\n"
            latex_str += "\\end{document}"
            with open(caminho_base + ".tex", "w", encoding="utf-8") as f:
                f.write(latex_str)
           
            # 5. Processar Imagens
            import matplotlib as mpl
            mpl.rcParams['svg.fonttype'] = 'path'
            
            imagens_html = ""
            imagens_temporarias_pdf = []
            
            for fig in figuras_para_exportar:
                if fig:
                    buf_svg = io.BytesIO()
                    fig.savefig(buf_svg, format='svg', bbox_inches='tight', facecolor=fig.get_facecolor())
                    buf_svg.seek(0)
                    svg_texto = buf_svg.read().decode('utf-8')
                    svg_b64 = base64.b64encode(svg_texto.encode('utf-8')).decode('utf-8')
                    imagens_html += f'<div style="text-align: center; margin-top: 40px;"><img src="data:image/svg+xml;base64,{svg_b64}" style="max-width: 100%; border-radius: 8px;"/></div>'
                    
                    svg_limpo = re.sub(r'<metadata>.*?</metadata>', '', svg_texto, flags=re.DOTALL)
                    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".svg", mode="w", encoding="utf-8")
                    tmp.write(svg_limpo)
                    tmp.close()
                    imagens_temporarias_pdf.append(tmp.name)

            # 6. Gerar HTML Espaçado e Colorido
            estilo = "<style> body { font-family: Helvetica, sans-serif; margin: 30px; background-color: #f4f4f9;} table { border-collapse: collapse; width: 100%; font-size: 12px; background-color: white; margin-bottom: 40px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);} th, td { border: 1px solid #ddd; padding: 10px; text-align: center; } th { background-color: #2D2D35; color: white; } </style>"
            
            html_tables_content = ""
            for nome_set, data in dfs_por_grupo.items():
                cor = data["cor"]
                df = data["df"]
                
                titulo_html = f"Group: {nome_set}" + (f" <span style='font-size: 0.85em; font-weight: normal; font-style: italic;'>- {data['desc']}</span>" if data['desc'] else "")
                html_tables_content += f'<h3 style="color: {cor}; border-bottom: 2px solid {cor}; padding-bottom: 5px; margin-top: 30px;">{titulo_html}</h3>\n'
                
                r, g, b = int(cor[1:3], 16), int(cor[3:5], 16), int(cor[5:7], 16)
                bg_color = f"rgba({r},{g},{b},0.1)"
                
                html_tb = f"<table><thead><tr>" + "".join([f"<th>{c}</th>" for c in colunas]) + "</tr></thead><tbody>"
                for _, row in df.iterrows():
                    html_tb += f"<tr style='background-color: {bg_color};'>" + "".join([f"<td>{v}</td>" for v in row]) + "</tr>"
                html_tb += "</tbody></table>\n"
                html_tables_content += html_tb

            # --- LAÇO PARA IMPRIMIR AS 3 MATRIZES NO HTML ---
            html_todas_matrizes = ""
            for dados_stats in matrizes_exportacao:
                html_matriz = f"<div style='margin-top: 50px; page-break-before: always;'>"
                html_matriz += f"<h3 style='color: #2c3e50; border-bottom: 2px solid #2c3e50; padding-bottom: 5px;'>Statistical Significance Matrix ({dados_stats['metrica']})</h3>"
                html_matriz += f"<p style='font-size: 14px; font-weight: bold; color: #27ae60;'>{dados_stats['texto_friedman']}</p>"
                
                html_matriz += "<table><thead><tr><th style='background-color: #f8f9fa; border: 1px solid #dee2e6;'></th>"
                for nome in dados_stats['nomes']:
                    html_matriz += f"<th style='background-color: #e9ecef; color: #333; border: 1px solid #dee2e6;'>{nome}</th>"
                html_matriz += "</tr></thead><tbody>"
                
                for i, linha in enumerate(dados_stats['grade']):
                    html_matriz += f"<tr><td style='background-color: #e9ecef; color: #333; font-weight: bold; border: 1px solid #dee2e6;'>{dados_stats['nomes'][i]}</td>"
                    for celula in linha:
                        bg_color = "#ffffff"
                        if celula['tipo'] == "diag": bg_color = "#f8f9fa" 
                        elif celula['tipo'] == "wilcoxon": bg_color = "#e3f2fd" 
                        elif celula['tipo'] == "nemenyi": bg_color = "#fff9c4" 
                        
                        html_matriz += f"<td style='background-color: {bg_color}; color: #212529; border: 1px solid #dee2e6;'>{celula['texto']}</td>"
                    html_matriz += "</tr>"
                html_matriz += "</tbody></table>"
                
                html_matriz += "<p style='font-size: 11px; color: #6c757d;'><b>Upper Triangle (Blue):</b> Wilcoxon Signed-Rank Test | <b>Lower Triangle (Yellow):</b> Nemenyi Post-hoc Test<br>*** p<0.001 &nbsp; ** p<0.01 &nbsp; * p<0.05 &nbsp; ns: not significant</p>"
                html_matriz += "</div>"
                
                html_todas_matrizes += html_matriz
                
            html_content = f"<!DOCTYPE html><html><head><meta charset='utf-8'>{estilo}</head><body><h2>{titulo_principal}</h2>{html_tables_content}{html_todas_matrizes}{imagens_html}</body></html>"

            with open(caminho_base + ".html", "w", encoding="utf-8") as f: 
                f.write(html_content)

            # 7. Gerar PDF Acadêmico
            pdf = FPDF(orientation="L", format="A4")
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.add_page()
            
            pdf.set_font("helvetica", "B", 16)
            pdf.cell(0, 10, titulo_principal, new_x="LMARGIN", new_y="NEXT", align="C")
            pdf.ln(5)

            pesos_colunas = (10, 6, 6, 6, 8, 8, 8, 10, 12, 30)

            for nome_set, data in dfs_por_grupo.items():
                df = data["df"]
                cor_hex = data["cor"]
                
                r, g, b = int(cor_hex[1:3], 16), int(cor_hex[3:5], 16), int(cor_hex[5:7], 16)
                r_fill = int((r * 0.15) + (255 * 0.85))
                g_fill = int((g * 0.15) + (255 * 0.85))
                b_fill = int((b * 0.15) + (255 * 0.85))

                titulo_pdf = f"Group: {nome_set}" + (f" - {data['desc']}" if data['desc'] else "")

                pdf.set_font("helvetica", "B", 12)
                pdf.set_text_color(r, g, b)
                pdf.cell(0, 10, titulo_pdf, new_x="LMARGIN", new_y="NEXT", align="L")
                
                pdf.set_text_color(0, 0, 0)
                pdf.set_font("helvetica", size=7) 
                pdf.set_draw_color(150, 150, 150)
                
                with pdf.table(text_align="CENTER", borders_layout="ALL", col_widths=pesos_colunas, cell_fill_color=(r_fill, g_fill, b_fill), cell_fill_mode="ALL") as table:
                    header_row = table.row()
                    for col in colunas:
                        header_row.cell(col)
                    
                    for _, pd_row in df.iterrows():
                        data_row = table.row()
                        for val in pd_row:
                            data_row.cell(str(val))
                pdf.ln(10)

            # --- LAÇO PARA IMPRIMIR AS 3 MATRIZES NO PDF ---
            for dados_stats in matrizes_exportacao:
                pdf.add_page()
                pdf.set_font("helvetica", "B", 14)
                pdf.set_text_color(0, 0, 0)
                pdf.cell(0, 10, f"Statistical Significance Matrix ({dados_stats['metrica']})", new_x="LMARGIN", new_y="NEXT", align="L")
                
                pdf.set_font("helvetica", "BI", 11)
                pdf.set_text_color(0, 0, 0) # Cor preta para o Friedman
                pdf.cell(0, 8, dados_stats['texto_friedman'], new_x="LMARGIN", new_y="NEXT", align="L")
                pdf.ln(5)

                pdf.set_font("helvetica", "", 10)
                pdf.set_text_color(0, 0, 0)
                
                with pdf.table(text_align="CENTER", borders_layout="ALL") as table:
                    header_row = table.row()
                    header_row.cell("") 
                    for nome in dados_stats["nomes"]:
                        header_row.cell(nome)
                        
                    for i, row_data in enumerate(dados_stats["grade"]):
                        pdf_row = table.row()
                        pdf_row.cell(dados_stats["nomes"][i]) 
                        for celula in row_data:
                            pdf_row.cell(celula["texto"])
                            
                pdf.ln(5)
                pdf.set_font("helvetica", "I", 8)
                pdf.set_text_color(100, 100, 100)
                pdf.cell(0, 5, "Upper Triangle: Wilcoxon Signed-Rank Test  |  Lower Triangle: Nemenyi Post-hoc Test", new_x="LMARGIN", new_y="NEXT")
                pdf.cell(0, 5, "*** p<0.001   ** p<0.01   * p<0.05   ns: not significant", new_x="LMARGIN", new_y="NEXT")

            for img_path in imagens_temporarias_pdf:
                pdf.add_page()
                pdf.image(img_path, x="C", y=10, w=285, h=190, keep_aspect_ratio=True)
                os.remove(img_path) 

            pdf.output(caminho_base + ".pdf")
            tk.messagebox.showinfo("Export Successful", f"All formats were successfully created at:\n\n{caminho_base}", parent=ABA_ANALISE_GLOBAL)

        except Exception as e:
            tk.messagebox.showerror("Export Error", f"An error occurred during export:\n{str(e)}", parent=ABA_ANALISE_GLOBAL)

    # AÇÕES DO TOPO: CHECKBOX DE TEMA E BOTÃO DE EXPORTAÇÃO
    frame_actions = ctk.CTkFrame(frame_tab_content, fg_color="transparent")
    frame_actions.pack(fill="x", pady=(10, 0), padx=10)

    # --- LÓGICA DO TEMA ACADÊMICO (BRANCO) ---
    var_light_theme = ctk.BooleanVar(value=False)
    
    def toggle_theme():
        from matplotlib.colors import to_rgba
        is_light = var_light_theme.get()
        
        # Paleta de Cores Dinâmica
        bg_c = "#FFFFFF" if is_light else "#1E1E21"
        title_c = "#111111" if is_light else "#FFFFFF"
        text_c = "#333333" if is_light else "#DDDDDD"
        spine_c = "#CCCCCC" if is_light else "#444444"
        grid_c = "#EAEAEA" if is_light else "#333333"

        # Mapas de substituição
        map_title = {to_rgba("#FFFFFF"): title_c, to_rgba("#111111"): title_c}
        map_text = {to_rgba("#DDDDDD"): text_c, to_rgba("#333333"): text_c}
        
        for fig in figuras_para_exportar:
            if not fig: continue
            fig.set_facecolor(bg_c)
            for ax in fig.axes:
                ax.set_facecolor(bg_c)
                
                ax.title.set_color(title_c)
                ax.xaxis.label.set_color(text_c)
                ax.yaxis.label.set_color(text_c)
                ax.tick_params(colors=text_c)
                
                for spine in ax.spines.values(): spine.set_color(spine_c)
                for gl in ax.get_xgridlines() + ax.get_ygridlines(): gl.set_color(grid_c)
                    
                leg = ax.get_legend()
                if leg:
                    for text in leg.get_texts(): text.set_color(text_c)
                        
                # Atualiza linhas (medianas, bigodes e outliers)
                for line in ax.lines:
                    c = line.get_color()
                    try:
                        if to_rgba(c) in map_title: line.set_color(map_title[to_rgba(c)])
                        elif to_rgba(c) in map_text: line.set_color(map_text[to_rgba(c)])
                    except: pass
                    
                    mfc = line.get_markerfacecolor()
                    try:
                        if to_rgba(mfc) in map_title: line.set_markerfacecolor(map_title[to_rgba(mfc)])
                    except: pass
                        
                    mec = line.get_markeredgecolor()
                    try:
                        if to_rgba(mec) in map_title: line.set_markeredgecolor(map_title[to_rgba(mec)])
                    except: pass

                # Atualiza caixas do boxplot e bordas do histograma
                for patch in ax.patches:
                    ec = patch.get_edgecolor()
                    try:
                        if to_rgba(ec) in map_title: patch.set_edgecolor(map_title[to_rgba(ec)])
                        elif to_rgba(ec) in map_text: patch.set_edgecolor(map_text[to_rgba(ec)])
                    except: pass
                    
                # Atualiza bordas do Stripplot
                for collection in ax.collections:
                    ecs = collection.get_edgecolors()
                    if len(ecs) > 0:
                        ec = ecs[0]
                        try:
                            if to_rgba(ec) in map_title: collection.set_edgecolor(map_title[to_rgba(ec)])
                            elif to_rgba(ec) in map_text: collection.set_edgecolor(map_text[to_rgba(ec)])
                        except: pass

        # Manda as telas piscarem e atualizarem na hora!
        for canvas in lista_canvases:
            canvas.draw_idle()
        
        metrica_atual = combo_metric_stats.get()
        atualizar_matriz_estatistica(metrica_atual)

    # --- RENDERIZAÇÃO DA CHECKBOX ---
    chk_theme = ctk.CTkCheckBox(
        frame_actions, 
        text="Light Paper Theme", 
        font=("Roboto", 12, "bold"), 
        variable=var_light_theme, 
        command=toggle_theme,
        fg_color="#0284c7", hover_color="#0ea5e9"
    )
    chk_theme.pack(side="left", padx=(10, 0))
    
    try: adicionar_tooltip(chk_theme, "Enable this to switch the graphs to a white background, making them suitable for academic papers.")
    except: pass

    # --- LÓGICA DE CARREGAMENTO DA IMAGEM ---
    from PIL import Image
    
    icon_export = None
    try:
        caminho_script = os.path.dirname(os.path.abspath(__file__))
        caminho_assets = os.path.join(os.path.dirname(caminho_script), "assets", "export.png")
        pil_img = Image.open(caminho_assets)
        icon_export = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(24, 24))
    except Exception as e:
        print(f"Aviso: Não foi possível carregar a imagem. Erro: {e}")

    # --- RENDERIZAÇÃO DO BOTÃO EXPORT ---
    btn_export = ctk.CTkButton(
        frame_actions, text=" Export", image=icon_export, compound="left", font=("Roboto", 12, "bold"), 
        fg_color="#0284c7", hover_color="#0ea5e9", width=90, command=acao_exportar_tudo
    )
    btn_export.pack(side="right")
    
    def adicionar_tooltip(widget, texto):
        tooltip_window = [None]
        timer_id = [None]

        def mostrar_tooltip():
            if tooltip_window[0] is not None: return
            
            # Recua 200 pixeis para a esquerda, garantindo que cabe no monitor
            x = widget.winfo_rootx() - 200 
            y = widget.winfo_rooty() + widget.winfo_height() + 5
            
            tw = tk.Toplevel(widget)
            tw.wm_overrideredirect(True)
            tw.wm_geometry(f"+{x}+{y}")
            
            # --- FIX: wraplength=200 força o texto a quebrar de linha! ---
            lbl = tk.Label(tw, text=texto, background="#1E1E21", foreground="#DDDDDD",
                           relief="solid", borderwidth=1, highlightbackground="#444", 
                           font=("Roboto", 10), padx=10, pady=8,
                           wraplength=200, justify="left")
            lbl.pack()
            tw.attributes("-topmost", True)
            tooltip_window[0] = tw

        def on_enter(event):
            if timer_id[0]: widget.after_cancel(timer_id[0])
            timer_id[0] = widget.after(500, mostrar_tooltip)

        def on_leave(event):
            if timer_id[0]: 
                widget.after_cancel(timer_id[0])
                timer_id[0] = None
            if tooltip_window[0]:
                tooltip_window[0].destroy()
                tooltip_window[0] = None

        widget.bind("<Enter>", on_enter, add="+")
        widget.bind("<Leave>", on_leave, add="+")
    
    try: adicionar_tooltip(btn_export, "Export the current session to PDF, HTML, TEX, and MD formats.")
    except: pass
    
    icon_export = None
    try:
        # Pega o diretório atual (interface/) e sobe um nível para acessar assets/
        caminho_script = os.path.dirname(os.path.abspath(__file__))
        caminho_assets = os.path.join(os.path.dirname(caminho_script), "assets", "export.png")
        
        pil_img = Image.open(caminho_assets)
        icon_export = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(24, 24))
    except Exception as e:
        print(f"Aviso: Não foi possível carregar a imagem export.png. Erro: {e}")

    # ================== 0. GRÁFICO DE CONVERGÊNCIA ==================
    lbl_conv = ctk.CTkLabel(frame_tab_content, text=" CONVERGENCE EVOLUTION ", font=("Roboto", 16, "bold"), text_color=CORES["destaque"])
    lbl_conv.pack(anchor="w", pady=(20, 5), padx=10)

    fig_conv = Figure(figsize=(largura_dinamica, 4.5), facecolor="#1E1E21")
    ax_conv = fig_conv.add_subplot(111)
    ax_conv.set_facecolor("#1E1E21")

    legend_patches_conv = []
    for cor_set in sorted(grupos.keys()):
        nome_set = grupos[cor_set]["nome"]
        lista_exp = grupos[cor_set]["exp"]
        legend_patches_conv.append(mpatches.Patch(color=cor_set, label=nome_set))
        for exp in lista_exp:
            x_vals = exp.get('x', [])
            y_vals = exp.get('y', [])
            if x_vals and y_vals:
                ax_conv.plot(x_vals, y_vals, color=cor_set, alpha=0.4, linewidth=1.5)

    ax_conv.set_title("Makespan Convergence Over Time", color="#FFFFFF", fontsize=12, pad=30, fontweight="bold")
    ax_conv.set_xlabel("Time (s)", color="#DDDDDD", fontsize=10)
    ax_conv.set_ylabel("Makespan", color="#DDDDDD", fontsize=10)
    ax_conv.tick_params(colors="#DDDDDD", labelsize=10)
    ax_conv.grid(color='#333333', linestyle='--', linewidth=0.5, alpha=0.7)
    for spine in ax_conv.spines.values():
        spine.set_color("#444444"); spine.set_linewidth(1.0)
        
    n_cols = len(legend_patches_conv) if legend_patches_conv else 1
    ax_conv.legend(handles=legend_patches_conv, loc='lower center', bbox_to_anchor=(0.5, 1.02), ncol=n_cols, frameon=False, labelcolor="#DDDDDD", fontsize=10)
    fig_conv.tight_layout()
    
    figuras_para_exportar.append(fig_conv) # GUARDA PARA EXPORTAÇÃO

    container_conv = ctk.CTkFrame(frame_tab_content, fg_color="transparent")
    container_conv.pack(fill="x", pady=(5, 30), padx=10)
    canvas_conv = FigureCanvasTkAgg(fig_conv, master=container_conv)
    lista_canvases.append(canvas_conv)
    canvas_conv.draw_idle()
    canvas_conv.get_tk_widget().pack(fill="x", expand=False, pady=10)
    toolbar_conv = CustomToolbar(canvas_conv, container_conv)
    toolbar_conv.update(); toolbar_conv.pack(side="bottom", fill="x")

    # ================== 1. GERAÇÃO DAS TABELAS INTERFACE ==================
    style = ttk.Style()
    style.theme_use("default")
    style.configure("Treeview", background="#1E1E21", foreground="white", fieldbackground="#1E1E21", borderwidth=0, rowheight=30, font=("Roboto", 10))
    style.map('Treeview', background=[('selected', CORES["primaria"])])
    style.configure("Treeview.Heading", background="#2D2D35", foreground=CORES["destaque"], font=("Roboto", 10, "bold"), borderwidth=0)
    style.map("Treeview.Heading", background=[('active', '#3D3D45')])

    def get_text_color_for_bg(hex_color):
        try:
            hex_color = hex_color.lstrip('#')
            r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            lum = 0.299 * r + 0.587 * g + 0.114 * b
            return "#000000" if lum > 160 else "#FFFFFF"
        except: return "#FFFFFF"

    def calcular_estatisticas_coluna(valores_str):
        limpos = []
        for v in valores_str:
            if v in ("-", "N/A", "") or v is None: continue
            v_limpo = str(v).replace("s", "").strip()
            try: limpos.append(float(v_limpo))
            except: pass

        if not limpos:
            return {k: "-" for k in ["Min", "Mean", "Median", "P95", "Max", "Stdev", "Variance", "Count", "CV (%)"]}

        n = len(limpos)
        limpos.sort()
        mn, mx, mean, median = min(limpos), max(limpos), sum(limpos) / n, statistics.median(limpos)

        k = (n - 1) * 0.95
        f, c = math.floor(k), math.ceil(k)
        p95 = limpos[int(k)] if f == c else limpos[f] * (c - k) + limpos[c] * (k - f)

        stdev = statistics.stdev(limpos) if n >= 2 else 0.0
        var = statistics.variance(limpos) if n >= 2 else 0.0
        cv = (stdev / mean * 100) if n >= 2 and mean != 0 else 0.0

        return {"Min": f"{mn:.2f}", "Mean": f"{mean:.2f}", "Median": f"{median:.2f}", "P95": f"{p95:.2f}", "Max": f"{mx:.2f}", "Stdev": f"{stdev:.2f}", "Variance": f"{var:.2f}", "Count": str(n), "CV (%)": f"{cv:.2f}%" if n >= 2 else "-"}

    def ordenar_coluna_treeview(tv, col, reverse):
        l_items = tv.get_children("")
        dados_reais, rodape_estatisticas = [], []
        
        for item in l_items:
            valores = tv.item(item, "values")
            tags = tv.item(item, "tags")
            if "separator" in tags or (valores and valores[0] in ["Min", "Mean", "Median", "P95", "Max", "Stdev", "Variance", "Count", "CV (%)"]):
                rodape_estatisticas.append(item)
            else:
                val_limpo = tv.set(item, col).replace("s", "").strip()
                if val_limpo in ("", "-", "N/A"): val_sort = float('inf') 
                else:
                    try: val_sort = float(val_limpo)
                    except ValueError: val_sort = val_limpo.lower()
                dados_reais.append((val_sort, item))

        try: dados_reais.sort(key=lambda x: x[0], reverse=reverse)
        except TypeError: dados_reais.sort(key=lambda x: str(x[0]), reverse=reverse)

        for index, (_, item) in enumerate(dados_reais): tv.move(item, '', index)
        for item in rodape_estatisticas: tv.move(item, '', 'end')
        tv.heading(col, command=lambda _col=col: ordenar_coluna_treeview(tv, _col, not reverse))

    for cor_set in sorted(grupos.keys()):
        nome_set = grupos[cor_set]["nome"]
        lista_exp = grupos[cor_set]["exp"]

        def get_best_makespan(exp): return min(exp['y']) if exp.get('y') else float('inf')
        lista_exp.sort(key=get_best_makespan)

        cor_texto = get_text_color_for_bg(cor_set)
        header_frame = ctk.CTkFrame(frame_tab_content, fg_color="transparent")
        header_frame.pack(fill="x", anchor="w", pady=(20, 5), padx=10)

        ctk.CTkLabel(header_frame, text=f" Group: {nome_set} ", font=("Roboto", 14, "bold"), fg_color=cor_set, text_color=cor_texto, corner_radius=0).pack(side="left")

        global SETS_DESCRICOES
        if 'SETS_DESCRICOES' not in globals(): SETS_DESCRICOES = {}
        desc = SETS_DESCRICOES.get(cor_set, "").strip()
        if desc: ctk.CTkLabel(header_frame, text=f" {desc} ", font=("Roboto", 12, "italic"), fg_color=cor_set, text_color=cor_texto, corner_radius=0).pack(side="left", padx=(10, 0))

        frame_tabela = ctk.CTkFrame(frame_tab_content, fg_color="transparent")
        frame_tabela.pack(fill="x", expand=False, padx=10, pady=(0, 15))

        tree = ttk.Treeview(frame_tabela, columns=colunas, show="headings")
        tree.tag_configure("separator", background=cor_set)

        scroll_x = ttk.Scrollbar(frame_tabela, orient="horizontal", command=tree.xview)
        tree.configure(xscrollcommand=scroll_x.set)
        tree.pack(side="top", fill="x", expand=True)
        scroll_x.pack(side="bottom", fill="x")

        mapeamento_notas = {}
        linhas_para_inserir = []

        for exp in lista_exp:
            inst = exp.get("meta_nome", "-")
            policy = exp.get("meta_decoder", "-")
            mksp = min(exp['y']) if exp.get('y') else "-"
            
            if exp.get('x') and exp.get('y'):
                runtime = f"{exp['x'][-1]:.2f}s"
                val_ttb = exp['x'][exp['y'].index(min(exp['y']))]
                time_to_best = f"{val_ttb:.2f}s"
            else: runtime, time_to_best = "-", "-"

            gantt = exp.get("gantt")
            machines, jobs = "-", "-"
            if gantt:
                if "M" in gantt: machines = str(len(gantt["M"]))
                if "C" in gantt: jobs = str(len(set(k[1] for k in gantt["C"].keys())))

            setup_rng = str(exp.get("meta_setup_range", "N/A"))
            raw_ag = exp.get('meta_agentes', [])
            if isinstance(raw_ag, str): raw_ag = [x.strip() for x in raw_ag.split("-") if x.strip()]
            param_short = ", ".join([a.split("[")[0].strip() for a in raw_ag])
            param_long = " | ".join(raw_ag)

            nota_texto = ""
            for chave_possivel in ["user_notes", "notes", "note", "nota", "notas", "Notes", "anotacao"]:
                if chave_possivel in exp and exp[chave_possivel]:
                    nota_texto = str(exp[chave_possivel]).strip()
                    break

            valores = (inst, machines, jobs, setup_rng, policy, str(mksp), runtime, time_to_best, param_short, param_long)
            linhas_para_inserir.append({"valores": valores, "nota": nota_texto, "tag": "normal"})

        stats_mac = calcular_estatisticas_coluna([p["valores"][1] for p in linhas_para_inserir])
        stats_job = calcular_estatisticas_coluna([p["valores"][2] for p in linhas_para_inserir])
        stats_mksp = calcular_estatisticas_coluna([p["valores"][5] for p in linhas_para_inserir])
        stats_rt = calcular_estatisticas_coluna([p["valores"][6] for p in linhas_para_inserir])
        stats_ttb = calcular_estatisticas_coluna([p["valores"][7] for p in linhas_para_inserir])

        estatisticas_por_grupo[cor_set] = {
            "mac": stats_mac, "job": stats_job, "mksp": stats_mksp, 
            "rt": stats_rt, "ttb": stats_ttb
        }

        linhas_para_inserir.append({"valores": tuple("" for _ in colunas), "nota": "", "tag": "separator"})

        for m in ["Min", "Mean", "Median", "P95", "Max", "Stdev", "Variance", "Count", "CV (%)"]:
            linhas_para_inserir.append({"valores": (m, stats_mac[m], stats_job[m], "-", "-", stats_mksp[m], stats_rt[m], stats_ttb[m], "-", "-"), "nota": "", "tag": "normal"})

        max_lens = {col: len(col) for col in colunas}
        for pacote in linhas_para_inserir:
            for i, col in enumerate(colunas):
                if len(str(pacote["valores"][i])) > max_lens[col]: max_lens[col] = len(str(pacote["valores"][i]))

        for col, largura in zip(colunas, [int(max_lens[col] * 8) + 30 for col in colunas]):
            tree.heading(col, text=col, anchor="w", command=lambda c=col, t=tree: ordenar_coluna_treeview(t, c, False))
            tree.column(col, width=largura, minwidth=largura, anchor="w", stretch=False)

        for pacote in linhas_para_inserir:
            item_id = tree.insert("", "end", values=pacote["valores"], tags=(pacote.get("tag", "normal"),))
            if pacote["nota"]: mapeamento_notas[item_id] = pacote["nota"]

        if mapeamento_notas: criar_tooltip_treeview(tree, mapeamento_notas)

    # ================== 2. EXTRAÇÃO DE DADOS PARA GRÁFICOS ESTATÍSTICOS ==================
    lbl_plots = ctk.CTkLabel(frame_tab_content, text=" STATISTICAL DISTRIBUTIONS ", font=("Roboto", 16, "bold"), text_color=CORES["destaque"])
    lbl_plots.pack(anchor="w", pady=(30, 5), padx=10)

    plot_labels, plot_colors, data_makespan, data_runtime, data_ttb = [], [], [], [], []

    for cor_set in sorted(grupos.keys()):
        plot_labels.append(grupos[cor_set]["nome"])
        plot_colors.append(cor_set)
        mksp_g, rt_g, ttb_g = [], [], []
        for exp in grupos[cor_set]["exp"]:
            if exp.get('y'): mksp_g.append(min(exp['y']))
            if exp.get('x') and exp.get('y'):
                rt_g.append(exp['x'][-1])
                ttb_g.append(exp['x'][exp['y'].index(min(exp['y']))])
        data_makespan.append(mksp_g); data_runtime.append(rt_g); data_ttb.append(ttb_g)

    # ================== 3. FUNÇÃO DE PLOTAGEM DOS BOXPLOTS E STRIPPLOTS ==================
    def criar_boxplot(data, title, xlabel, with_strip=False):
        plt.rcParams['font.family'] = 'sans-serif'
        valid_data, valid_colors, valid_labels = [], [], []
        for d, c, l in zip(data, plot_colors, plot_labels):
            if d: valid_data.append(d); valid_colors.append(c); valid_labels.append(l) 
        if not valid_data: return
        
        fig = Figure(figsize=(largura_dinamica, max(5.0, len(valid_data) * 1.5)), facecolor="#1E1E21")
        ax = fig.add_subplot(111); ax.set_facecolor("#1E1E21")
        
        # 1. Desenha o Stripplot  (zorder=1)
        if with_strip:
            for i, (d, color) in enumerate(zip(valid_data, valid_colors)):
                y_jitter = (i + 1) + np.random.uniform(-0.15, 0.15, size=len(d))
                # As bolinhas ficam sólidas, mas jogadas para trás
                ax.scatter(d, y_jitter, alpha=0.85, color=color, edgecolors='#FFFFFF', linewidth=0.6, s=35, zorder=1)

        # 2. Desenha o Boxplot POR CIMA
        bplot = ax.boxplot(valid_data, vert=False, patch_artist=True, labels=["" for _ in valid_data],
                           boxprops=dict(color="#DDDDDD", linewidth=1.5), 
                           capprops=dict(color="#DDDDDD", linewidth=1.5),
                           whiskerprops=dict(color="#DDDDDD", linewidth=1.5), 
                           flierprops=dict(markerfacecolor="#FFFFFF", markeredgecolor="#FFFFFF", marker='o', markersize=5),
                           medianprops=dict(color="#FFFFFF", linewidth=2.0))
                           
        # Ajusta a opacidade (alpha) e traz a caixa para a frente (zorder=3)
        for patch, color in zip(bplot['boxes'], valid_colors): 
            patch.set_facecolor(color)
            patch.set_zorder(3) 
            if with_strip:
                patch.set_alpha(0.6) # Efeito "vidro": permite ver as bolinhas atrás
            else:
                patch.set_alpha(1.0)
                
        # Traz as linhas do boxplot (mediana, bigodes, etc.) para a primeiríssima camada (zorder=4)
        for line in bplot['medians']: line.set_zorder(4)
        for line in bplot['whiskers']: line.set_zorder(4)
        for line in bplot['caps']: line.set_zorder(4)
        for line in bplot['fliers']: line.set_zorder(4)

        # 3. Estilização Geral
        ax.set_title(title, color="#FFFFFF", fontsize=12, pad=30, fontweight="bold")
        ax.set_xlabel(xlabel, color="#DDDDDD", fontsize=10)
        ax.tick_params(colors="#DDDDDD", labelsize=10)
        ax.grid(axis='x', color='#333333', linestyle='--', linewidth=0.5, alpha=0.7)
        ax.set_axisbelow(True); ax.tick_params(axis='y', which='both', length=0)
        for spine in ax.spines.values(): spine.set_color("#444444"); spine.set_linewidth(1.0)
            
        legend_patches = [mpatches.Patch(color=c, label=l) for c, l in zip(valid_colors, valid_labels)]
        ax.legend(handles=legend_patches, loc='lower center', bbox_to_anchor=(0.5, 1.02), ncol=max(1, len(legend_patches)), frameon=False, labelcolor="#DDDDDD", fontsize=10)
        fig.tight_layout()
        
        figuras_para_exportar.append(fig)
        
        container_frame = ctk.CTkFrame(frame_tab_content, fg_color="transparent")
        container_frame.pack(fill="x", pady=(10, 25), padx=10)
        canvas = FigureCanvasTkAgg(fig, master=container_frame)
        lista_canvases.append(canvas)
        canvas.draw_idle()
        canvas.get_tk_widget().pack(fill="x", expand=False, pady=10)
        CustomToolbar(canvas, container_frame).update()

    # MAKESPAN
    criar_boxplot(data_makespan, "Makespan", "Makespan Value", with_strip=False)
    criar_boxplot(data_makespan, "Makespan (Boxplot + Stripplot)", "Makespan Value", with_strip=True)

    # RUNTIME
    criar_boxplot(data_runtime, "Total Runtime ", "Seconds (s)", with_strip=False)
    criar_boxplot(data_runtime, "Total Runtime (Boxplot + Stripplot)", "Seconds (s)", with_strip=True)

    # TIME TO BEST
    criar_boxplot(data_ttb, "Time to Best", "Seconds (s)", with_strip=False)
    criar_boxplot(data_ttb, "Time to Best (Boxplot + Stripplot)", "Seconds (s)", with_strip=True)

   # ================== 4. GRÁFICOS DE INTERVALO DE CONFIANÇA 95% (EMPILHADOS E COMPACTOS) ==================
    lbl_ic_plots = ctk.CTkLabel(frame_tab_content, text=" 95% CONFIDENCE INTERVALS (BOOTSTRAP) ", font=("Roboto", 16, "bold"), text_color=CORES["destaque"])
    lbl_ic_plots.pack(anchor="w", pady=(30, 5), padx=10)

    # Filtra os dados válidos primeiro
    valid_data_m, valid_data_t, valid_colors, valid_labels = [], [], [], []
    for dm, dt, c, l in zip(data_makespan, data_ttb, plot_colors, plot_labels):
        if dm or dt: 
            valid_data_m.append(dm)
            valid_data_t.append(dt)
            valid_colors.append(c)
            valid_labels.append(l)

    if valid_data_m or valid_data_t:
        def calcular_bootstrap_ic(arr, n_resamples=10000):
            if not arr: return 0, 0, 0
            if len(arr) < 2: return (arr[0] if len(arr) == 1 else 0), (arr[0] if len(arr) == 1 else 0), (arr[0] if len(arr) == 1 else 0)
            arr_np = np.array(arr)
            medias_amostrais = np.mean(np.random.choice(arr_np, size=(n_resamples, len(arr_np)), replace=True), axis=1)
            return np.mean(arr_np), np.percentile(medias_amostrais, 2.5), np.percentile(medias_amostrais, 97.5)

        # --- FIX: Aumentamos ligeiramente a proporção da altura para compensar o novo espaçamento ---
        altura_dinamica = max(3.0, len(valid_labels) * 0.7)
        fig_ic = Figure(figsize=(largura_dinamica, altura_dinamica * 2.2), facecolor="#1E1E21")
        
        ax_m = fig_ic.add_subplot(211) # Cima
        ax_t = fig_ic.add_subplot(212) # Baixo
        ax_m.set_facecolor("#1E1E21")
        ax_t.set_facecolor("#1E1E21")

        y_positions = np.arange(len(valid_labels))

        # --- Desenha Makespan (Cima) ---
        means_m, erro_inf_m, erro_sup_m = [], [], []
        for d in valid_data_m:
            m, inf, sup = calcular_bootstrap_ic(d)
            means_m.append(m); erro_inf_m.append(m - inf); erro_sup_m.append(sup - m)
        
        for i in range(len(valid_labels)):
            if valid_data_m[i]:
                ax_m.errorbar(means_m[i], y_positions[i], xerr=[[erro_inf_m[i]], [erro_sup_m[i]]], fmt='o', color=valid_colors[i], ecolor=valid_colors[i], elinewidth=3, capsize=6, capthick=2, markersize=8)

        # --- Desenha Time to Best (Baixo) ---
        means_t, erro_inf_t, erro_sup_t = [], [], []
        for d in valid_data_t:
            m, inf, sup = calcular_bootstrap_ic(d)
            means_t.append(m); erro_inf_t.append(m - inf); erro_sup_t.append(sup - m)
            
        for i in range(len(valid_labels)):
            if valid_data_t[i]:
                ax_t.errorbar(means_t[i], y_positions[i], xerr=[[erro_inf_t[i]], [erro_sup_t[i]]], fmt='o', color=valid_colors[i], ecolor=valid_colors[i], elinewidth=3, capsize=6, capthick=2, markersize=8)

        # --- Estilização ---
        titulos = ["Makespan 95% CI", "Time to Best 95% CI"]
        xlabels = ["Mean Makespan", "Mean Seconds (s)"]
        
        for ax, titulo, xlabel in zip([ax_m, ax_t], titulos, xlabels):
            ax.set_yticks(y_positions)
            ax.set_yticklabels(["" for _ in valid_labels])
            
            # --- FIX: O gráfico de cima ganha um pad gigante (45) para empurrar o título para o topo.
            # O gráfico de baixo continua com pad=15 para o título não voar.
            pad_val = 45 if ax == ax_m else 15
            ax.set_title(titulo, color="#FFFFFF", fontsize=12, pad=pad_val, fontweight="bold")
            
            ax.set_xlabel(xlabel, color="#DDDDDD", fontsize=10)
            ax.tick_params(colors="#DDDDDD", labelsize=10)
            ax.grid(axis='x', color='#333333', linestyle='--', linewidth=0.5, alpha=0.7)
            ax.set_axisbelow(True)
            ax.tick_params(axis='y', which='both', length=0)
            for spine in ax.spines.values():
                spine.set_color("#444444")
                spine.set_linewidth(1.0)

        # --- FIX: A legenda desce para a posição (1.08), ficando perfeitamente ensanduichada entre o título e o gráfico!
        legend_patches = [mpatches.Patch(color=c, label=l) for c, l in zip(valid_colors, valid_labels)]
        ax_m.legend(handles=legend_patches, loc='lower center', bbox_to_anchor=(0.5, 1.08), ncol=max(1, len(legend_patches)), frameon=False, labelcolor="#DDDDDD", fontsize=10)

        # O 'top=0.85' garante que o título lá em cima não é cortado pela borda da imagem
        fig_ic.subplots_adjust(left=0.08, right=0.95, top=0.85, bottom=0.10, hspace=0.70)

        figuras_para_exportar.append(fig_ic) 

        container_ic = ctk.CTkFrame(frame_tab_content, fg_color="transparent")
        container_ic.pack(fill="x", pady=(10, 25), padx=10)
        canvas_ic = FigureCanvasTkAgg(fig_ic, master=container_ic)
        lista_canvases.append(canvas_ic)
        canvas_ic.draw_idle()
        canvas_ic.get_tk_widget().pack(fill="x", expand=False, pady=10)
        CustomToolbar(canvas_ic, container_ic).update()

    # ================== 5. FREQUENCY HISTOGRAMS ==================
    lbl_hist = ctk.CTkLabel(frame_tab_content, text=" FREQUENCY HISTOGRAMS", font=("Roboto", 16, "bold"), text_color=CORES["destaque"])
    lbl_hist.pack(anchor="w", pady=(30, 5), padx=10)

    frame_combo_hist = ctk.CTkFrame(frame_tab_content, fg_color="transparent")
    frame_combo_hist.pack(fill="x", padx=10, pady=(0, 10))
    ctk.CTkLabel(frame_combo_hist, text="Binning Rule:", text_color="white", font=("Roboto", 12)).pack(side="left", padx=(0, 10))
    
    combo_bins = ctk.CTkComboBox(frame_combo_hist, values=["Sturges' Rule", "Rice's Rule", "Scott's Rule", "Freedman-Diaconis"], state="readonly", width=180, fg_color="#2D2D35", border_color="#444444", text_color="white")
    combo_bins.set("Freedman-Diaconis")
    combo_bins.pack(side="left")

    container_hist = ctk.CTkFrame(frame_tab_content, fg_color="transparent")
    container_hist.pack(fill="x", pady=(5, 30), padx=10)
    fig_hist = Figure(figsize=(largura_dinamica, 9.0), facecolor="#1E1E21")
    canvas_hist = FigureCanvasTkAgg(fig_hist, master=container_hist)
    lista_canvases.append(canvas_hist)
    figuras_para_exportar.append(fig_hist) # GUARDA PARA EXPORTAÇÃO

    mapa_regras = {"Sturges' Rule": "sturges", "Rice's Rule": "rice", "Scott's Rule": "scott", "Freedman-Diaconis": "fd"}

    # Função que desenha (e redesenha) o gráfico baseada na regra
    def atualizar_histogramas(escolha_ui):
        regra_np = mapa_regras.get(escolha_ui, "sturges")
        
        # --- FIX: Lê o estado da checkbox para manter as cores corretas ao atualizar! ---
        is_light = False
        try:
            is_light = var_light_theme.get()
        except Exception:
            pass # Se a variável ainda não estiver pronta no momento da criação, assume escuro
            
        bg_c = "#FFFFFF" if is_light else "#1E1E21"
        title_c = "#111111" if is_light else "#FFFFFF"
        text_c = "#333333" if is_light else "#DDDDDD"
        spine_c = "#CCCCCC" if is_light else "#444444"
        grid_c = "#EAEAEA" if is_light else "#333333"
        # -------------------------------------------------------------------------------

        fig_hist.clf() 
        fig_hist.patch.set_facecolor(bg_c)
        
        ax_m, ax_t = fig_hist.add_subplot(211), fig_hist.add_subplot(212)
        ax_m.set_facecolor(bg_c); ax_t.set_facecolor(bg_c)
        tem_dados = False

        for i in range(len(plot_labels)):
            m_data, t_data = data_makespan[i], data_ttb[i]
            if m_data:
                tem_dados = True
                ax_m.hist(m_data, bins=(regra_np if len(set(m_data)) > 1 else 1), alpha=0.6, color=plot_colors[i], edgecolor=title_c, linewidth=1.0, label=plot_labels[i])
            if t_data:
                ax_t.hist(t_data, bins=(regra_np if len(set(t_data)) > 1 else 1), alpha=0.6, color=plot_colors[i], edgecolor=title_c, linewidth=1.0, label=plot_labels[i])

        # --- Aplicação das cores dinâmicas no Makespan (Cima) ---
        ax_m.set_title("Makespan Frequency", color=title_c, fontsize=12, pad=40, fontweight="bold")
        ax_m.set_xlabel("Makespan Value", color=text_c, fontsize=10)
        ax_m.set_ylabel("Frequency", color=text_c, fontsize=10)
        ax_m.tick_params(colors=text_c, labelsize=10)
        ax_m.grid(axis='y', color=grid_c, linestyle='--', linewidth=0.5, alpha=0.7)
        ax_m.set_axisbelow(True)
        for spine in ax_m.spines.values(): 
            spine.set_color(spine_c)
            spine.set_linewidth(1.0)

        # --- Aplicação das cores dinâmicas no Time to Best (Baixo) ---
        ax_t.set_title("Time to Best Frequency", color=title_c, fontsize=12, pad=40, fontweight="bold")
        ax_t.set_xlabel("Seconds (s)", color=text_c, fontsize=10)
        ax_t.set_ylabel("Frequency", color=text_c, fontsize=10)
        ax_t.tick_params(colors=text_c, labelsize=10)
        ax_t.grid(axis='y', color=grid_c, linestyle='--', linewidth=0.5, alpha=0.7)
        ax_t.set_axisbelow(True)
        for spine in ax_t.spines.values(): 
            spine.set_color(spine_c)
            spine.set_linewidth(1.0)

        if tem_dados:
            legend_patches = [mpatches.Patch(color=c, label=l) for c, l in zip(plot_colors, plot_labels)]
            ax_m.legend(handles=legend_patches, loc='lower center', bbox_to_anchor=(0.5, 1.05), ncol=max(1, len(legend_patches)), frameon=False, labelcolor=text_c, fontsize=10)
            ax_t.legend(handles=legend_patches, loc='lower center', bbox_to_anchor=(0.5, 1.05), ncol=max(1, len(legend_patches)), frameon=False, labelcolor=text_c, fontsize=10)
        
        fig_hist.subplots_adjust(left=0.08, right=0.95, top=0.88, bottom=0.12, hspace=0.6)
        canvas_hist.draw_idle()

    combo_bins.configure(command=atualizar_histogramas)
    atualizar_histogramas("Freedman-Diaconis")

    canvas_hist.get_tk_widget().pack(fill="x", expand=False, pady=10)
    CustomToolbar(canvas_hist, container_hist).update()


    # ================== 6. TESTES ESTATÍSTICOS (FRIEDMAN, WILCOXON, NEMENYI) ==================
    lbl_stats = ctk.CTkLabel(frame_tab_content, text=" STATISTICAL SIGNIFICANCE TESTS ", font=("Roboto", 16, "bold"), text_color=CORES["destaque"])
    lbl_stats.pack(anchor="w", pady=(30, 5), padx=10)

    frame_controles_stats = ctk.CTkFrame(frame_tab_content, fg_color="transparent")
    frame_controles_stats.pack(fill="x", padx=10, pady=(0, 10))

    ctk.CTkLabel(frame_controles_stats, text="Select Metric:", text_color="white", font=("Roboto", 12)).pack(side="left", padx=(0, 10))
    combo_metric_stats = ctk.CTkComboBox(frame_controles_stats, values=["Makespan", "Time to Best", "Runtime"], state="readonly", width=150, fg_color="#2D2D35", border_color="#444444", text_color="white")
    combo_metric_stats.set("Makespan")
    combo_metric_stats.pack(side="left")

    container_matriz = ctk.CTkFrame(frame_tab_content, fg_color="transparent")
    container_matriz.pack(fill="x", pady=(10, 30), padx=10)

    def obter_asteriscos(p_val):
        if p_val < 0.001: return f"{p_val:.4f} ***"
        elif p_val < 0.01: return f"{p_val:.4f} **"
        elif p_val < 0.05: return f"{p_val:.4f} *"
        else: return f"{p_val:.4f} ns"

    def atualizar_matriz_estatistica(escolha_metrica):
        for widget in container_matriz.winfo_children():
            widget.destroy()

        try:
            import scipy.stats as stats
            import scikit_posthocs as sp
            import numpy as np
            import os # Adicionado para corrigir caminhos de instâncias
        except ImportError:
            ctk.CTkLabel(container_matriz, text="⚠️ Install required libraries to use this feature:\npip install scipy scikit-posthocs", text_color="#E74C3C").pack(pady=20)
            return

        # 1. Extrair os dados pareados (COM CORREÇÃO DE REPETIÇÕES E CAMINHOS)
        dados_pareados = {}
        nomes_grupos = []
        
        for cor_set in sorted(grupos.keys()):
            nome_g = grupos[cor_set]["nome"]
            if nome_g in nomes_grupos: 
                nome_g = f"{nome_g} ({cor_set})"
            nomes_grupos.append(nome_g)
            
            dict_inst = {}
            contagem_nomes = {} 
            
            for exp in grupos[cor_set]["exp"]:
                nome_bruto = str(exp.get("meta_nome", "Inst")).strip()
                inst_base = os.path.basename(nome_bruto)
                
                if not inst_base or inst_base == "-": 
                    inst_base = "Inst"
                
                contagem_nomes[inst_base] = contagem_nomes.get(inst_base, 0) + 1
                inst_id = f"{inst_base}_run{contagem_nomes[inst_base]}"
                
                val = None
                if escolha_metrica == "Makespan" and exp.get('y'):
                    val = min(exp['y'])
                elif escolha_metrica == "Time to Best" and exp.get('x') and exp.get('y'):
                    val = exp['x'][exp['y'].index(min(exp['y']))]
                elif escolha_metrica == "Runtime" and exp.get('x'):
                    val = exp['x'][-1]
                
                if val is not None:
                    dict_inst[inst_id] = val
                    
            dados_pareados[nome_g] = dict_inst

        if len(nomes_grupos) < 2:
            ctk.CTkLabel(container_matriz, text="⚠️ Not enough groups to run statistical tests (minimum 2).", text_color="gray").pack(pady=20)
            return

        # Intersecção de instâncias em comum
        lista_conjuntos = [set(d.keys()) for d in dados_pareados.values()]
        if not lista_conjuntos: return
        insts_comuns = set.intersection(*lista_conjuntos)
        
        # Sistema de Debug Inteligente
        if len(insts_comuns) < 3:
            msg = f"⚠️ Estatística Impossível: Foram encontradas apenas {len(insts_comuns)} amostras pareadas em comum.\n\n"
            msg += "Regra Matemática: Testes não-paramétricos exigem no MÍNIMO 3 execuções em comum.\n"
            if len(insts_comuns) == 0:
                msg += "\n💡 DICA DE DEBUG: Veja como a interface leu os nomes das suas instâncias:\n"
                for g, d in dados_pareados.items():
                    exemplos = list(d.keys())[:3]
                    msg += f"   ➤ {g}: {exemplos}\n"

            lbl_erro = ctk.CTkLabel(container_matriz, text=msg, text_color="#E74C3C", font=("Roboto", 13), justify="left")
            lbl_erro.grid(row=0, column=0, padx=10, pady=20, sticky="w")
            return

        insts_comuns = sorted(list(insts_comuns))
        matriz_dados = np.array([[dados_pareados[g][inst] for inst in insts_comuns] for g in nomes_grupos])

        # 2. Teste de Friedman (Global)
        if len(nomes_grupos) > 2:
            stat_f, p_friedman = stats.friedmanchisquare(*matriz_dados)
            texto_friedman = f"Friedman Test p-value: {obter_asteriscos(p_friedman)}"
        else:
            p_friedman = 0.0
            texto_friedman = "Friedman Test: N/A (Only 2 groups)"

        cor_f = "#2ECC71" 
        ctk.CTkLabel(container_matriz, text=texto_friedman, font=("Roboto", 14, "bold"), text_color=cor_f).grid(row=0, column=0, columnspan=len(nomes_grupos)+1, pady=(0, 5), sticky="w")

        # 3. Testes Post-Hoc (Wilcoxon e Nemenyi)
        n_grupos = len(nomes_grupos)
        
        if n_grupos > 2:
            try:
                matriz_nemenyi = sp.posthoc_nemenyi(matriz_dados.T)
            except:
                matriz_nemenyi = None
        else: matriz_nemenyi = None

        # ==========================================================
        # VERIFICA O TEMA ATUAL PARA APLICAR A PALETA DE CORES CORRETA
        # ==========================================================
        modo_light = var_light_theme.get() == 1
        
        if modo_light:
            cor_bg_matriz = "#FFFFFF"     # Fundo branco
            cor_bg_cabecalho = "#F0F0F0"  # Cinza bem claro
            cor_txt_cabecalho = "#333333" # Texto escuro
            
            cor_bg_diag = "#F8F9FA"       # Quase branco
            cor_txt_diag = "#888888"
            
            cor_bg_wilcoxon = "#E3F2FD"   # Azul pastel
            cor_txt_wilcoxon_sig = "#0D47A1" # Azul forte (Significativo)
            cor_txt_wilcoxon_ns = "#666666"  # Cinza (Não Significativo)
            
            cor_bg_nemenyi = "#FFF9C4"    # Amarelo pastel
            cor_txt_nemenyi_sig = "#F57F17"  # Laranja/Mostarda forte (Significativo)
            cor_txt_nemenyi_ns = "#666666"   # Cinza (Não Significativo)
            
            cor_txt_legenda_base = "#FFFFFF" # Texto da legenda escuro para leitura no fundo claro
        else:
            cor_bg_matriz = "transparent"
            cor_bg_cabecalho = "#2D2D35"
            cor_txt_cabecalho = "#FFFFFF"
            
            cor_bg_diag = "#1A1A1E"
            cor_txt_diag = "#444444"
            
            cor_bg_wilcoxon = "#1C3A5A"
            cor_txt_wilcoxon_sig = "#64B5F6"
            cor_txt_wilcoxon_ns = "#90CAF9"
            
            cor_bg_nemenyi = "#524A15"
            cor_txt_nemenyi_sig = "#FFD54F"
            cor_txt_nemenyi_ns = "#FFE082"
            
            cor_txt_legenda_base = "white"

        # --- LEGENDA ÚNICA NO TOPO COM COR DINÂMICA ---
        legenda = ctk.CTkFrame(container_matriz, fg_color="transparent")
        legenda.grid(row=1, column=0, columnspan=n_grupos+1, pady=(0, 20), sticky="w")
        
        ctk.CTkLabel(legenda, text="Upper Triangle (Blue): ", font=("Roboto", 12, "bold"), text_color="#64B5F6" if not modo_light else "#1976D2").pack(side="left")
        ctk.CTkLabel(legenda, text="Wilcoxon Signed-Rank Test   |   ", font=("Roboto", 12), text_color=cor_txt_legenda_base).pack(side="left")
        
        ctk.CTkLabel(legenda, text="Lower Triangle (Yellow): ", font=("Roboto", 12, "bold"), text_color="#FFD54F" if not modo_light else "#F57F17").pack(side="left")
        ctk.CTkLabel(legenda, text="Nemenyi Post-hoc Test   |   ", font=("Roboto", 12), text_color=cor_txt_legenda_base).pack(side="left")
        
        ctk.CTkLabel(legenda, text="*** p<0.001   ** p<0.01   * p<0.05   ns: not significant", font=("Roboto", 12, "italic"), text_color="#AAAAAA").pack(side="left")

        # 4. Desenhar a Matriz Customizada (Expandida) e Salvar para Exportação
        for col in range(n_grupos + 1):
            container_matriz.grid_columnconfigure(col, weight=1)

        ctk.CTkFrame(container_matriz, fg_color=cor_bg_matriz, height=50).grid(row=2, column=0, padx=2, pady=2, sticky="nsew")
        
        for i, nome in enumerate(nomes_grupos):
            lbl_top = ctk.CTkLabel(container_matriz, text=nome, font=("Roboto", 13, "bold"), fg_color=cor_bg_cabecalho, text_color=cor_txt_cabecalho, height=50, corner_radius=6)
            lbl_top.grid(row=2, column=i+1, padx=2, pady=2, sticky="nsew")
            lbl_left = ctk.CTkLabel(container_matriz, text=nome, font=("Roboto", 13, "bold"), fg_color=cor_bg_cabecalho, text_color=cor_txt_cabecalho, height=50, corner_radius=6)
            lbl_left.grid(row=i+3, column=0, padx=2, pady=2, sticky="nsew")
            container_matriz.grid_rowconfigure(i+3, weight=1)

        # --- VARIÁVEL QUE VAI GUARDAR OS DADOS PARA O EXPORTADOR ---
        grade_exportacao = []

        for i in range(n_grupos):
            linha_export = []
            for j in range(n_grupos):
                texto_celula = "-"
                cor_fundo = cor_bg_diag 
                cor_texto = cor_txt_diag
                tipo_celula = "diag" 

                if i < j: 
                    cor_fundo = cor_bg_wilcoxon 
                    tipo_celula = "wilcoxon"
                    try:
                        _, p_val = stats.wilcoxon(matriz_dados[i], matriz_dados[j], zero_method='zsplit')
                        texto_celula = obter_asteriscos(p_val)
                        cor_texto = cor_txt_wilcoxon_sig if p_val < 0.05 else cor_txt_wilcoxon_ns
                    except ValueError:
                        texto_celula = "Tie"
                
                elif i > j: 
                    cor_fundo = cor_bg_nemenyi 
                    tipo_celula = "nemenyi"
                    if matriz_nemenyi is not None:
                        p_val = matriz_nemenyi.iloc[i, j]
                        texto_celula = obter_asteriscos(p_val)
                        cor_texto = cor_txt_nemenyi_sig if p_val < 0.05 else cor_txt_nemenyi_ns
                    else:
                        texto_celula = "N/A"

                frm = ctk.CTkFrame(container_matriz, fg_color=cor_fundo, corner_radius=6, height=50)
                frm.grid(row=i+3, column=j+1, padx=2, pady=2, sticky="nsew")
                frm.grid_propagate(False)
                frm.columnconfigure(0, weight=1)
                frm.rowconfigure(0, weight=1)
                ctk.CTkLabel(frm, text=texto_celula, font=("Roboto", 13, "bold" if "ns" not in texto_celula else "normal"), text_color=cor_texto).grid(row=0, column=0, sticky="nsew")
                
                # Guarda a informação limpa desta célula para o PDF/HTML
                linha_export.append({"texto": texto_celula, "tipo": tipo_celula})
            grade_exportacao.append(linha_export)

        # Guarda na memória global da aba para o botão de exportar conseguir ler
        ABA_ANALISE_GLOBAL.dados_stats_export = {
            "metrica": escolha_metrica,
            "nomes": nomes_grupos,
            "texto_friedman": texto_friedman,
            "grade": grade_exportacao
        }
    combo_metric_stats.configure(command=atualizar_matriz_estatistica)
    atualizar_matriz_estatistica("Makespan")

    tabs_obj[nome_analise] = {"btn_frame": tab_btn, "content": frame_tab_content}
    selecionar_aba(nome_analise)
    FUNCAO_SHOW_TAB_GLOBAL(ABA_ANALISE_GLOBAL)

def configurar_aba_historico(aba, largura_total=1280, altura_total=810):
    global FRAME_LISTA_HISTORICO, FIG_HIST_LINHA, AX_HIST_LINHA, CANVAS_HIST_LINHA, FIG_HIST_GANTT, AX_HIST_GANTT, CANVAS_HIST_GANTT
    global VAR_FILTRO_INSTANCIA, VAR_FILTRO_DECODER, VARS_FILTRO_AGENTES, COMBO_INSTANCIAS, VAR_ORDENACAO_HISTORICO

    for i in range(2, 20):
        aba.grid_columnconfigure(i, weight=0, minsize=0)
        aba.grid_rowconfigure(i, weight=0, minsize=0)

    aba.grid_columnconfigure(0, weight=0, minsize=280) 
    aba.grid_columnconfigure(1, weight=1) 
    aba.grid_rowconfigure(0, weight=1)

    frame_esq = ctk.CTkFrame(aba, fg_color="transparent", width=270)
    frame_esq.grid(row=0, column=0, rowspan=10, sticky="nsew", padx=(5, 5), pady=(5, 5))
    
    frame_esq.grid_rowconfigure(2, weight=1) 
    frame_esq.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(frame_esq, text="FINISHED JOBS", font=("Roboto", 16, "bold"), text_color=CORES["destaque"]).grid(row=0, column=0, pady=(0, 5), sticky="ew")

    frame_filtros = ctk.CTkFrame(frame_esq, fg_color="#242424", corner_radius=8)
    frame_filtros.grid(row=1, column=0, sticky="ew", pady=(0, 10), padx=2)
    
    ctk.CTkLabel(frame_filtros, text="Filter by Instance:", font=("Roboto", 10)).pack(anchor="w", padx=5, pady=(5,0))
    VAR_FILTRO_INSTANCIA = ctk.StringVar(value="all")
    COMBO_INSTANCIAS = ctk.CTkComboBox(frame_filtros, variable=VAR_FILTRO_INSTANCIA, values=["all"], state="readonly", height=22, font=("Roboto", 11), command=aplicar_filtros_historico)
    COMBO_INSTANCIAS.pack(fill="x", padx=5, pady=(0, 5))
    
    ctk.CTkLabel(frame_filtros, text="Filter by Decoder:", font=("Roboto", 10)).pack(anchor="w", padx=5)
    VAR_FILTRO_DECODER = ctk.StringVar(value="all")
    combo_dec = ctk.CTkComboBox(frame_filtros, variable=VAR_FILTRO_DECODER, values=["all", "CHEAPEST", "M3LAW", "ECT", "INCREMENTAL", "KSTS"], state="readonly", height=22, font=("Roboto", 11), command=aplicar_filtros_historico)
    combo_dec.pack(fill="x", padx=5, pady=(0, 5))

    ctk.CTkLabel(frame_filtros, text="Sort by:", font=("Roboto", 10)).pack(anchor="w", padx=5)
    VAR_ORDENACAO_HISTORICO = ctk.StringVar(value="Descending Date/Hour")
    combo_sort = ctk.CTkComboBox(
        frame_filtros, 
        variable=VAR_ORDENACAO_HISTORICO,
        values=[
            "Descending Date/Hour", 
            "Ascending Date/Hour", 
            "Ascending Instance", 
            "Descending Instance", 
            "Ascending Makespan", 
            "Descending Makespan",
            "Decoder"
        ],
        state="readonly", 
        height=22, 
        font=("Roboto", 11),
        command=aplicar_filtros_historico
    )
    combo_sort.pack(fill="x", padx=5, pady=(0, 5))

    ctk.CTkLabel(frame_filtros, text="Select RKO Agents:", font=("Roboto", 10)).pack(anchor="w", padx=5)
    
    frm_agentes_container = ctk.CTkFrame(frame_filtros, fg_color="transparent")
    frm_agentes_container.pack(fill="x", padx=2, pady=2)

    # 1. Lado Esquerdo: Grade de Checkboxes
    frame_checks = ctk.CTkFrame(frm_agentes_container, fg_color="transparent")
    frame_checks.pack(side="left", fill="both", expand=True)
    
    lista_agentes = ["BRKGA", "SA", "ILS", "VNS", "PSO", "GA", "LNS"]
    VARS_FILTRO_AGENTES = {}
    for i, ag in enumerate(lista_agentes):
        var = ctk.BooleanVar(value=False)
        chk = ctk.CTkCheckBox(frame_checks, text=ag, variable=var, font=("Roboto", 9), height=16, width=16, checkbox_width=16, checkbox_height=16, command=aplicar_filtros_historico)
        chk.grid(row=i//3, column=i%3, sticky="w", padx=2, pady=2)
        VARS_FILTRO_AGENTES[ag] = var

    # 2. Lado Direito: Botão Analyse
    # Botão azulado para destacar ação de análise
    btn_analyse = ctk.CTkButton(frm_agentes_container, text="ANALYSIS", width=65, height=50, 
                                font=("Roboto", 10, "bold"),
                                fg_color="#0284c7", hover_color="#0ea5e9",
                                command=pedir_nome_analise
                                )
    btn_analyse.pack(side="right", padx=(5, 5), pady=2, anchor="center")
    # -----------------------------------------------------------

    FRAME_LISTA_HISTORICO = ctk.CTkScrollableFrame(frame_esq, width=250, fg_color=CORES["fundo_cartao"], corner_radius=10)
    FRAME_LISTA_HISTORICO.grid(row=2, column=0, sticky="nsew", padx=0, pady=0)
    FRAME_LISTA_HISTORICO.grid_columnconfigure(0, weight=1)

    frame_dir = ctk.CTkScrollableFrame(aba, fg_color="transparent")
    frame_dir.grid(row=0, column=1, rowspan=10, sticky="nsew", padx=(5, 5), pady=5)
    frame_dir.grid_columnconfigure(0, weight=1) 

    # GRÁFICOS
    frame_top = ctk.CTkFrame(frame_dir, fg_color="#242424", corner_radius=10, height=500) 
    frame_top.pack(fill="x", pady=(0, 20)); frame_top.pack_propagate(False) 
    
    FIG_HIST_LINHA, AX_HIST_LINHA = plt.subplots(dpi=100) 
    FIG_HIST_LINHA.patch.set_facecolor('#242424'); AX_HIST_LINHA.set_facecolor('#2b2b2b')
    AX_HIST_LINHA.set_title("Convergence Curves", color="white", fontsize=10)
    AX_HIST_LINHA.tick_params(colors='white', labelsize=8)
    for s in AX_HIST_LINHA.spines.values(): s.set_color('white')
    FIG_HIST_LINHA.subplots_adjust(left=0.05, right=0.98, top=0.92, bottom=0.15)

    CANVAS_HIST_LINHA = FigureCanvasTkAgg(FIG_HIST_LINHA, master=frame_top)
    toolbar_linha = CustomToolbar(CANVAS_HIST_LINHA, frame_top)
    toolbar_linha.update()
    toolbar_linha.pack(side="bottom", fill="x")

    CANVAS_HIST_LINHA.draw(); CANVAS_HIST_LINHA.get_tk_widget().pack(side="top", fill="both", expand=True)

    frame_bot = ctk.CTkFrame(frame_dir, fg_color="#242424", corner_radius=10, height=700)
    frame_bot.pack(fill="x", pady=0); frame_bot.pack_propagate(False) 
    
    FIG_HIST_GANTT, AX_HIST_GANTT = plt.subplots(dpi=100) 
    FIG_HIST_GANTT.patch.set_facecolor('#242424'); AX_HIST_GANTT.set_facecolor('#212121')
    AX_HIST_GANTT.set_title("Current Schedule", color="white", fontsize=10)
    AX_HIST_GANTT.tick_params(colors='white', labelsize=8)
    for s in AX_HIST_GANTT.spines.values(): s.set_color('white')
    FIG_HIST_GANTT.subplots_adjust(left=0.05, right=0.98, top=0.95, bottom=0.15)
    
    CANVAS_HIST_GANTT = FigureCanvasTkAgg(FIG_HIST_GANTT, master=frame_bot)
    toolbar_gantt = CustomToolbar(CANVAS_HIST_GANTT, frame_bot)
    toolbar_gantt.update()
    toolbar_gantt.pack(side="bottom", fill="x")
    CANVAS_HIST_GANTT.draw(); CANVAS_HIST_GANTT.get_tk_widget().pack(side="top", fill="both", expand=True)

    iniciar_watchdog_historico()

def carregar_instancia_historico(chave_unica):
    global CHAVE_SELECIONADA_ATUAL
    CHAVE_SELECIONADA_ATUAL = chave_unica    
    aplicar_filtros_historico()
    dados = HISTORICO_DATA.get(chave_unica)
    if not dados: return

    AX_HIST_GANTT.clear()
    gantt = dados['gantt']
    max_makespan = 0
    if gantt:
        M, p, X, C = gantt["M"], gantt["p"], gantt["X"], gantt["C"]
        import matplotlib.cm as cm
        max_id = max([k[1] for k in C.keys()]) if C else 10
        colors = cm.get_cmap("tab20", max_id + 1)
        for i in M:
            jobs = [j for (m, k, j), v in X.items() if m == i and v > 0.5]
            for j in jobs:
                comp = C.get((i, j), 0); proc = p.get((i, j), 0); start = comp - proc
                if comp > max_makespan: max_makespan = comp
                AX_HIST_GANTT.barh(y=f'M{i}', width=proc, left=start, height=0.6, color=colors(j), edgecolor='black')
                if proc > 0: AX_HIST_GANTT.text(start + proc/2, f'M{i}', f'{j}', ha='center', va='center', color='white', fontsize=6, fontweight='bold')
    
    AX_HIST_GANTT.set_facecolor('#212121'); AX_HIST_GANTT.invert_yaxis()
    AX_HIST_GANTT.set_title(f"Current Schedule | Makespan: {max_makespan}", color="white", fontsize=10)
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
    AX_GANTT.set_title(f"Instance: {nome_instancia}  |  Makespan: {max_completion_time}  |  Time to Best: {tempo_decorrido:.2f}s", color="white", fontsize=11, fontweight="bold")
    AX_GANTT.set_xlabel("Horizon", fontsize=9, color="white")
    AX_GANTT.set_ylabel("Machines", fontsize=9, color="white")
    AX_GANTT.tick_params(axis='x', colors='white', labelsize=8); AX_GANTT.tick_params(axis='y', colors='white', labelsize=8)
    for s in AX_GANTT.spines.values(): s.set_color('white')
    AX_GANTT.grid(axis='x', linestyle='--', alpha=0.2, color='white')
    CANVAS_GANTT.draw()

def manipulador_retorno_interface(dados):
    global ESCRITOR_TERMINAL_GLOBAL, START_BUTTON_GLOBAL, DADOS_X, DADOS_Y, NOME_INSTANCIA_ATUAL
    global CANVAS_GANTT, MELHOR_MAKESPAN_ATUAL, TEMPO_INICIO_BATERIA, HISTORICO_DATA, FILA_BOTOES_PENDENTES
    global CANVAS_GLOBAL, AX_GLOBAL, LINHA_GLOBAL, AX_GANTT, MONOTONIC_FILTER
    global PAUSE_BUTTON_GLOBAL, SAVE_BUTTON_GLOBAL
    global TEMPO_FINAL_CACHE 

    if ESCRITOR_TERMINAL_GLOBAL is None: return

    if START_BUTTON_GLOBAL and not START_BUTTON_GLOBAL.winfo_exists():
        return

    tipo_status = dados.get("status")
    texto_log = dados.get("message", "")
    nome_pacote = dados.get("instancia") 
    
    COR_NEUTRA = "#333333"
    COR_STOP = "#C0392B" 

    if tipo_status == "running":
        if nome_pacote: NOME_INSTANCIA_ATUAL = nome_pacote
        MELHOR_MAKESPAN_ATUAL = float('inf'); TEMPO_INICIO_BATERIA = time.time(); DADOS_X.clear(); DADOS_Y.clear()
        
        if MONOTONIC_FILTER: MONOTONIC_FILTER.reset()
            
        ESCRITOR_TERMINAL_GLOBAL.write(f"{texto_log}\n")
        
        if START_BUTTON_GLOBAL:
            START_BUTTON_GLOBAL.configure(text="STOP EXECUTION", fg_color=COR_STOP, state="normal")
        if PAUSE_BUTTON_GLOBAL:
            PAUSE_BUTTON_GLOBAL.configure(state="normal")
        
        if CANVAS_GLOBAL:
            LINHA_GLOBAL.set_data([], [])
            AX_GLOBAL.set_title(f"{NOME_INSTANCIA_ATUAL}...", fontsize=10, color="white")
            AX_GLOBAL.set_xlim(auto=True); AX_GLOBAL.set_ylim(auto=True); AX_GLOBAL.relim(); AX_GLOBAL.autoscale_view(); 
            CANVAS_GLOBAL.draw_idle() # <--- AQUI (Tire o .draw())
        if AX_GANTT: 
            AX_GANTT.clear()
            CANVAS_GANTT.draw_idle()

    elif tipo_status == "update":
        makespan = dados.get("makespan"); gantt_data = dados.get("gantt_data")
        if nome_pacote == NOME_INSTANCIA_ATUAL:
            if makespan <= MELHOR_MAKESPAN_ATUAL:
                time_to_best = dados.get("time_to_best")
                if time_to_best is None: time_to_best = time.time() - TEMPO_INICIO_BATERIA
                time_to_best = abs(float(time_to_best))
                nome_agente = dados.get("agent", "RKO Parallel")
                msg_final = f"[{nome_agente}] NEW BEST: {makespan:.4f} - Time: {time_to_best:.2f}s\n"
                if MONOTONIC_FILTER: MONOTONIC_FILTER.print_if_better(msg_final, makespan)
                if makespan < MELHOR_MAKESPAN_ATUAL:
                    MELHOR_MAKESPAN_ATUAL = makespan
                    DADOS_X.append(time_to_best); DADOS_Y.append(makespan) 
                    if CANVAS_GLOBAL: 
                        LINHA_GLOBAL.set_data(DADOS_X, DADOS_Y)
                        AX_GLOBAL.set_title(f"Instance: {NOME_INSTANCIA_ATUAL}  |  Best: {MELHOR_MAKESPAN_ATUAL}  |  Elapsed Time: {time_to_best:.2f}s", fontsize=10, color="#00FF00", fontweight="bold")
                        AX_GLOBAL.relim(); AX_GLOBAL.autoscale_view(); CANVAS_GLOBAL.draw_idle()
                if gantt_data and CANVAS_GANTT: CANVAS_GANTT.get_tk_widget().after(0, lambda: atualizar_desenho_gantt(gantt_data, nome_pacote, time_to_best))
    
    elif tipo_status == "final_plateau":
        # Guarda o tempo, mas deixa o trabalho pesado para o instancia_concluida garantir a consistência
        final_time = float(dados.get("final_time", 0))
        TEMPO_FINAL_CACHE = final_time

    elif tipo_status == "paused":
        ESCRITOR_TERMINAL_GLOBAL.write(f"{texto_log}\n")
        if PAUSE_BUTTON_GLOBAL and hasattr(PAUSE_BUTTON_GLOBAL, 'icons'):
            PAUSE_BUTTON_GLOBAL.configure(text="RESUME", state="normal", image=PAUSE_BUTTON_GLOBAL.icons["resume"], fg_color=COR_NEUTRA, text_color="white")
        if SAVE_BUTTON_GLOBAL: SAVE_BUTTON_GLOBAL.configure(state="normal", fg_color=COR_NEUTRA)
        if START_BUTTON_GLOBAL: START_BUTTON_GLOBAL.configure(state="normal") 

    elif tipo_status == "resumed":
        ESCRITOR_TERMINAL_GLOBAL.write(f"{texto_log}\n")
        if PAUSE_BUTTON_GLOBAL and hasattr(PAUSE_BUTTON_GLOBAL, 'icons'):
            PAUSE_BUTTON_GLOBAL.configure(text="PAUSE", state="normal", image=PAUSE_BUTTON_GLOBAL.icons["pause"], fg_color=COR_NEUTRA, text_color="white")
        if SAVE_BUTTON_GLOBAL: SAVE_BUTTON_GLOBAL.configure(state="disabled")
        if START_BUTTON_GLOBAL: 
            START_BUTTON_GLOBAL.configure(text="STOP EXECUTION", fg_color=COR_STOP, state="normal") 

    elif tipo_status == "instancia_concluida":
        nome_base = dados.get("instancia")
        gantt_final = dados.get("gantt_data")
        makespan_final = dados.get("makespan")

        if nome_base == NOME_INSTANCIA_ATUAL:
            
            # 1. CAPTURA O TEMPO "REAL" DA ÚLTIMA MELHORIA (Antes de criar o platô)
            tempo_to_best = DADOS_X[-1] if DADOS_X else 0.0

            # 2. LÓGICA DO PLATÔ (Adiciona a linha reta até o fim do tempo limite)
            tempo_limite = TEMPO_FINAL_CACHE if 'TEMPO_FINAL_CACHE' in globals() and TEMPO_FINAL_CACHE > 0 else 0
            
            # Se o gráfico parou antes do tempo limite (ex: achou em 15s, mas rodou até 60s)
            if DADOS_X and tempo_limite > DADOS_X[-1]:
                 DADOS_X.append(tempo_limite)
                 DADOS_Y.append(makespan_final)
                 
                 # Atualiza o desenho da linha
                 if CANVAS_GLOBAL and LINHA_GLOBAL:
                     LINHA_GLOBAL.set_data(DADOS_X, DADOS_Y)
                     AX_GLOBAL.set_xlim(left=0, right=tempo_limite * 1.02)
                     if DADOS_Y:
                        min_y, max_y = min(DADOS_Y), max(DADOS_Y)
                        margem = (max_y - min_y) * 0.1 if max_y != min_y else 1
                        AX_GLOBAL.set_ylim(bottom=max(0, min_y - margem), top=max_y + margem)
                     # --- CORRIGIDO: draw_idle() no platô ---
                     CANVAS_GLOBAL.draw_idle() 
            
            # 3. PREPARA DADOS FINAIS (Com o platô incluído para o histórico visual)
            eixo_x_final = list(DADOS_X) if DADOS_X else []
            eixo_y_final = list(DADOS_Y) if DADOS_Y else []
            
            # 4. ATUALIZA O TÍTULO (Usando o tempo_to_best capturado no passo 1)
            if CANVAS_GLOBAL:
                titulo_final = f"Instance: {nome_base}  |  Best: {makespan_final}  |  Time to Best: {tempo_to_best:.2f}s"
                AX_GLOBAL.set_title(titulo_final, fontsize=10, color="#00FF00", fontweight="bold")
                CANVAS_GLOBAL.draw_idle()

        # =====================================================================
        # --- 1º PASSO: SALVA NO HISTÓRICO (MEMÓRIA) ---
        # =====================================================================
        decoder_usado = dados.get("decoder", "Dec")
        agentes_usados = dados.get("agentes", ["Agentes"]) 
        str_agentes = "-".join(agentes_usados) if isinstance(agentes_usados, list) else str(agentes_usados)
        hora_termino = time.strftime("%d/%m/%y %H:%M:%S")
        
        chave_unica = f"{nome_base} [{decoder_usado}] ({str_agentes}) @{hora_termino}"
        
        if nome_base:
            HISTORICO_DATA[chave_unica] = {
                'x': eixo_x_final, 'y': eixo_y_final, 'gantt': gantt_final,
                'meta_nome': nome_base, 'meta_decoder': decoder_usado, 
                'meta_agentes': str_agentes, 'meta_hora': hora_termino,
                'meta_setup_range': dados.get("meta_setup_range", "N/A") 
            }
            if chave_unica not in FILA_BOTOES_PENDENTES: FILA_BOTOES_PENDENTES.append(chave_unica)

    elif tipo_status == "finished": 
        ESCRITOR_TERMINAL_GLOBAL.write(f"\n{'='*40}\n{texto_log}\n{'='*40}\n")
        try: START_BUTTON_GLOBAL.resetar_estado()
        except: pass
        # Habilita salvar após parar manualmente
        if SAVE_BUTTON_GLOBAL: SAVE_BUTTON_GLOBAL.configure(state="normal", fg_color=COR_NEUTRA)

    elif tipo_status == "error": 
        ESCRITOR_TERMINAL_GLOBAL.write(f"ERRO: {texto_log}\n")
        try: START_BUTTON_GLOBAL.resetar_estado()
        except: pass   
        # Habilita salvar mesmo com erro (para preservar o que rodou antes)
        if SAVE_BUTTON_GLOBAL: SAVE_BUTTON_GLOBAL.configure(state="normal", fg_color=COR_NEUTRA)

    elif tipo_status == "completed_all":
        ESCRITOR_TERMINAL_GLOBAL.write(f"\n>>> {texto_log} <<<\n")
        try: START_BUTTON_GLOBAL.resetar_estado()
        except: pass
        # Habilita salvar após terminar tudo com sucesso
        if SAVE_BUTTON_GLOBAL: SAVE_BUTTON_GLOBAL.configure(state="normal", fg_color=COR_NEUTRA)

    elif tipo_status == "log": 
        ESCRITOR_TERMINAL_GLOBAL.write(f"{texto_log}\n")
        
        # Ouve ativamente a linha de finalização para engatilhar o Dump no momento exato
        if "==================================================" in texto_log:
            try:
                # Dispara síncrono. O backend fica bloqueado esperando salvar.
                msg_sucesso = fazer_dump_automatico()
                if msg_sucesso:
                    ESCRITOR_TERMINAL_GLOBAL.write(msg_sucesso)
            except Exception as e:
                ESCRITOR_TERMINAL_GLOBAL.write(f">>> [Auto-Save Error] {e}\n\n")

def configurar_aba_parametros(aba):
    global VAR_PERIODIC_DUMP
    import customtkinter as ctk
    
    # SEMPRE RECRIAR A VARIÁVEL PARA NÃO DAR CONFLITO DE JANELA MORTA 
    VAR_PERIODIC_DUMP = ctk.BooleanVar(value=False)

    aba.widgets_armazenados = {} 
    
    aba.grid_columnconfigure(0, minsize=20)
    aba.grid_columnconfigure(1, weight=0)
    aba.grid_columnconfigure(2, weight=0)
    aba.grid_columnconfigure(3, weight=0)
    aba.grid_columnconfigure(4, weight=0)   # --- NOVA COLUNA DUMP ---
    aba.grid_columnconfigure(5, weight=1)

    rotulo_titulo = ctk.CTkLabel(aba, text="HYPER-PARAMETERS", text_color=CORES["destaque"], font=FONTES["titulo"])
    rotulo_titulo.grid(row=0, column=1, sticky="w", columnspan=4, pady=(15, 15), padx=0)
    
    rotulo_decoder = ctk.CTkLabel(aba, text="SELECT DECODER", font=FONTES["subtitulo"], text_color=CORES["texto"])
    rotulo_decoder.grid(row=1, column=1, sticky="w", padx=0, pady=(0, 2))
    combo_decoder = ctk.CTkComboBox(
        aba, values=["CHEAPEST", "M3LAW", "ECT", "INCREMENTAL", "KSTS"], 
        border_color=CORES["primaria"], border_width=2, corner_radius=0, width=180,
        dropdown_fg_color="lavender", dropdown_text_color=CORES["texto_escuro"], dropdown_hover_color=CORES["destaque"]
    )
    combo_decoder.grid(row=2, column=1, sticky="w", padx=0, pady=(0, 5))
    aba.widgets_armazenados["decoder"] = combo_decoder 
    
    rotulo_tempo = ctk.CTkLabel(aba, text="TIME LIMIT (S)", font=FONTES["subtitulo"], text_color=CORES["texto"])
    rotulo_tempo.grid(row=1, column=2, sticky="w", padx=30, pady=(0, 2)) 
    entrada_tempo = ctk.CTkEntry(aba, width=100, corner_radius=0, border_color=CORES["primaria"], border_width=2)
    entrada_tempo.insert(0,"60")
    entrada_tempo.grid(row=2, column=2, sticky="w", padx=30, pady=(0, 5))
    aba.widgets_armazenados["time_limit"] = entrada_tempo 

    rotulo_execucoes = ctk.CTkLabel(aba, text="EXECUTION TIMES", font=FONTES["subtitulo"], text_color=CORES["texto"])
    rotulo_execucoes.grid(row=1, column=3, sticky="w", padx=30, pady=(0, 2))
    entrada_execucoes = ctk.CTkEntry(aba, width=100, corner_radius=0, border_color=CORES["primaria"], border_width=2)
    entrada_execucoes.insert(0, "1")
    entrada_execucoes.grid(row=2, column=3, sticky="w", padx=30, pady=(0, 5))
    aba.widgets_armazenados["execution_times"] = entrada_execucoes

    # =========================================================================
    # --- PERIODIC DUMP COM PREFIXO CUSTOMIZADO ---
    rotulo_dump = ctk.CTkLabel(aba, text="AUTO-SAVE", font=FONTES["subtitulo"], text_color=CORES["texto"])
    rotulo_dump.grid(row=1, column=4, sticky="w", padx=30, pady=(0, 2))
    
    frame_dump_opts = ctk.CTkFrame(aba, fg_color="transparent")
    frame_dump_opts.grid(row=2, column=4, sticky="w", padx=30, pady=(0, 5))
    
    def atualizar_estado_dump():
        global AUTO_DUMP_ATIVO
        if VAR_PERIODIC_DUMP is not None:
            AUTO_DUMP_ATIVO = bool(VAR_PERIODIC_DUMP.get())

    chk_dump = ctk.CTkCheckBox(
        frame_dump_opts, 
        text=" ", 
        font=("Roboto", 12),
        variable=VAR_PERIODIC_DUMP,
        fg_color=CORES["primaria"],
        hover_color="#555555",
        command=atualizar_estado_dump
    )
    chk_dump.pack(side="left")

    # Garante a criação da variável global para o backend ler depois
    global VAR_DUMP_PREFIX
    if 'VAR_DUMP_PREFIX' not in globals() or VAR_DUMP_PREFIX is None:
        VAR_DUMP_PREFIX = ctk.StringVar()

    # 1. CRIAMOS A ENTRY SEM TEXTVARIABLE PARA O PLACEHOLDER FUNCIONAR
    entry_prefix = ctk.CTkEntry(
        frame_dump_opts,
        width=180,
        placeholder_text="Prefix (max 30 chars)",
        placeholder_text_color="#D1CECE",
        font=("Roboto", 12),
        fg_color="#2b2b2b",
        border_width=1,
        border_color=CORES["primaria"],
        corner_radius=0
    )
    entry_prefix.pack(side="left", padx=(15, 0))

    # 2. FUNÇÃO QUE LIMITA OS CARACTERES E ATUALIZA A VARIÁVEL SILENCIOSAMENTE
    def ao_digitar_prefixo(event):
        texto = entry_prefix.get()
        if len(texto) > 30:
            # Corta o excesso diretamente no widget
            entry_prefix.delete(30, "end") 
            texto = texto[:30]
            
        # Alimenta a variável global para que o backend continue conseguindo ler
        VAR_DUMP_PREFIX.set(texto)

    # Liga a função à digitação do teclado, resolvendo todos os problemas de foco
    entry_prefix.bind("<KeyRelease>", ao_digitar_prefixo)

    # Preenchimento de segurança: Se já houver algo salvo na variável global, injeta na entry
    valor_salvo = VAR_DUMP_PREFIX.get()
    if valor_salvo:
        entry_prefix.insert(0, valor_salvo)

    aba.widgets_armazenados["periodic_dump"] = VAR_PERIODIC_DUMP
    aba.widgets_armazenados["dump_prefix"] = entry_prefix 
    
    atualizar_estado_dump()
    # =========================================================================

    frm_sep = ctk.CTkFrame(aba, height=2, fg_color=CORES["borda"])
    frm_sep.grid(row=3, column=0, columnspan=10, sticky="ew", pady=30, padx=20)

    cache = carregar_cache_caminhos()
    def sel_dir(w):
        p = filedialog.askdirectory(parent=aba)
        if p: 
            w.delete(0, "end")
            w.insert(0, p)
            
    ctk.CTkLabel(aba, text="IO CONFIGURATION", text_color=CORES["destaque"], font=FONTES["titulo"]).grid(row=4, column=1, columnspan=4, sticky="w", pady=(0, 20), padx=0)
    try: img = ctk.CTkImage(Image.open(resource_path("assets/dots.png")), size=(16, 16))
    except: img = None 
        
    lista_campos = [("output_path", "Output Path"), ("instance_path", "Instance Folder Path"), ("gantt_path", "Gantt Chart Path")]
    frame_io = ctk.CTkFrame(aba, fg_color="transparent")
    frame_io.grid(row=5, column=1, columnspan=5, sticky="w")
    frame_io.grid_columnconfigure(0, minsize=200) 
    frame_io.grid_columnconfigure(1, weight=1)    

    for i, (k, txt) in enumerate(lista_campos):
        ctk.CTkLabel(frame_io, text=txt, font=FONTES["subtitulo"]).grid(row=i, column=0, sticky="w", pady=8, padx=(0, 10))
        ent = ctk.CTkEntry(frame_io, border_color=CORES["primaria"], border_width=2, width=450)
        ent.grid(row=i, column=1, sticky="w", pady=8)
        valor_cache = cache.get(k, "")
        if valor_cache: ent.insert(0, valor_cache)
        aba.widgets_armazenados[k] = ent 
        ctk.CTkButton(frame_io, text="" if img else "...", width=30, image=img, 
                      fg_color="transparent", hover_color=CORES["destaque"], 
                      command=lambda e=ent: sel_dir(e)).grid(row=i, column=2, sticky="w", padx=5, pady=8)

def configurar_aba_agentes(aba):
    # 1. Reseta a lista global de referências (CRUCIAL para a lógica de soma de workers)
    global LISTA_REF_WORKERS
    LISTA_REF_WORKERS = [] 

    area_rolagem = ctk.CTkScrollableFrame(aba, width=1160, height=860, fg_color="transparent")
    area_rolagem.grid(row=0, column=0, columnspan=10, rowspan=10, padx=10, pady=10, sticky="nsew")
    for i in range(3): area_rolagem.grid_columnconfigure(i, weight=1, minsize=400)
    aba.parametros_agentes = {} 
    
    ctk.CTkLabel(area_rolagem, text="AGENTS PARAMETERS", font=FONTES["titulo"], text_color=CORES["destaque"]).grid(row=0, column=0, columnspan=3, sticky="ew", padx=12, pady=(8,12))
    
    configuracao_agentes = {
        "BRKGA": {"linha": 1, "coluna": 0, "titulo": "BIASED RANDOM KEY GENETIC ALGORITHM (BRKGA)", "campos": [("Population", "100"), ("Elite set", "0.20"), ("Mutant set", "0.10"), ("Inheritance Prob", "0.70")]},
        "SA":    {"linha": 1, "coluna": 1, "titulo": "SIMULATED ANNEALING (SA)", "campos": [("Iterations", "50"), ("alphaSA", "0.99"), ("betaMin", "0.05"), ("betaMax", "0.25"), ("Initial Temperature", "10000")]},
        "PSO":   {"linha": 2, "coluna": 0, "titulo": "PARTICLE SWARM OPTIMIZATION (PSO)", "campos": [("PSize", "100"), ("c1", "2.05"), ("c2", "2.05"), ("w", "0.73")]},
        "GA":    {"linha": 2, "coluna": 1, "titulo": "GENETIC ALGORITHM (GA)", "campos": [("Population", "100"), ("CrosProb", "0.98"), ("MutProb", "0.005")]},
        "LNS":   {"linha": 1, "coluna": 2, "titulo": "LARGE NEIGHBORHOOD SEARCH (LNS)", "campos": [("betaMin", "0.10"), ("betaMax", "0.30"), ("T0", "1000"), ("alphaLNS", "0.95")]},
        "VNS":   {"linha": 2, "coluna": 2, "titulo": "VARIABLE NEIGHBORHOOD SEARCH (VNS)", "campos": [("kMax", "5"), ("betaMin", "0.05")]},
        "ILS":   {"linha": 3, "coluna": 2, "titulo": "ITERATED LOCAL SEARCH (ILS)", "campos": [("betaMin", "0.1"), ("betaMax", "0.20")]},
    }

    # --- LÓGICA INTELIGENTE DE ATIVAÇÃO ---
    nucleos_reais = os.cpu_count() or 4
    
    # Ordem de prioridade: quais ativar primeiro se faltar núcleo
    prioridade = ["BRKGA", "PSO", "SA", "GA", "LNS", "VNS", "ILS"]
    
    # Define quais nomes devem estar True
    agentes_para_ativar = set(prioridade[:nucleos_reais])
    # --------------------------------------

    for nome, config in configuracao_agentes.items():
        # Injeta a configuração de ativação baseada no hardware
        if nome in agentes_para_ativar:
            config["padrao_ativado"] = True
        else:
            config["padrao_ativado"] = False

        aba.parametros_agentes[nome] = criar_cartao_agente(area_rolagem, config)

def criar_cartao_agente(conteiner_pai, config):
    # Limpa referências mortas
    global LISTA_REF_WORKERS
    LISTA_REF_WORKERS = [ref for ref in LISTA_REF_WORKERS if ref[1].winfo_exists()]
    
    frame = ctk.CTkFrame(conteiner_pai, fg_color=CORES["fundo_cartao"], width=LARGURA_CARTAO_AGENTE, height=ALTURA_CARTAO_AGENTE, border_width=1, border_color=CORES["borda"])
    frame.grid(row=config["linha"], column=config["coluna"], padx=8, pady=8, sticky="n")
    frame.grid_propagate(False) 
    
    ctk.CTkLabel(frame, text=config["titulo"], font=FONTES["corpo_negrito"], text_color=CORES["destaque"]).grid(row=0, column=0, sticky="w", padx=10, pady=(8,4))
    
    # Estado inicial
    estado_inicial = config.get("padrao_ativado", True)
    var_chk = tk.BooleanVar(value=estado_inicial)
    
    # --- CONTROLE DE WORKERS ---
    frm_workers = ctk.CTkFrame(frame, fg_color="transparent")
    frm_workers.grid(row=1, column=0, columnspan=2, sticky="w", padx=10, pady=2)
    
    ctk.CTkLabel(frm_workers, text="Workers:", font=FONTES["pequena"], text_color="gray").pack(side="left", padx=(0,5))
    
    btn_minus = ctk.CTkButton(frm_workers, text="-", width=25, height=20, fg_color="#333333", font=("Arial", 12, "bold"))
    btn_minus.pack(side="left")
    
    ent_workers = ctk.CTkEntry(frm_workers, width=40, height=20, font=("Arial", 12), justify="center")
    ent_workers.insert(0, "1")
    ent_workers.pack(side="left", padx=2)
    
    btn_plus = ctk.CTkButton(frm_workers, text="+", width=25, height=20, fg_color="#333333", font=("Arial", 12, "bold"))
    btn_plus.pack(side="left")
    
    max_cpu = os.cpu_count() or 4
    ctk.CTkLabel(frm_workers, text=f"(Max: {max_cpu})", font=("Arial", 9), text_color="gray").pack(side="left", padx=5)

    LISTA_REF_WORKERS.append((var_chk, ent_workers))

    # Variável para controlar o timer do pisca (evita bug de cor travada)
    id_flash = None

    # --- LÓGICA DE TRAVAMENTO DO CHECKBOX ---
    def validar_ativacao():
        nonlocal id_flash # Permite modificar a variável externa
        
        if var_chk.get():
            total_ocupado = 0
            for r_chk, r_ent in LISTA_REF_WORKERS:
                if r_ent.winfo_exists() and r_ent != ent_workers and r_chk.get():
                    try: total_ocupado += int(r_ent.get())
                    except: pass
            
            if total_ocupado >= max_cpu:
                var_chk.set(False) 
                
                # --- CORREÇÃO DO PISCA-PISCA ---
                # 1. Se já tiver um agendamento pendente, cancela ele
                if id_flash is not None:
                    try: frame.after_cancel(id_flash)
                    except: pass
                
                # 2. Define cor vermelha
                frame.configure(fg_color="#521818") 
                
                # 3. Define função de restauração para a cor FIXA do tema
                def restaurar():
                    frame.configure(fg_color=CORES["fundo_cartao"])
                
                # 4. Agenda a restauração e guarda o ID
                id_flash = frame.after(300, restaurar)
                
                toggle_state() 
                return

        toggle_state()

    chk_enable = ctk.CTkCheckBox(frame, text="", variable=var_chk, width=20, command=validar_ativacao)
    chk_enable.grid(row=0, column=1, sticky="e", padx=10, pady=(8,4))

    # --- LÓGICA +/- ---
    def alterar_workers(delta):
        if not var_chk.get(): return

        try: val_atual = int(ent_workers.get())
        except: val_atual = 1

        if delta < 0:
            novo = max(1, val_atual + delta)
            ent_workers.delete(0, "end"); ent_workers.insert(0, str(novo))
            return

        if delta > 0:
            total_usados = 0
            for r_chk, r_ent in LISTA_REF_WORKERS:
                if r_ent.winfo_exists() and r_ent != ent_workers and r_chk.get():
                    try: total_usados += int(r_ent.get())
                    except: pass
            
            saldo = max_cpu - total_usados
            novo = val_atual + delta
            
            if novo <= saldo and novo <= max_cpu:
                ent_workers.delete(0, "end"); ent_workers.insert(0, str(novo))
            else:
                ent_workers.configure(text_color="#FF5555")
                frame.after(200, lambda: ent_workers.configure(text_color="white"))

    btn_minus.configure(command=lambda: alterar_workers(-1))
    btn_plus.configure(command=lambda: alterar_workers(1))
    
    def toggle_state(*args):
        st = "normal" if var_chk.get() else "disabled"
        cor_txt = "white" if var_chk.get() else "gray"
        
        ent_workers.configure(state=st, text_color=cor_txt)
        btn_minus.configure(state=st)
        btn_plus.configure(state=st)
        
        for k, w in widgets.items():
            if isinstance(w, ctk.CTkEntry) and k != "workers_entry": 
                w.configure(state=st, text_color=cor_txt)
            
    widgets = {"frame_conteiner": frame, "variavel_controle": var_chk, "workers_entry": ent_workers}
    
    row_start = 2
    for i, (txt, val) in enumerate(config["campos"], start=row_start):
        ctk.CTkLabel(frame, text=txt, anchor="w", font=FONTES["pequena"]).grid(row=i, column=0, sticky="w", padx=90, pady=4)
        ent = ctk.CTkEntry(frame, width=70, height=22); ent.insert(0, val)
        ent.grid(row=i, column=0, sticky="w", padx=10 if config.get("coluna",0)!=0 else 0, pady=4)
        widgets[txt] = ent
        
    toggle_state()
    return widgets

def configurar_aba_entrada_saida(aba):
    cache = carregar_cache_caminhos()

    aba.widgets_armazenados = {} 
    
    def sel_dir(w):
        p = filedialog.askdirectory(parent=aba)
        if p: 
            w.delete(0, "end")
            w.insert(0, p)
            
    ctk.CTkLabel(aba, text="IO CONFIGURATION", text_color=CORES["destaque"], font=FONTES["titulo"]).grid(row=0, column=1, columnspan=10, sticky="w", pady=(8,12), padx=70)
    
    try: img = ctk.CTkImage(Image.open(resource_path("assets/dots.png")), size=(16, 16))
    except: img = None 
        
    lista_campos = [
        ("output_path", "Output Path", 1), 
        ("instance_path", "Instance Folder Path", 2), 
        ("gantt_path", "Gantt Chart Path", 3)
    ]

    for k, txt, row in lista_campos:
        fr = ctk.CTkFrame(aba, fg_color="transparent")
        fr.grid(row=row, column=0, padx=8, pady=8, sticky="n")
        
        ctk.CTkLabel(fr, text=txt, font=FONTES["subtitulo"]).grid(row=0, column=0, padx=8, sticky="w")
        
        ent = ctk.CTkEntry(fr, border_color=CORES["primaria"], border_width=2, width=350)
        ent.grid(row=1, column=0, padx=10, pady=3)
        
        valor_cache = cache.get(k, "")
        if valor_cache:
            ent.insert(0, valor_cache)

        aba.widgets_armazenados[k] = ent 
        
        ctk.CTkButton(fr, text="" if img else "...", width=30, image=img, fg_color="transparent", hover_color=CORES["destaque"], command=lambda e=ent: sel_dir(e)).grid(row=1, column=1, pady=10)

def carregar_dados_interface(dados, aba_p, aba_a): # Removido aba_io
    """Preenche widgets com dados do dump."""
    try:
        # Carrega Params e IO (ambos estão em aba_p agora)
        if hasattr(aba_p, 'widgets_armazenados'):
            # Mescla as fontes de dados para iterar uma vez
            fontes = []
            if "hyper_parameters" in dados: fontes.append(dados["hyper_parameters"])
            if "io" in dados: fontes.append(dados["io"])
            
            for fonte in fontes:
                for k, v in fonte.items():
                    w = aba_p.widgets_armazenados.get(k)
                    if w:
                        if isinstance(w, ctk.CTkComboBox): w.set(v)
                        elif isinstance(w, ctk.CTkEntry): w.delete(0, "end"); w.insert(0, str(v))
        
        # --- CARREGAR AGENTES E WORKERS ---
        if "agents" in dados and hasattr(aba_a, 'parametros_agentes'):
            for _, widgets in aba_a.parametros_agentes.items():
                widgets["variavel_controle"].set(False)
            
            for nome_ag, valor in dados["agents"].items():
                widgets = aba_a.parametros_agentes.get(nome_ag)
                if widgets:
                    if isinstance(valor, int) and valor > 0:
                        widgets["variavel_controle"].set(True)
                        if "workers_entry" in widgets:
                            widgets["workers_entry"].delete(0, "end")
                            widgets["workers_entry"].insert(0, str(valor))
                    elif isinstance(valor, dict):
                        widgets["variavel_controle"].set(True)
                        for kp, vp in valor.items():
                            ent = widgets.get(kp)
                            if ent and isinstance(ent, ctk.CTkEntry):
                                ent.delete(0, "end"); ent.insert(0, str(vp))
    except Exception as e: print(f"Erro popular UI: {e}")

def configurar_aba_execucao(aba, aba_p, aba_a):
    global ESCRITOR_TERMINAL_GLOBAL, START_BUTTON_GLOBAL, PAUSE_BUTTON_GLOBAL, SAVE_BUTTON_GLOBAL, MONOTONIC_FILTER
    
    def carregar_icone(nome_arquivo):
        try:
            caminho = resource_path(f"assets/{nome_arquivo}")
            img = Image.open(caminho)
            return ctk.CTkImage(light_image=img, dark_image=img, size=(20, 20))
        except Exception as e: return None

    aba.icons = {
        "rocket": carregar_icone("rocket.png"), "pause":  carregar_icone("pause.png"),
        "resume": carregar_icone("play.png"), "save":   carregar_icone("save.png"),
        "load":   carregar_icone("folder.png")
    }

    controles = {"paused": False, "running": False}
    frm_botoes = ctk.CTkFrame(aba, fg_color="transparent")
    frm_botoes.grid(row=1, column=0, columnspan=10, pady=10, padx=20, sticky="ew")
    for i in range(4): frm_botoes.grid_columnconfigure(i, weight=1)

    COR_NEUTRA = "#333333"
    COR_NEUTRA_HOVER = "#444444"
    COR_START = "#77198f"
    COR_STOP = "#C0392B"

    def travar_campos_estruturais(bloquear: bool):
        estado = "disabled" if bloquear else "normal"
        fg_c = "#101010" if bloquear else "#343638" 
        txt_c = "#555555" if bloquear else "#FFFFFF"
        brd_c = "#222222" if bloquear else CORES["primaria"]

        def _aplicar(widget):
            if widget:
                widget.configure(state=estado, fg_color=fg_c, text_color=txt_c, border_color=brd_c)

        if hasattr(aba_p, 'widgets_armazenados'):
            _aplicar(aba_p.widgets_armazenados.get("execution_times"))
            _aplicar(aba_p.widgets_armazenados.get("instance_path"))

    def alternar_start_stop():
        if rko_gui_start is None: return
        if not controles["running"]:
            # INICIAR
            controles["running"] = True; controles["paused"] = False
            travar_campos_estruturais(True)
            
            btn_start.configure(text="STOP EXECUTION", fg_color=COR_STOP, hover_color="#E74C3C", state="normal")
            btn_pause.configure(state="normal", text="PAUSE", image=aba.icons["pause"], fg_color=COR_NEUTRA, hover_color=COR_NEUTRA_HOVER)
            btn_save.configure(state="disabled"); btn_load.configure(state="disabled")
            
            try: term.configure(state="normal"); term.delete("1.0", "end"); term.configure(state="disabled")
            except: pass

            data = coletar_dados_interface(aba_p, aba_a)
            dados_io = data.get("io", {})
            salvar_cache_caminhos(dados_io.get("instance_path", ""), dados_io.get("output_path", ""), dados_io.get("gantt_path", ""))

            rko_gui_start.iniciar_resolucao(data, manipulador_retorno_interface)
        else:
            # PARAR
            rko_gui_start.solicitar_parada()
            btn_start.configure(text="STOPPING...", state="disabled", fg_color="#555555")
            btn_pause.configure(state="disabled")
            frm_botoes.update()

    def alternar_pause():
        if not controles["running"]: return
        
        if not controles["paused"]:
            btn_pause.configure(text="PAUSING...", state="disabled", fg_color=COR_NEUTRA, image=None) 
            btn_save.configure(state="disabled") 
            btn_start.configure(state="normal") 
            
            aba.update_idletasks()
            
            controles["paused"] = True
            if hasattr(rko_gui_start, 'alternar_pausa'):
                rko_gui_start.alternar_pausa(True)
        else:
            btn_pause.configure(text="RESUMING...", state="disabled", fg_color=COR_NEUTRA, image=None)
            aba.update_idletasks()
            
            novos_dados = coletar_dados_interface(aba_p, aba_a)
            if hasattr(rko_gui_start, 'atualizar_parametros_runtime'):
                rko_gui_start.atualizar_parametros_runtime(novos_dados)

            controles["paused"] = False
            if hasattr(rko_gui_start, 'alternar_pausa'):
                rko_gui_start.alternar_pausa(False)
            
            btn_save.configure(state="disabled")
            btn_start.configure(state="normal")

    def acao_salvar_experimento():
        janela_pai = aba.winfo_toplevel()
        esta_rodando = (START_BUTTON_GLOBAL.cget("text") == "STOP EXECUTION")
        esta_pausado = controles.get("paused", False)
    
        if esta_rodando and not esta_pausado:
            messagebox.showwarning("Warning", "You must PAUSE the experiment before saving while it's running.\n(Or wait for it to finish)", parent=janela_pai)
            return
    
        # --- FIX: SUPORTE PARA O NOVO .pkl E O ANTIGO .rko ---
        caminho = filedialog.asksaveasfilename(
            parent=janela_pai, 
            defaultextension=".pkl", 
            filetypes=[("RKO Data", "*.pkl"), ("Legacy RKO Exp", "*.rko"), ("All Files", "*.*")]
        )
        # -----------------------------------------------------
        if not caminho: return
    
        try:
            btn_save.configure(text="SAVING...", state="disabled"); aba.update_idletasks()
            
            global SETS_CRIADOS, SETS_DESCRICOES
            estado_ui = {
                "historico": HISTORICO_DATA, 
                "dados_grafico_x": DADOS_X, 
                "dados_grafico_y": DADOS_Y, 
                "melhor": MELHOR_MAKESPAN_ATUAL, 
                "instancia": NOME_INSTANCIA_ATUAL,
                "sets_criados": SETS_CRIADOS if 'SETS_CRIADOS' in globals() else {},
                "sets_descricoes": SETS_DESCRICOES if 'SETS_DESCRICOES' in globals() else {}
            }
            
            estado_backend = rko_gui_start.obter_estado_checkpoint() if hasattr(rko_gui_start, 'obter_estado_checkpoint') else {}
            dados_visuais = coletar_dados_interface(aba_p, aba_a)
            estado_backend["params"] = dados_visuais 
    
            dump = {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "ui": estado_ui, "backend": estado_backend}
            with open(caminho, "wb") as f: pickle.dump(dump, f)
            
            ESCRITOR_TERMINAL_GLOBAL.write(f"\n>>> SAVED: {os.path.basename(caminho)}\n")
            messagebox.showinfo("Saved", "Experiment saved successfully!", parent=janela_pai)
            
        except Exception as e: 
            messagebox.showerror("Error", str(e), parent=janela_pai)
        finally: 
            btn_save.configure(text="SAVE EXP.", state="normal")
    
    def acao_carregar_experimento():
        if controles["running"]: return
        
        # --- FIX: CARREGA TANTO OS NOVOS .pkl QUANTO OS ANTIGOS .rko ---
        caminho = filedialog.askopenfilename(
            parent=aba, 
            filetypes=[("All RKO Files", "*.pkl *.rko"), ("RKO Data", "*.pkl"), ("Legacy RKO Exp", "*.rko"), ("All Files", "*.*")]
        )
        # ---------------------------------------------------------------
        if not caminho: return
        
        try:
            btn_load.configure(text="LOADING...", state="disabled")
            aba.update_idletasks()

            with open(caminho, "rb") as f: dump = pickle.load(f)
            
            if "backend" not in dump or "ui" not in dump: raise ValueError("Invalid file structure.")

            d_back = dump["backend"]
            fila_tarefas = d_back.get("fila_tarefas", [])
            if fila_tarefas and len(fila_tarefas) > 0:
                primeira_tarefa = fila_tarefas[0]
                if "inst_idx" not in primeira_tarefa or "inst_total" not in primeira_tarefa:
                    raise ValueError("Incompatible Version detected!")
            
            d_ui = dump["ui"]
            if "params" in d_back: 
                carregar_dados_interface(d_back["params"], aba_p, aba_a)
            
            global HISTORICO_DATA, DADOS_X, DADOS_Y, MELHOR_MAKESPAN_ATUAL, NOME_INSTANCIA_ATUAL, FILA_BOTOES_PENDENTES
            global SETS_CRIADOS, SETS_DESCRICOES
            
            HISTORICO_DATA = d_ui.get("historico", {})
            DADOS_X = d_ui.get("dados_grafico_x", [])
            DADOS_Y = d_ui.get("dados_grafico_y", [])
            MELHOR_MAKESPAN_ATUAL = d_ui.get("melhor", float('inf'))
            NOME_INSTANCIA_ATUAL = d_ui.get("instancia", "Resumed")
            FILA_BOTOES_PENDENTES = list(HISTORICO_DATA.keys())
            
            SETS_CRIADOS = d_ui.get("sets_criados", {}) 
            SETS_DESCRICOES = d_ui.get("sets_descricoes", {})
            
            try: 
                term.configure(state="normal"); term.delete("1.0", "end"); term.configure(state="disabled")
            except: pass
            
            ESCRITOR_TERMINAL_GLOBAL.write(f">>> LOADED: {d_ui.get('timestamp')}\n")
            ESCRITOR_TERMINAL_GLOBAL.write(f">>> SYSTEM PAUSED. Check params then RESUME.\n")
            
            controles["running"] = True
            controles["paused"] = True
            travar_campos_estruturais(True)
            
            btn_start.configure(text="STOP EXECUTION", fg_color=COR_STOP, state="normal")
            btn_pause.configure(state="normal", text="RESUME", image=aba.icons["resume"], fg_color=COR_NEUTRA, hover_color=COR_NEUTRA_HOVER)
            btn_save.configure(state="normal", fg_color=COR_NEUTRA) 
            btn_load.configure(state="disabled")
            
            aplicar_filtros_historico()

            if hasattr(rko_gui_start, 'restaurar_e_continuar'):
                rko_gui_start.restaurar_e_continuar(d_back, manipulador_retorno_interface, start_paused=True)
                
        except Exception as e:
            messagebox.showerror("Load Failed", f"Could not load checkpoint:\n{e}", parent=aba)
            btn_load.configure(text="LOAD EXP.", state="normal")
        finally: 
            if controles["running"]: btn_load.configure(state="disabled", text="LOAD EXP.")
            else: btn_load.configure(state="normal", text="LOAD EXP.")

    def resetar_botoes():
        controles["running"] = False; controles["paused"] = False
        travar_campos_estruturais(False)
        btn_start.configure(text="START SOLVER", image=aba.icons["rocket"], fg_color=COR_START, hover_color="#9c27b0", state="normal")
        btn_pause.configure(text="PAUSE", image=aba.icons["pause"], fg_color=COR_NEUTRA, state="disabled", text_color="white")
        btn_save.configure(state="disabled")
        btn_load.configure(state="normal")

    # BOTOES
    btn_start = ctk.CTkButton(frm_botoes, text='START SOLVER', image=aba.icons["rocket"], compound="right", command=alternar_start_stop, fg_color=COR_START, hover_color="#9c27b0", height=40)
    btn_start.grid(row=0, column=0, padx=5, sticky="ew")
    btn_pause = ctk.CTkButton(frm_botoes, text='PAUSE', image=aba.icons["pause"], compound="right", command=alternar_pause, state="disabled", fg_color=COR_NEUTRA, hover_color=COR_NEUTRA_HOVER, height=40)
    btn_pause.grid(row=0, column=1, padx=5, sticky="ew")
    btn_save = ctk.CTkButton(frm_botoes, text='SAVE EXP.', image=aba.icons["save"], compound="right", command=acao_salvar_experimento, state="disabled", fg_color=COR_NEUTRA, hover_color=COR_NEUTRA_HOVER, height=40)
    btn_save.grid(row=0, column=2, padx=5, sticky="ew")
    btn_load = ctk.CTkButton(frm_botoes, text='LOAD EXP.', image=aba.icons["load"], compound="right", command=acao_carregar_experimento, fg_color=COR_NEUTRA, hover_color=COR_NEUTRA_HOVER, height=40)
    btn_load.grid(row=0, column=3, padx=5, sticky="ew")

    term = ctk.CTkTextbox(aba, border_width=2, fg_color="black", text_color="#00FF00", border_color="#2D2D35", font=("Consolas", 13))
    term.grid(row=2, column=0, columnspan=10, rowspan=8, sticky="nsew", padx=45, pady=(0,45))
    term.configure(state="disabled")

    MONOTONIC_FILTER = MonotonicFilter(term)
    ESCRITOR_TERMINAL_GLOBAL = StdoutRedirector(MONOTONIC_FILTER)
    START_BUTTON_GLOBAL = btn_start; START_BUTTON_GLOBAL.resetar_estado = resetar_botoes
    PAUSE_BUTTON_GLOBAL = btn_pause; PAUSE_BUTTON_GLOBAL.icons = aba.icons
    SAVE_BUTTON_GLOBAL = btn_save
    sys.stdout = ESCRITOR_TERMINAL_GLOBAL

    # RESTAURAR O PRINT ORIGINAL SE A JANELA FECHAR 
    def ao_destruir_terminal(event):
        import sys
        if sys.stdout == ESCRITOR_TERMINAL_GLOBAL:
            sys.stdout = sys.__stdout__  # Devolve o print pro terminal do SO
            
    term.bind("<Destroy>", ao_destruir_terminal)

def coletar_dados_interface(aba_p, aba_a): # Removido aba_io
    data = {}
    
    # 1. Hyper-Parameters E IO (Agora estão juntos na aba_p)
    if hasattr(aba_p, 'widgets_armazenados'):
        # Separamos logicamente apenas para manter compatibilidade com o backend
        # O backend espera "hyper_parameters" e "io" separados
        
        # Lista de chaves que pertencem ao IO
        keys_io = ["output_path", "instance_path", "gantt_path"]
        
        params = {}
        io_data = {}
        
        for k, w in aba_p.widgets_armazenados.items():
            val = w.get()
            if k in keys_io:
                io_data[k] = val
            else:
                params[k] = val
                
        data["hyper_parameters"] = params
        data["io"] = io_data
    
    # 3. Agents 
    data["agents"] = {}
    if hasattr(aba_a, 'parametros_agentes'):
        for nome_agente, widgets in aba_a.parametros_agentes.items():
            if widgets["variavel_controle"].get():
                params_agente = {}
                try: qtd = int(widgets["workers_entry"].get())
                except: qtd = 1
                params_agente["workers"] = qtd
                for k_widget, w_entry in widgets.items():
                    if k_widget not in ["frame_conteiner", "variavel_controle", "workers_entry"]:
                        params_agente[k_widget] = w_entry.get()
                data["agents"][nome_agente] = params_agente
            else:
                data["agents"][nome_agente] = {"workers": 0}

    return data

def centralizar_janela(janela, w, h):
    ws = janela.winfo_screenwidth(); hs = janela.winfo_screenheight()
    x = (ws - w) // 2; y = (hs - h) // 2
    janela.geometry(f"{w}x{h}+{x}+{y}")

def criar_aba_base(pai):
    f = ctk.CTkFrame(pai, width=1200, height=900, border_width=5, border_color=CORES["borda"])
    for i in range(10): f.grid_rowconfigure(i, weight=1, minsize=20); f.grid_columnconfigure(i, weight=1, minsize=20)
    return f

def configurar_aba_analise(aba):
    """
    Prepara o terreno para a futura aba de Análise Estatística.
    """
    # Grid base
    aba.grid_rowconfigure(0, weight=1)
    aba.grid_columnconfigure(0, weight=1)
    
    # Placeholder provisório
    lbl = ctk.CTkLabel(aba, text="STATISTICAL ANALYSIS", font=("Roboto", 24, "bold"), text_color=CORES["destaque"])
    lbl.pack(pady=50)
    
    ctk.CTkLabel(aba, text="(To be developed...)", font=("Roboto", 14), text_color="gray").pack()

def configurar_interface(janela):
    global ABA_ANALISE_GLOBAL, FUNCAO_SHOW_TAB_GLOBAL # <--- ADICIONE ISTO
    
    # 1. Configuração do Grid Principal da Janela
    for i in range(10): 
        janela.grid_rowconfigure(i, minsize=0, weight=0)
        janela.grid_columnconfigure(i, minsize=0, weight=0)
    
    janela.grid_rowconfigure(2, weight=1)
    janela.grid_columnconfigure(2, weight=1)

    # 2. Criação do Frame Principal
    frame_main = ctk.CTkFrame(janela, fg_color=CORES["fundo_principal"], corner_radius=0)
    frame_main.grid(row=2, column=2, columnspan=20, sticky="nsew", padx=0, pady=0)
    frame_main.grid_rowconfigure(0, weight=1)
    frame_main.grid_columnconfigure(0, weight=1)
    frame_main.grid_propagate(False)

    # 3. Criação das "Abas"
    abas = [criar_aba_base(frame_main) for _ in range(7)]
    aba_p, aba_a, aba_exe, aba_gra, aba_gan, aba_hist, aba_ana = abas

    # 4. Função para alternar abas
    def show(a_sel):
        for a in abas: a.grid_forget()
        a_sel.grid(row=0, column=0, sticky="nsew")

    # --- SALVA REFERÊNCIAS GLOBAIS ---
    ABA_ANALISE_GLOBAL = aba_ana
    FUNCAO_SHOW_TAB_GLOBAL = show
    # ---------------------------------

    # 5. Configuração do Conteúdo
    configurar_aba_parametros(aba_p) 
    configurar_aba_agentes(aba_a)
    configurar_aba_execucao(aba_exe, aba_p, aba_a) 
    configurar_aba_grafico(aba_gra)
    configurar_aba_gantt_live(aba_gan)
    configurar_aba_historico(aba_hist, largura_total=1280, altura_total=810)
    
    # Agora a aba_ana é gerada dinamicamente pelo botão, então só damos um fundo a ela aqui
    aba_ana.configure(fg_color=CORES["fundo_principal"])

    # 6. Criação dos Botões Laterais
    create_buttons(janela, show, aba_p, aba_a, aba_exe, aba_gra, aba_gan, aba_hist, aba_ana)

    # 7. Inicia mostrando a primeira aba
    show(aba_p)

def resetar_variaveis_globais():
    """Limpa todos os dados da memória para iniciar o Benchmark zerado."""
    global HISTORICO_DATA, DADOS_X, DADOS_Y, MELHOR_MAKESPAN_ATUAL
    global NOME_INSTANCIA_ATUAL, FILA_BOTOES_PENDENTES
    global START_BUTTON_GLOBAL, PAUSE_BUTTON_GLOBAL, SAVE_BUTTON_GLOBAL
    global ESCRITOR_TERMINAL_GLOBAL, MONOTONIC_FILTER
    global SETS_CRIADOS

    
    SETS_CRIADOS = {}
    
    # Limpa estruturas de dados
    HISTORICO_DATA.clear()
    DADOS_X.clear()
    DADOS_Y.clear()
    FILA_BOTOES_PENDENTES.clear()
    
    # Reseta valores escalares
    MELHOR_MAKESPAN_ATUAL = float('inf')
    NOME_INSTANCIA_ATUAL = "---"
    
    # Reseta referências de UI (para evitar erros de widget destruído)
    START_BUTTON_GLOBAL = None
    PAUSE_BUTTON_GLOBAL = None
    SAVE_BUTTON_GLOBAL = None
    
    # Reseta o filtro de log
    if MONOTONIC_FILTER:
        MONOTONIC_FILTER.reset()

def carregar_icones():
    global ICONES_UI
    if ICONES_UI: return

    def criar_versao_preta(img_pil):
        """Cria uma silhueta preta da imagem preservando a transparência."""
        # Cria uma imagem preta do mesmo tamanho
        black_img = Image.new("RGBA", img_pil.size, (0, 0, 0, 255))
        # Usa o canal Alpha (transparência) da original como máscara
        black_img.putalpha(img_pil.getchannel("A"))
        return black_img

    try:
        # Carrega originais (Brancos/Cinzas)
        pil_trash = Image.open("assets/trash.png")
        pil_eye = Image.open("assets/eye.png")
        pil_eye_closed = Image.open("assets/eye_closed.png")
        pil_write = Image.open("assets/write.png") 
        pil_warning = Image.open("assets/warning.png") # Se tiver usando no popup
        pil_add = Image.open("assets/add.png")

        pil_label = Image.open("assets/label.png")   # Ícone vazio (sem set)
        pil_label2 = Image.open("assets/label2.png")
        pil_cheese = Image.open("assets/cheese.png")

        # Salva versões normais
        ICONES_UI["trash"] = ctk.CTkImage(pil_trash, size=(16, 16))
        ICONES_UI["eye"] = ctk.CTkImage(pil_eye, size=(16, 16))
        ICONES_UI["eye_closed"] = ctk.CTkImage(pil_eye_closed, size=(16, 16))
        ICONES_UI["write"] = ctk.CTkImage(pil_write, size=(16, 16))
        ICONES_UI["add"] = ctk.CTkImage(pil_add, size=(16, 16))
        ICONES_UI["label"] = ctk.CTkImage(pil_label, size=(16, 16))
        ICONES_UI["label2"] = ctk.CTkImage(pil_label2, size=(16, 16))
        ICONES_UI["cheese"] = ctk.CTkImage(pil_cheese, size=(16, 16))
        
        # --- GERA VERSÕES PRETAS AUTOMATICAMENTE ---
        ICONES_UI["trash_black"] = ctk.CTkImage(criar_versao_preta(pil_trash), size=(16, 16))
        ICONES_UI["eye_black"] = ctk.CTkImage(criar_versao_preta(pil_eye), size=(16, 16))
        ICONES_UI["eye_closed_black"] = ctk.CTkImage(criar_versao_preta(pil_eye_closed), size=(16, 16))
        ICONES_UI["write_black"] = ctk.CTkImage(criar_versao_preta(pil_write), size=(16, 16))
        ICONES_UI["label_black"] = ctk.CTkImage(criar_versao_preta(pil_label), size=(16, 16))
        ICONES_UI["label2_black"] = ctk.CTkImage(criar_versao_preta(pil_label2), size=(16, 16))

    except Exception as e:
        print(f"Erro ao carregar ícones: {e}")

def abrir_benchmark(root_parent=None):
    resetar_variaveis_globais()
    carregar_icones()
    # Se receber um pai (Launcher), cria como Toplevel (Janela Filha)
    # Se não receber (teste isolado), cria como CTk (Janela Principal)
    if root_parent:
        janela_benchmark = ctk.CTkToplevel(root_parent)
    else:
        janela_benchmark = ctk.CTk()

    janela_benchmark.title("RKO Solver - Benchmark & Experimentation")
    
    # Centralizar
    w, h = 1280, 810
    ws, hs = janela_benchmark.winfo_screenwidth(), janela_benchmark.winfo_screenheight()
    x, y = (ws - w) // 2, (hs - h) // 2
    janela_benchmark.geometry(f"{w}x{h}+{x}+{y}")
    
    # Configura o layout
    configurar_interface(janela_benchmark)
    
    # Protocolo de Fechamento Seguro
    def ao_fechar():
        # Para execuções e threads se estiverem rodando
        if rko_gui_start:
            rko_gui_start.solicitar_parada() 
            
        janela_benchmark.destroy()
        
        # Se tiver pai (Launcher), NAO MATA O PAI
        if not root_parent:
            sys.exit(0)

    janela_benchmark.protocol("WM_DELETE_WINDOW", ao_fechar)

    # Se for filha, traz para frente e foca
    if root_parent:
        janela_benchmark.lift()
        janela_benchmark.focus_force()

    else:
        janela_benchmark.mainloop()

# Para testes isolados (sem launcher)
if __name__ == "__main__":
    ctk.set_appearance_mode('dark')
    abrir_benchmark(None) # None = Modo isolado 