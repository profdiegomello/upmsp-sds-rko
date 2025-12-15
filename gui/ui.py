import customtkinter as ctk
import tkinter as tk
from PIL import Image
from tkinter import filedialog
from typing import Tuple

# --- CONSTANTES DE DESIGN ---
COLORS = {
    "bg_main": "#1A1A1D",
    "bg_card": "#151516",
    "border": "#2D2D35",
    "accent": "#5CAEC4",
    "primary": "#6852A0",
    "text": "#FFFFFF",
    "text_dim": "#413D3D"
}

FONTS = {
    "title": ("Roboto", 20, "bold"),
    "subtitle": ("Roboto", 17, "bold"),
    "body_bold": ("Roboto", 12, "bold"),
    "small": ("Roboto", 11)
}

# --- FUNÇÕES DE APOIO ---

def _center_window(win, width, height):
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    x = (sw - width) // 2
    y = (sh - height) // 2
    win.geometry(f"{width}x{height}+{x}+{y}")

def _create_base_tab(parent) -> ctk.CTkFrame:
    tab = ctk.CTkFrame(parent, width=1200, height=900, border_width=5, border_color=COLORS["border"])
    for i in range(10):
        tab.grid_rowconfigure(i, weight=1, minsize=20)
        tab.grid_columnconfigure(i, weight=1, minsize=20)
    return tab

# --- DIMENSÕES ---
WINDOW_WIDTH = 1375
WINDOW_HEIGHT = 975
AGENT_CARD_WIDTH = 360
AGENT_CARD_HEIGHT = 300

# ==============================================================================
# NOVA FUNÇÃO: COLETOR DE DADOS
# ==============================================================================
def collect_all_data(knight_tab, sliders_tab, io_tab) -> dict:
    """
    Varre todas as abas, extrai os valores dos widgets e empacota em um dicionário.
    """
    data = {}

    # 1. Coletando Knight Tab (Hyper-parameters)
    # Verificamos se os widgets foram criados antes de tentar acessar
    if hasattr(knight_tab, 'widgets'):
        data["hyper_parameters"] = {
            "decoder": knight_tab.widgets["decoder"].get(),
            "time_limit": knight_tab.widgets["time_limit"].get()
        }

    # 2. Coletando Sliders Tab (Agents)
    data["agents"] = {}
    if hasattr(sliders_tab, 'params'):
        for agent_name, widgets in sliders_tab.params.items():
            # Só adiciona se o Checkbox estiver marcado
            is_enabled = widgets["var"].get()
            
            if is_enabled:
                agent_params = {}
                for key, widget in widgets.items():
                    # Ignora chaves de controle visual
                    if key not in ("frame", "var"):
                        agent_params[key] = widget.get()
                
                data["agents"][agent_name] = agent_params

    # 3. Coletando IO Tab (Paths)
    data["io"] = {}
    if hasattr(io_tab, 'widgets'):
        for key, entry_widget in io_tab.widgets.items():
            data["io"][key] = entry_widget.get()

    return data
# ==============================================================================

def build_app() -> Tuple[ctk.CTk, callable, ctk.CTkFrame, ctk.CTkFrame, ctk.CTkFrame, ctk.CTkFrame]:
    janela = ctk.CTk()
    janela.title("RKO-SOLVER")
    _center_window(janela, WINDOW_WIDTH, WINDOW_HEIGHT)
    
    janela.resizable(False, False)
    ctk.set_appearance_mode('dark')

    for malha in range(10):
        janela.grid_rowconfigure(malha, minsize=20)
        janela.grid_columnconfigure(malha, minsize=20)

    main_frame = ctk.CTkFrame(
        janela, fg_color=COLORS["bg_main"], width=1200, height=900,
        border_width=5, border_color=COLORS["border"]
    )
    main_frame.grid(row=2, column=2, columnspan=20, sticky="nsew", padx=10)
    main_frame.grid_rowconfigure(0, weight=1)
    main_frame.grid_columnconfigure(0, weight=1)
    main_frame.grid_propagate(False)

    knight_tab = _create_base_tab(main_frame)
    sliders_tab = _create_base_tab(main_frame)
    io_tab = _create_base_tab(main_frame)
    play_tab = _create_base_tab(main_frame)

    def show_tab(tab):
        for aba in (knight_tab, sliders_tab, io_tab, play_tab):
            aba.grid_forget()
        tab.grid(row=0, column=0, sticky="nsew")

    _setup_knight_tab(knight_tab)
    _setup_sliders_tab(sliders_tab)
    _setup_io_tab(io_tab)
    
    # Passamos as outras abas para o setup do play tab, para podermos ler os dados lá
    _setup_play_tab(play_tab, knight_tab, sliders_tab, io_tab)

    show_tab(knight_tab)

    return janela, show_tab, knight_tab, sliders_tab, io_tab, play_tab

# --- CONFIGURAÇÃO DAS ABAS (ATUALIZADAS COM STORAGE) ---

def _setup_knight_tab(tab):
    tab.widgets = {} # Storage

    ctk.CTkLabel(tab, text="HYPER-PARAMETERS", text_color=COLORS["accent"], font=FONTS["title"]).grid(row=0, column=1, sticky="e", columnspan=3)
    
    ctk.CTkLabel(tab, text="SELECT DECODER", font=FONTS["subtitle"], text_color=COLORS["text"]).grid(row=1, column=1, padx=10, sticky="s")
    
    combo = ctk.CTkComboBox(tab, values=["ECT", "3M", "2n", "KSTS", "SJF"], 
                            border_color=COLORS["primary"], border_width=2, corner_radius=0,
                            dropdown_fg_color="lavender", dropdown_text_color=COLORS["text_dim"], dropdown_hover_color=COLORS["accent"])
    combo.grid(row=2, column=1, padx=10, sticky="n", pady=5)
    tab.widgets["decoder"] = combo # Salvando referência
    
    ctk.CTkLabel(tab, text="TIME LIMIT (SECONDS)", font=FONTS["subtitle"], text_color=COLORS["text"]).grid(row=1, column=2, sticky="sw")
    
    entry = ctk.CTkEntry(tab, width=90, corner_radius=0, border_color=COLORS["primary"], border_width=2)
    entry.grid(row=2, column=2, padx=15,sticky="wn")
    tab.widgets["time_limit"] = entry # Salvando referência

def _setup_sliders_tab(tab):
    content = ctk.CTkScrollableFrame(tab, width=1160, height=860, fg_color="transparent")
    content.grid(row=0, column=0, columnspan=10, rowspan=10, padx=10, pady=10, sticky="nsew")
    
    for i in range(3): content.grid_columnconfigure(i, weight=1, minsize=360)

    tab.params = {} # Storage 
    
    header = ctk.CTkLabel(content, text="AGENTS PARAMETERS", font=FONTS["title"], text_color=COLORS["accent"])
    header.grid(row=0, column=0, columnspan=3, sticky="ew", padx=12, pady=(8,12))

    agents_config = {
        "BRKGA": {"row": 1, "col": 0, "title": "BIASED RANDOM KEY GENETIC ALGORITHM (BRKGA)", 
                  "fields": [("Population", "100"), ("Elite set", "0.20"), ("Mutant set", "0.10"), ("Elite parent inheritance prob", "0.70")]},
        "SA": {"row": 1, "col": 1, "title": "SIMULATED ANNEALING (SA)", 
               "fields": [("Iterations", "50"), ("alphaSA", "0.99"), ("betaMin", "0.05"), ("betaMax", "0.25"), ("Initial Temperature", "10000")]},
        "ILS": {"row": 1, "col": 2, "title": "ITERATED LOCAL SEARCH (ILS)", 
                "fields": [("betaMin", "0.1"), ("betaMax", "0.20")]},
        "VNS": {"row": 2, "col": 0, "title": "VARIABLE NEIGHBORHOOD SEARCH (VNS)", 
                "fields": [("kMax", "5"), ("betaMin", "0.05")]},
        "PSO": {"row": 2, "col": 1, "title": "PARTICLE SWARM OPTIMIZATION (PSO)", 
                "fields": [("PSize", "100"), ("c1", "2.05"), ("betaMin", "2.05"), ("betaMax", "0.73")]},
        "GA1": {"row": 3, "col": 0, "title": "GENETIC ALGORITHM (GA)", 
                "fields": [("Population", "100"), ("CrosProb", "0.98"), ("MutProb", "0.005")]},
        "LNS": {"row": 3, "col": 1, "title": "LARGE NEIGHBORHOOD SEARCH (LNS)", 
                "fields": [("betaMin", "0.10"), ("betaMax", "0.30"), ("T0", "1000"), ("alphaLNS", "0.95")]},
    }

    for name, config in agents_config.items():
        tab.params[name] = _create_agent_card(content, config)

def _create_agent_card(parent, config):
    frame = ctk.CTkFrame(parent, fg_color=COLORS["bg_card"], width=AGENT_CARD_WIDTH, 
                         height=AGENT_CARD_HEIGHT, border_width=1, border_color=COLORS["border"])
    frame.grid(row=config["row"], column=config["col"], padx=8, pady=8, sticky="n")
    frame.grid_propagate(False)

    lbl = ctk.CTkLabel(frame, text=config["title"], font=FONTS["body_bold"], text_color=COLORS["accent"])
    lbl.grid(row=0, column=0, sticky="w", padx=10, pady=(8,4))
    
    var = tk.BooleanVar(value=True)
    ctk.CTkCheckBox(frame, text="", variable=var).grid(row=0, column=1, sticky="e", padx=10, pady=(8,4))

    widgets = {"frame": frame, "var": var}
    for i, (label_text, default_val) in enumerate(config["fields"], start=1):
        ctk.CTkLabel(frame, text=label_text, anchor="w", font=FONTS["small"]).grid(row=i, column=0, sticky="w", padx=10, pady=6)
        entry = ctk.CTkEntry(frame, width=90)
        entry.insert(0, default_val)
        entry.grid(row=i, column=1 if "col" in config and config["col"] != 0 else 0, sticky="e", padx=10 if config["col"] != 0 else 0, pady=6)
        widgets[label_text] = entry
        
    return widgets

def _setup_io_tab(tab):
    tab.widgets = {} # Storage

    def _escolher(entry):
        pasta = filedialog.askdirectory()
        if pasta:
            entry.delete(0, "end")
            entry.insert(0, pasta)

    ctk.CTkLabel(tab, text="IO CONFIGURATION", text_color=COLORS["accent"], font=FONTS["title"]).grid(row=0, column=1, columnspan=10, sticky="w", pady=(8,12), padx=70)
    
    try:
        dots_img = ctk.CTkImage(Image.open("img/dots.png"), size=(16, 16))
    except:
        dots_img = None 

    # chave (key) para cada item da lista: ("key", "Label", row)
    secoes = [
        ("output_path", "Output Path", 1), 
        ("instance_path", "Instance Folder Path", 2), 
        ("gantt_path", "Gantt Chart Path", 3)
    ]
    
    for key, label, row in secoes:
        f = ctk.CTkFrame(tab, fg_color="transparent")
        f.grid(row=row, column=0, padx=8, pady=8, sticky="n")
        
        ctk.CTkLabel(f, text=label, font=FONTS["subtitle"]).grid(row=0, column=0, padx=8, sticky="w")
        e = ctk.CTkEntry(f, border_color=COLORS["primary"], border_width=2, width=350)
        e.grid(row=1, column=0, padx=10, pady=3)
        tab.widgets[key] = e # Salvando referência usando a chave
        
        ctk.CTkButton(f, text="" if dots_img else "...", width=30, image=dots_img, 
                      fg_color="transparent", hover_color=COLORS["accent"],
                      command=lambda ent=e: _escolher(ent)).grid(row=1, column=1, pady=10)

def _setup_play_tab(tab, knight_tab, sliders_tab, io_tab):
    
    def on_start():
        # AQUI É O MOMENTO MÁGICO
        dados = collect_all_data(knight_tab, sliders_tab, io_tab)
        
        # depois troco para chamar a thread
        print(dados)
        #print("Dicionário pronto para ser enviado para a Thread!")

    class RedirectText(object):
        def __init__(self, text_widget):
            self.text_widget = text_widget

        def write(self, string):
            # habilita temporariamente para inserir
            self.text_widget.configure(state="normal")
            self.text_widget.insert("end", string)
            self.text_widget.see("end")  # rola automaticamente para o fim
            # volta a desabilitar
            self.text_widget.configure(state="disabled")

        def flush(self):
            pass  # necessário para compatibilidade com sys.stdout

    import sys
    
    execution_lbl = ctk.CTkLabel(tab, text="EXECUTION", text_color=COLORS["accent"], font=FONTS["title"])
    execution_lbl.grid(row=0, column=3, columnspan=3, sticky="ew", padx=7, pady=(8,12))
    
    start_btn = ctk.CTkButton(tab, text='START', width=200, height=50, command=on_start,
                              fg_color="#77198f",
                              font=("Roboto", 18, "bold")
                              )
    start_btn.grid(row=1, column=2, sticky="we")
    
    terminal = ctk.CTkTextbox(tab, width=580, height=600, border_width=0, fg_color="black", text_color="#009605",
                              corner_radius=0
                              )
    terminal.grid(row=1, column=4, sticky="sn", rowspan=5)
    
    # desativa escrita manual logo de início
    terminal.configure(state="disabled")
    
    sys.stdout = RedirectText(terminal)
