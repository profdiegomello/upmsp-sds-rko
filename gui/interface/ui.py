import customtkinter as ctk
import tkinter as tk
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

FIG_HIST_LINHA, AX_HIST_LINHA, CANVAS_HIST_LINHA = None, None, None
FIG_HIST_GANTT, AX_HIST_GANTT, CANVAS_HIST_GANTT = None, None, None

VAR_FILTRO_INSTANCIA = None
VAR_FILTRO_DECODER = None
VARS_FILTRO_AGENTES = {}
CHAVE_SELECIONADA_ATUAL = None
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
            parent=top_level,  # <--- O PULO DO GATO ESTÁ AQUI
            title="Save the figure",
            filetypes=tk_filetypes,
            defaultextension=default_filetype
        )

        if fname:
            try:
                self.canvas.figure.savefig(fname)
            except Exception as e:
                messagebox.showerror("Error saving file", str(e), parent=top_level)

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

def aplicar_filtros_historico(evento=None):
    global FRAME_LISTA_HISTORICO, HISTORICO_DATA, VAR_FILTRO_INSTANCIA, VAR_FILTRO_DECODER, VARS_FILTRO_AGENTES, CHAVE_SELECIONADA_ATUAL, COMBO_INSTANCIAS, VAR_ORDENACAO_HISTORICO

    # Limpa a lista atual
    for widget in FRAME_LISTA_HISTORICO.winfo_children():
        widget.destroy()

    # Pega os valores dos filtros
    f_inst = VAR_FILTRO_INSTANCIA.get()
    f_dec = VAR_FILTRO_DECODER.get()
    f_sort = VAR_ORDENACAO_HISTORICO.get() # Criterio de ordenacao
    
    agentes_requeridos = [nome for nome, var in VARS_FILTRO_AGENTES.items() if var.get()]
    
    if COMBO_INSTANCIAS and HISTORICO_DATA:
        nomes_unicos = sorted(list(set([v['meta_nome'] for v in HISTORICO_DATA.values()])))
        COMBO_INSTANCIAS.configure(values=["all"] + nomes_unicos)

    chaves_filtradas = []
    for chave, dados in HISTORICO_DATA.items():
        if f_inst != "all" and dados['meta_nome'] != f_inst: continue
        if f_dec != "all" and dados['meta_decoder'].lower() != f_dec.lower(): continue
        
        if agentes_requeridos:
            raw_agentes_run = dados.get('meta_agentes', '')
            lista_agentes_na_run = [ag for ag in raw_agentes_run.split("-") if ag]
            if not all(req in lista_agentes_na_run for req in agentes_requeridos):
                continue
             
        chaves_filtradas.append(chave)

    def natural_keys(chave):
        texto = HISTORICO_DATA[chave]['meta_nome']
        return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', texto)]

    def get_makespan(chave):
        lista_y = HISTORICO_DATA[chave]['y']
        if lista_y:
            return min(lista_y)
        return float('inf') # Se nao tiver dados, joga pro final

    if f_sort == "Descending Date/Hour":
        try:
            chaves_filtradas.sort(
                key=lambda k: datetime.strptime(HISTORICO_DATA[k]['meta_hora'], "%d/%m/%y %H:%M:%S"), 
                reverse=True
            )
        except: chaves_filtradas.sort()

    elif f_sort == "Ascending Date/Hour":
        try:
            chaves_filtradas.sort(
                key=lambda k: datetime.strptime(HISTORICO_DATA[k]['meta_hora'], "%d/%m/%y %H:%M:%S"), 
                reverse=False
            )
        except: chaves_filtradas.sort()
            
    elif f_sort == "Ascending Instance":
        try: chaves_filtradas.sort(key=natural_keys, reverse=False)
        except: chaves_filtradas.sort()

    elif f_sort == "Descending Instance":
        try: chaves_filtradas.sort(key=natural_keys, reverse=True)
        except: chaves_filtradas.sort()
    
    elif f_sort == "Ascending Makespan":
        # Do MELHOR (menor valor) para o PIOR (maior valor)
        try: chaves_filtradas.sort(key=get_makespan, reverse=False)
        except: chaves_filtradas.sort()

    elif f_sort == "Descending Makespan":
        # Do PIOR (maior valor) para o MELHOR (menor valor)
        try: chaves_filtradas.sort(key=get_makespan, reverse=True)
        except: chaves_filtradas.sort()

    elif f_sort == "Decoder":
        chaves_filtradas.sort(key=lambda k: HISTORICO_DATA[k]['meta_decoder'])
    
    else:
        # Fallback
        try:
            chaves_filtradas.sort(
                key=lambda k: datetime.strptime(HISTORICO_DATA[k]['meta_hora'], "%d/%m/%y %H:%M:%S"), 
                reverse=True
            )
        except: chaves_filtradas.sort()

    AX_HIST_LINHA.clear()
    
    for chave in chaves_filtradas:
        dados = HISTORICO_DATA[chave]
        raw_x, raw_y = dados['x'], dados['y']
        
        if not raw_x: continue
        
        eixo_x, eixo_y = zip(*sorted(zip(raw_x, raw_y), key=lambda p: p[0]))
        if chave != CHAVE_SELECIONADA_ATUAL:
            AX_HIST_LINHA.plot(eixo_x, eixo_y, color='white', alpha=0.6, linewidth=1.7)

        raw_agentes = dados.get('meta_agentes', 'N/A')
        lista_nomes = [x for x in raw_agentes.split("-") if x]
        
        linhas_agentes = []
        linha_atual = ""
        limite_char = 28
        
        for nome in lista_nomes:
            if len(linha_atual) + len(nome) + 2 > limite_char:
                linhas_agentes.append(linha_atual.strip(", "))
                linha_atual = nome + ", "
            else:
                linha_atual += nome + ", "
        
        if linha_atual:
            linhas_agentes.append(linha_atual.strip(", "))
            
        texto_agentes_formatado = "\n".join(linhas_agentes)
        qtd_linhas_extras = len(linhas_agentes)
        altura_dinamica = 65 + (qtd_linhas_extras * 15)

        melhor_mksp = min(eixo_y) if eixo_y else "?"
        hora = dados.get('meta_hora', '')
        
        txt_btn = f"{dados['meta_nome']}\n" \
                  f"Time: {hora}\n" \
                  f"Best: {melhor_mksp} | {dados['meta_decoder']}\n" \
                  f"[{texto_agentes_formatado}]"
                  
        cor_btn_normal = "#6D28D9" if chave == CHAVE_SELECIONADA_ATUAL else "#333333"
        
        btn = ctk.CTkButton(
            FRAME_LISTA_HISTORICO, 
            text=txt_btn, 
            font=("Roboto", 11),
            fg_color=cor_btn_normal, 
            text_color="#FFFFFF", 
            hover_color="#FFFFFF",
            height=altura_dinamica, 
            anchor="w",
            command=lambda k=chave: carregar_instancia_historico(k)
        )
        btn.chave_privada = chave
        
        def on_enter(e, b=btn):
            b.configure(fg_color="#FFFFFF", text_color="#000000")
            
        def on_leave(e, b=btn, cor_orig=cor_btn_normal):
            b.configure(fg_color=cor_orig, text_color="#FFFFFF")

        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        
        btn.pack(fill="x", pady=2, padx=5)

    if CHAVE_SELECIONADA_ATUAL and CHAVE_SELECIONADA_ATUAL in chaves_filtradas:
        dados = HISTORICO_DATA[CHAVE_SELECIONADA_ATUAL]
        eixo_x, eixo_y = zip(*sorted(zip(dados['x'], dados['y']), key=lambda p: p[0]))
        AX_HIST_LINHA.plot(eixo_x, eixo_y, color='#00FF00', linewidth=2.5, marker='o', markersize=4, label="Selected")
        AX_HIST_LINHA.set_title(f"Convergence Curves | Selected: {dados['meta_nome']} (Makespan: {min(eixo_y)})", color="white", fontsize=10)
    else:
        AX_HIST_LINHA.set_title(f"Convergence Curves (Total: {len(chaves_filtradas)})", color="white", fontsize=10)

    AX_HIST_LINHA.grid(True, linestyle='--', alpha=0.3)
    CANVAS_HIST_LINHA.draw()

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
    frame_checks = ctk.CTkFrame(frame_filtros, fg_color="transparent")
    frame_checks.pack(fill="x", padx=2, pady=2)
    
    lista_agentes = ["BRKGA", "SA", "ILS", "VNS", "PSO", "GA", "LNS"]
    VARS_FILTRO_AGENTES = {}
    for i, ag in enumerate(lista_agentes):
        var = ctk.BooleanVar(value=False)
        chk = ctk.CTkCheckBox(frame_checks, text=ag, variable=var, font=("Roboto", 9), height=16, width=16, checkbox_width=16, checkbox_height=16, command=aplicar_filtros_historico)
        chk.grid(row=i//4, column=i%4, sticky="w", padx=2, pady=2)
        VARS_FILTRO_AGENTES[ag] = var

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
    AX_GANTT.set_title(f"Instance: {nome_instancia}  |  Makespan: {max_completion_time}  |  Elapsed Time: {tempo_decorrido:.2f}s", color="white", fontsize=11, fontweight="bold")
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

    if ESCRITOR_TERMINAL_GLOBAL is None: return

    tipo_status = dados.get("status")
    texto_log = dados.get("message", "")
    nome_pacote = dados.get("instancia") 
    
    COR_NEUTRA = "#333333"

    if tipo_status == "running":
        if nome_pacote: NOME_INSTANCIA_ATUAL = nome_pacote
        MELHOR_MAKESPAN_ATUAL = float('inf'); TEMPO_INICIO_BATERIA = time.time(); DADOS_X.clear(); DADOS_Y.clear()
        
        if MONOTONIC_FILTER: MONOTONIC_FILTER.reset()
            
        ESCRITOR_TERMINAL_GLOBAL.write(f"{texto_log}\n")
        
        if CANVAS_GLOBAL:
            LINHA_GLOBAL.set_data([], [])
            AX_GLOBAL.set_title(f"{NOME_INSTANCIA_ATUAL}...", fontsize=10, color="white")
            AX_GLOBAL.set_xlim(auto=True); AX_GLOBAL.set_ylim(auto=True); AX_GLOBAL.relim(); AX_GLOBAL.autoscale_view(); CANVAS_GLOBAL.draw()
        if AX_GANTT: AX_GANTT.clear(); CANVAS_GANTT.draw()

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
                        AX_GLOBAL.relim(); AX_GLOBAL.autoscale_view(); CANVAS_GLOBAL.draw()
                if gantt_data and CANVAS_GANTT: CANVAS_GANTT.get_tk_widget().after(0, lambda: atualizar_desenho_gantt(gantt_data, nome_pacote, time_to_best))
    
    elif tipo_status == "final_plateau":
        final_time = float(dados.get("final_time", 0))
        final_mksp = float(dados.get("final_makespan", 0))
        nome_inst = dados.get("instancia")
        if nome_inst == NOME_INSTANCIA_ATUAL and DADOS_X:
            if final_time > DADOS_X[-1]:
                DADOS_X.append(final_time); DADOS_Y.append(final_mksp)
                if CANVAS_GLOBAL and LINHA_GLOBAL:
                    LINHA_GLOBAL.set_data(DADOS_X, DADOS_Y)
                    AX_GLOBAL.set_xlim(left=0, right=final_time * 1.02)
                    if DADOS_Y:
                        min_y, max_y = min(DADOS_Y), max(DADOS_Y)
                        margem = (max_y - min_y) * 0.1 if max_y != min_y else 1
                        AX_GLOBAL.set_ylim(bottom=max(0, min_y - margem), top=max_y + margem)
                    AX_GLOBAL.set_title(f"Instance: {NOME_INSTANCIA_ATUAL} (Completed)", fontsize=10, color="white", fontweight="bold"); CANVAS_GLOBAL.draw()

    elif tipo_status == "paused":
        ESCRITOR_TERMINAL_GLOBAL.write(f"{texto_log}\n")
        if PAUSE_BUTTON_GLOBAL and hasattr(PAUSE_BUTTON_GLOBAL, 'icons'):
            PAUSE_BUTTON_GLOBAL.configure(
                text="RESUME", state="normal", 
                image=PAUSE_BUTTON_GLOBAL.icons["resume"], 
                fg_color=COR_NEUTRA, 
                text_color="white"
            )
        if SAVE_BUTTON_GLOBAL:
            SAVE_BUTTON_GLOBAL.configure(state="normal", fg_color=COR_NEUTRA)
        if START_BUTTON_GLOBAL:
            # MUDANÇA: Mantém o Start/Stop habilitado durante a pausa
            START_BUTTON_GLOBAL.configure(state="normal") 

    elif tipo_status == "resumed":
        ESCRITOR_TERMINAL_GLOBAL.write(f"{texto_log}\n")
        if PAUSE_BUTTON_GLOBAL and hasattr(PAUSE_BUTTON_GLOBAL, 'icons'):
            PAUSE_BUTTON_GLOBAL.configure(
                text="PAUSE", state="normal", 
                image=PAUSE_BUTTON_GLOBAL.icons["pause"], 
                fg_color=COR_NEUTRA, 
                text_color="white"
            )
        if SAVE_BUTTON_GLOBAL:
            SAVE_BUTTON_GLOBAL.configure(state="disabled")
        if START_BUTTON_GLOBAL:
            START_BUTTON_GLOBAL.configure(state="normal") 

    elif tipo_status == "instancia_concluida":
        nome_base = dados.get("instancia"); gantt_final = dados.get("gantt_data")
        if nome_base == NOME_INSTANCIA_ATUAL and len(DADOS_X) > 0: eixo_x_final = list(DADOS_X); eixo_y_final = list(DADOS_Y)
        else: eixo_x_final = []; eixo_y_final = []
        decoder_usado = dados.get("decoder", "Dec"); agentes_usados = dados.get("agentes", ["Agentes"]) 
        if isinstance(agentes_usados, list): str_agentes = "-".join(agentes_usados)
        else: str_agentes = str(agentes_usados)
        hora_termino = time.strftime("%d/%m/%y %H:%M:%S")
        chave_unica = f"{nome_base} [{decoder_usado}] ({str_agentes}) @{hora_termino}"
        if nome_base:
            HISTORICO_DATA[chave_unica] = {
                'x': eixo_x_final, 'y': eixo_y_final, 'gantt': gantt_final,
                'meta_nome': nome_base, 'meta_decoder': decoder_usado, 
                'meta_agentes': str_agentes, 'meta_hora': hora_termino 
            }
            if chave_unica not in FILA_BOTOES_PENDENTES: FILA_BOTOES_PENDENTES.append(chave_unica)

    elif tipo_status == "finished": 
        ESCRITOR_TERMINAL_GLOBAL.write(f"\n{'='*40}\n{texto_log}\n{'='*40}\n")
        try: START_BUTTON_GLOBAL.resetar_estado()
        except: pass
    elif tipo_status == "error": 
        ESCRITOR_TERMINAL_GLOBAL.write(f"ERRO: {texto_log}\n")
        try: START_BUTTON_GLOBAL.resetar_estado()
        except: pass   
    elif tipo_status == "completed_all":
        ESCRITOR_TERMINAL_GLOBAL.write(f"\n>>> {texto_log} <<<\n")
        try: START_BUTTON_GLOBAL.resetar_estado()
        except: pass
    elif tipo_status == "log": 
        ESCRITOR_TERMINAL_GLOBAL.write(f"{texto_log}\n")

def configurar_aba_parametros(aba):
    aba.widgets_armazenados = {} 
    
    rotulo_titulo = ctk.CTkLabel(aba, text="HYPER-PARAMETERS", text_color=CORES["destaque"], font=FONTES["titulo"])
    rotulo_titulo.grid(row=0, column=1, sticky="e", columnspan=3)
    
    rotulo_decoder = ctk.CTkLabel(aba, text="SELECT DECODER", font=FONTES["subtitulo"], text_color=CORES["texto"])
    rotulo_decoder.grid(row=1, column=1, padx=10, sticky="s")
    
    combo_decoder = ctk.CTkComboBox(
        aba, values=["CHEAPEST", "M3LAW", "ECT", "INCREMENTAL", "KSTS"], 
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
    for i in range(3): area_rolagem.grid_columnconfigure(i, weight=1, minsize=400)
    aba.parametros_agentes = {} 
    
    ctk.CTkLabel(area_rolagem, text="AGENTS PARAMETERS", font=FONTES["titulo"], text_color=CORES["destaque"]).grid(row=0, column=0, columnspan=3, sticky="ew", padx=12, pady=(8,12))
    
    configuracao_agentes = {
        "BRKGA": {"linha": 1, "coluna": 0, "titulo": "BIASED RANDOM KEY GENETIC ALGORITHM (BRKGA)", "campos": [("Population", "100"), ("Elite set %", "0.20"), ("Mutant set %", "0.10"), ("Inheritance Prob", "0.70")]},
        "SA":    {"linha": 1, "coluna": 1, "titulo": "SIMULATED ANNEALING (SA)", "campos": [("Iterations", "50"), ("alphaSA", "0.99"), ("betaMin", "0.05"), ("betaMax", "0.25"), ("Initial Temperature", "10000")]},
        "PSO":   {"linha": 2, "coluna": 0, "titulo": "PARTICLE SWARM OPTIMIZATION (PSO)", "campos": [("PSize", "100"), ("c1", "2.05"), ("c2", "2.05"), ("w", "0.73")]},
        "GA":    {"linha": 2, "coluna": 1, "titulo": "GENETIC ALGORITHM (GA)", "campos": [("Population", "100"), ("CrosProb", "0.98"), ("MutProb", "0.005")]},
        "LNS":   {"linha": 1, "coluna": 2, "titulo": "LARGE NEIGHBORHOOD SEARCH (LNS)", "campos": [("betaMin", "0.10"), ("betaMax", "0.30"), ("T0", "1000"), ("alphaLNS", "0.95")]},
        "VNS":   {"linha": 2, "coluna": 2, "titulo": "VARIABLE NEIGHBORHOOD SEARCH (VNS)", "campos": [("kMax", "5"), ("betaMin", "0.05")]},
        "ILS":   {"linha": 3, "coluna": 2, "titulo": "ITERATED LOCAL SEARCH (ILS)", "campos": [("betaMin", "0.1"), ("betaMax", "0.20")]},
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
    
    widgets = {"frame_conteiner": frame , "variavel_controle": var_chk}
    for i, (txt, val) in enumerate(config["campos"], start=1):
        ctk.CTkLabel(frame, text=txt, anchor="w", font=FONTES["pequena"]).grid(row=i, column=0, sticky="w", padx=70+20, pady=6)
        
        ent = ctk.CTkEntry(frame, width=70); ent.insert(0, val)
        ent.grid(row=i, column=0, sticky="w", padx=10 if config.get("coluna",0) != 0 else 0, pady=6)
        
        widgets[txt] = ent
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

def carregar_dados_interface(dados, aba_p, aba_a, aba_io):
    """Preenche widgets com dados do dump."""
    try:
        if "hyper_parameters" in dados and hasattr(aba_p, 'widgets_armazenados'):
            for k, v in dados["hyper_parameters"].items():
                w = aba_p.widgets_armazenados.get(k)
                if w:
                    if isinstance(w, ctk.CTkComboBox): w.set(v)
                    elif isinstance(w, ctk.CTkEntry): w.delete(0, "end"); w.insert(0, str(v))
        if "io" in dados and hasattr(aba_io, 'widgets_armazenados'):
            for k, v in dados["io"].items():
                w = aba_io.widgets_armazenados.get(k)
                if w: w.delete(0, "end"); w.insert(0, str(v))
        if "agents" in dados and hasattr(aba_a, 'parametros_agentes'):
            for _, widgets in aba_a.parametros_agentes.items():
                widgets["variavel_controle"].set(False)
            for nome_ag, params in dados["agents"].items():
                widgets = aba_a.parametros_agentes.get(nome_ag)
                if widgets:
                    widgets["variavel_controle"].set(True)
                    for kp, vp in params.items():
                        ent = widgets.get(kp)
                        if ent and isinstance(ent, ctk.CTkEntry):
                            ent.delete(0, "end"); ent.insert(0, str(vp))
    except Exception as e: print(f"Erro popular UI: {e}")

def configurar_aba_execucao(aba, aba_p, aba_a, aba_io):
    global ESCRITOR_TERMINAL_GLOBAL, START_BUTTON_GLOBAL, PAUSE_BUTTON_GLOBAL, SAVE_BUTTON_GLOBAL, MONOTONIC_FILTER
    
    # --- ÍCONES ---
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

    # --- CORES ---
    COR_NEUTRA = "#333333"
    COR_NEUTRA_HOVER = "#444444"
    COR_START = "#77198f"
    COR_STOP = "#C0392B"

    # --- FUNÇÃO AUXILIAR: TRAVAR CAMPOS (COM VISUAL TRANSPARENTE) ---
    def travar_campos_estruturais(bloquear: bool):
        estado = "disabled" if bloquear else "normal"
        
        # Cores para indicar travamento (efeito visual)
        # Se bloqueado: Fundo quase preto, texto cinza, borda escura
        # Se normal: Fundo padrão do tema Dark (#343638), texto branco, borda roxa
        fg_c = "#101010" if bloquear else "#343638" 
        txt_c = "#555555" if bloquear else "#FFFFFF"
        brd_c = "#222222" if bloquear else CORES["primaria"]

        def _aplicar(widget):
            if widget:
                widget.configure(state=estado, fg_color=fg_c, text_color=txt_c, border_color=brd_c)

        if hasattr(aba_p, 'widgets_armazenados'):
            _aplicar(aba_p.widgets_armazenados.get("execution_times"))
            
        if hasattr(aba_io, 'widgets_armazenados'):
            _aplicar(aba_io.widgets_armazenados.get("instance_path"))

    def alternar_start_stop():
        if rko_gui_start is None: return
        if not controles["running"]:
            # INICIAR
            controles["running"] = True; controles["paused"] = False
            travar_campos_estruturais(True) # Trava e escurece campos
            
            btn_start.configure(text="STOP EXECUTION", fg_color=COR_STOP, hover_color="#E74C3C", state="normal")
            btn_pause.configure(state="normal", text="PAUSE", image=aba.icons["pause"], fg_color=COR_NEUTRA, hover_color=COR_NEUTRA_HOVER)
            btn_save.configure(state="disabled"); btn_load.configure(state="disabled")
            
            try: term.configure(state="normal"); term.delete("1.0", "end"); term.configure(state="disabled")
            except: pass

            data = coletar_dados_interface(aba_p, aba_a, aba_io)
            # Salvar cache
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
            # PAUSANDO...
            btn_pause.configure(text="PAUSING...", state="disabled", fg_color=COR_NEUTRA, image=None) 
            btn_save.configure(state="disabled") 
            
            # --- MUDANÇA AQUI: NÃO DESABILITA O STOP ---
            # btn_start.configure(state="disabled") <- Removido
            btn_start.configure(state="normal") # Garante que STOP continua ativo
            
            aba.update_idletasks()
            
            controles["paused"] = True
            if hasattr(rko_gui_start, 'alternar_pausa'):
                rko_gui_start.alternar_pausa(True)
        else:
            # RETOMANDO...
            btn_pause.configure(text="RESUMING...", state="disabled", fg_color=COR_NEUTRA, image=None)
            
            aba.update_idletasks()
            
            novos_dados = coletar_dados_interface(aba_p, aba_a, aba_io)
            if hasattr(rko_gui_start, 'atualizar_parametros_runtime'):
                rko_gui_start.atualizar_parametros_runtime(novos_dados)

            controles["paused"] = False
            if hasattr(rko_gui_start, 'alternar_pausa'):
                rko_gui_start.alternar_pausa(False)
            
            btn_save.configure(state="disabled")
            btn_start.configure(state="normal")

    def acao_salvar_experimento():
        if not controles["paused"]:
            messagebox.showwarning("Warning", "You must PAUSE before saving.")
            return
        caminho = filedialog.asksaveasfilename(parent=aba, 
                                               defaultextension=".rko",
                                               filetypes=[("RKO Exp", "*.rko")])
        if not caminho: return
        try:
            btn_save.configure(text="SAVING...", state="disabled"); aba.update_idletasks()
            
            estado_ui = {"historico": HISTORICO_DATA, "dados_grafico_x": DADOS_X, "dados_grafico_y": DADOS_Y, "melhor": MELHOR_MAKESPAN_ATUAL, "instancia": NOME_INSTANCIA_ATUAL}
            estado_backend = rko_gui_start.obter_estado_checkpoint() if hasattr(rko_gui_start, 'obter_estado_checkpoint') else {}
            
            dados_visuais = coletar_dados_interface(aba_p, aba_a, aba_io)
            estado_backend["params"] = dados_visuais 

            dump = {"timestamp": datetime.now().strftime("%Y-%m-%d"), "ui": estado_ui, "backend": estado_backend}
            with open(caminho, "wb") as f: pickle.dump(dump, f)
            ESCRITOR_TERMINAL_GLOBAL.write(f"\n>>> SAVED: {os.path.basename(caminho)}\n")
            messagebox.showinfo("Saved", "Success!")
        except Exception as e: messagebox.showerror("Error", str(e))
        finally: btn_save.configure(text="SAVE EXP.", state="normal")

    def acao_carregar_experimento():
        if controles["running"]: return
        
        caminho = filedialog.askopenfilename(parent=aba, filetypes=[("RKO Exp", "*.rko")])
        if not caminho: return
        
        try:
            btn_load.configure(text="LOADING...", state="disabled")
            aba.update_idletasks()

            with open(caminho, "rb") as f: dump = pickle.load(f)
            
            # Checa integridade
            if "backend" not in dump or "ui" not in dump:
                raise ValueError("Invalid file structure: Missing 'backend' or 'ui' keys.")

            d_back = dump["backend"]
            fila_tarefas = d_back.get("fila_tarefas", [])

            # Verifica se é um dump da versão antiga (sem contadores de instância)
            if fila_tarefas and len(fila_tarefas) > 0:
                primeira_tarefa = fila_tarefas[0]
                if "inst_idx" not in primeira_tarefa or "inst_total" not in primeira_tarefa:
                    raise ValueError(
                        "Incompatible Version detected!\n\n"
                        "Please use checkpoints created with the current version."
                    )
            
            # Se passou da validação, prossegue normalmente
            
            d_ui = dump["ui"]
            
            if "params" in d_back: 
                carregar_dados_interface(d_back["params"], aba_p, aba_a, aba_io)
            
            global HISTORICO_DATA, DADOS_X, DADOS_Y, MELHOR_MAKESPAN_ATUAL, NOME_INSTANCIA_ATUAL, FILA_BOTOES_PENDENTES
            HISTORICO_DATA = d_ui.get("historico", {})
            DADOS_X = d_ui.get("dados_grafico_x", [])
            DADOS_Y = d_ui.get("dados_grafico_y", [])
            MELHOR_MAKESPAN_ATUAL = d_ui.get("melhor", float('inf'))
            NOME_INSTANCIA_ATUAL = d_ui.get("instancia", "Resumed")
            FILA_BOTOES_PENDENTES = list(HISTORICO_DATA.keys())
            
            try: 
                term.configure(state="normal")
                term.delete("1.0", "end")
                term.configure(state="disabled")
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
            
            if hasattr(rko_gui_start, 'restaurar_e_continuar'):
                rko_gui_start.restaurar_e_continuar(d_back, manipulador_retorno_interface, start_paused=True)
                
        except Exception as e:
            # Mostra o erro amigável para o usuário e cancela o carregamento
            messagebox.showerror("Load Failed", f"Could not load checkpoint:\n{e}", parent=aba)
            
            # Reseta estado visual caso tenha falhado no meio do caminho
            btn_load.configure(text="LOAD EXP.", state="normal")
            
        finally: 
            # Se deu certo (está rodando), mantém LOAD desabilitado. Se deu erro, reabilita.
            if controles["running"]: 
                btn_load.configure(state="disabled", text="LOAD EXP.")
            else:
                btn_load.configure(state="normal", text="LOAD EXP.")

    def resetar_botoes():
        controles["running"] = False; controles["paused"] = False
        
        # Destrava visualmente ao terminar
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

def centralizar_janela(janela, w, h):
    ws = janela.winfo_screenwidth(); hs = janela.winfo_screenheight()
    x = (ws - w) // 2; y = (hs - h) // 2
    janela.geometry(f"{w}x{h}+{x}+{y}")

def criar_aba_base(pai):
    f = ctk.CTkFrame(pai, width=1200, height=900, border_width=5, border_color=CORES["borda"])
    for i in range(10): f.grid_rowconfigure(i, weight=1, minsize=20); f.grid_columnconfigure(i, weight=1, minsize=20)
    return f

# FUNCAO PRINCIPAL REFATORADA (Para uso do Launcher) 
def configurar_interface(janela):
    
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

    # 3. Criação das "Abas" (Frames sobrepostos)
    abas = [criar_aba_base(frame_main) for _ in range(7)]
    aba_p, aba_a, aba_io, aba_exe, aba_gra, aba_gan, aba_hist = abas

    # 4. Função para alternar abas
    def show(a_sel):
        for a in abas: a.grid_forget()
        a_sel.grid(row=0, column=0, sticky="nsew")

    # 5. Configuração do Conteúdo de cada Aba
    configurar_aba_parametros(aba_p)
    configurar_aba_agentes(aba_a)
    configurar_aba_entrada_saida(aba_io)
    configurar_aba_execucao(aba_exe, aba_p, aba_a, aba_io)
    configurar_aba_grafico(aba_gra)
    configurar_aba_gantt_live(aba_gan)
    configurar_aba_historico(aba_hist, largura_total=1280, altura_total=810)

    # 6. Criação dos Botões Laterais (Usando buttons.py)
    # A função create_buttons coloca os botões na grid(row=2, column=0, columnspan=2)
    # que é a lateral esquerda definida no layout original.
    create_buttons(janela, show, aba_p, aba_a, aba_io, aba_exe, aba_gra, aba_gan, aba_hist)

    # 7. Inicia mostrando a primeira aba
    show(aba_p)

def abrir_benchmark(root_parent=None):
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