import customtkinter as ctk
from tkinter import ttk, filedialog, messagebox
import tkinter as tk
import os
import sys
import random
import statistics
import math
from PIL import Image
from tkinter.colorchooser import askcolor

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import numpy as np

# Tenta importar o tksheet
try:
    from tksheet import Sheet
except ImportError:
    print("ERRO CRÍTICO: Biblioteca 'tksheet' não instalada.")
    Sheet = None 

# Toolbar customizada para corrigir o foco da janela ao salvar gráficos
class CustomToolbar(NavigationToolbar2Tk):
    def save_figure(self, *args):
        top_level = self.canvas.get_tk_widget().winfo_toplevel()
        filetypes = self.canvas.get_supported_filetypes()
        default_filetype = self.canvas.get_default_filetype()
        
        tk_filetypes = []
        for name, ext in filetypes.items():
            tk_filetypes.append((name, ext))
        
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


CORES_CREATOR = {
    "sidebar_bg": "#2B2B30",       
    "main_bg": "#1A1A1D",          
    "card_bg": "#2D2D35",      
    "btn_primary": "#3A5F75",      
    "btn_hover": "#4A7A95",
    "btn_action": "#6D28D9",   
    "btn_action_hover": "#5b21b6",
    "text_highlight": "#5CAEC4",
    "grid_bg": "#151516",
    "success_text": "#00E676", 
    
    # Cores tksheet
    "sheet_bg": "#151516",             
    "sheet_fg": "#E0E0E0",             
    "sheet_header_bg": "#2D2D35",      
    "sheet_header_fg": "#5CAEC4",      
    "sheet_grid": "#333333",           
    "sheet_select": "#6D28D9",         
    "sheet_select_bg": "#3c3c42",
}

class InstanceCreator(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        
        self.parent_app = parent
        self.protocol("WM_DELETE_WINDOW", self.ao_fechar)
        
        self.title("RKO Instance Creator")
        self.geometry("1250x700") 
        
        if os.name == 'nt':
            try: self.after(200, lambda: self.iconbitmap())
            except: pass
        self.focus_force()

        # --- DADOS DA INSTÂNCIA ---
        self.dados = {
            "created": False,
            "N": 0, "M": 0,
            "processing": [], 
            "setup": {} 
        }
        
        # Carregar icones (Cache)
        self.icon_save = None
        self.carregar_icones()
        
        # Rastreia o que está selecionado na árvore: ("tipo", "tag")
        self.selecao_atual = ("general", "root")

        # --- VARIÁVEIS DE ESTATÍSTICA ---
        self.canvas_stats = None 
        self.fig_stats = None
        self.toolbar_stats = None
        self.layout_var = ctk.StringVar(value="Horizontal") 
        
        self.STATS_CONFIG = [
            ("Min", 'min', ""),
            ("Mean", 'mean', ".2f"),
            ("Median", 'median', ".2f"),
            ("P95", 'p95', ".2f"),
            ("Max", 'max', ""),
            ("StDev", 'stdev', ".2f"),
            ("Variance", 'var', ".2f"),
            ("Count", 'count', ""),
            ("CV (%)", 'cv', ".2f")
        ]

        # Layout Principal
        self.grid_columnconfigure(0, weight=0, minsize=260) # Sidebar
        self.grid_columnconfigure(1, weight=1)              # Main Area
        self.grid_rowconfigure(0, weight=1)

        self.criar_sidebar()
        
        # Container Principal (Direita)
        self.frm_main_container = ctk.CTkFrame(self, fg_color=CORES_CREATOR["main_bg"], corner_radius=0)
        self.frm_main_container.grid(row=0, column=1, sticky="nsew")
        
        self.frm_main_container.grid_rowconfigure(1, weight=1)
        self.frm_main_container.grid_columnconfigure(0, weight=1)

        # Header Global 
        self.criar_header_global()
        
        # Area de Conteudo (Views)
        self.frm_content = ctk.CTkFrame(self.frm_main_container, fg_color="transparent")
        self.frm_content.grid(row=1, column=0, sticky="nsew")
        self.frm_content.grid_rowconfigure(0, weight=1)
        self.frm_content.grid_columnconfigure(0, weight=1)

        # Inicializa as views
        self.criar_general_view()
        self.criar_sheet_view()
        self.criar_area_estatisticas()
        
        # Mostra General por padrao
        self.mostrar_general()

    def ao_fechar(self):
        self.destroy()

    def carregar_icones(self):
        try:
            caminho_script = os.path.dirname(os.path.abspath(__file__))
            caminho_pai = os.path.dirname(caminho_script)
            caminho_img = os.path.join(caminho_pai, "assets", "discket.png")
            pil_img = Image.open(caminho_img)
            self.icon_save = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(20, 20))
        except Exception as e:
            self.icon_save = None

    # =========================================================================
    # --- FUNÇÕES DE LÓGICA DO HEATMAP ---
    # =========================================================================
    def _get_cor_heatmap(self, valor, v_min, v_max):
        if v_max == v_min: return None
        try: ratio = (valor - v_min) / (v_max - v_min)
        except ZeroDivisionError: return None
        
        start_rgb = (230, 230, 230) 
        end_rgb = self.hex_to_rgb(self.cor_heatmap_atual)
        
        r = int(start_rgb[0] + (end_rgb[0] - start_rgb[0]) * ratio)
        g = int(start_rgb[1] + (end_rgb[1] - start_rgb[1]) * ratio)
        b = int(start_rgb[2] + (end_rgb[2] - start_rgb[2]) * ratio)
        return f"#{r:02x}{g:02x}{b:02x}"

    def hex_to_rgb(self, hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def escolher_cor_heatmap(self):
        color = askcolor(color=self.cor_heatmap_atual, title="Choose Heatmap Max Color", parent=self)[1]
        if color:
            self.cor_heatmap_atual = color
            self.btn_cor_picker.configure(fg_color=color, hover_color=color)
            self.chk_heatmap.configure(fg_color=color)
            if self.var_heatmap.get():
                self.aplicar_heatmap_visual()

    def aplicar_heatmap_visual(self):
        if not Sheet or not hasattr(self, 'sheet') or not self.dados["created"]: return
        
        try: self.sheet.dehighlight_all() 
        except: pass 

        if not self.var_heatmap.get():
            self.sheet.refresh()
            return

        try:
            data = self.sheet.get_sheet_data()
            if not data: return
            
            vals = []
            for row in data:
                for c in row:
                    try: vals.append(float(c))
                    except: pass
            
            if not vals: return
            v_min = min(vals)
            v_max = max(vals)
            
            for r_idx, row in enumerate(data):
                for c_idx, val in enumerate(row):
                    try:
                        v = float(val)
                        if v == 0 and self.selecao_atual[0] == "setup":
                            continue
                            
                        cor_bg_hex = self._get_cor_heatmap(v, v_min, v_max)
                        
                        if cor_bg_hex:
                            bg_rgb = self.hex_to_rgb(cor_bg_hex)
                            luminance = (0.299 * bg_rgb[0] + 0.587 * bg_rgb[1] + 0.114 * bg_rgb[2])
                            cor_texto = "white" if luminance < 130 else "black"
                            self.sheet.highlight_cells(row=r_idx, column=c_idx, bg=cor_bg_hex, fg=cor_texto, redraw=False)
                    except ValueError: pass 

            self.sheet.refresh() 
        except Exception as e:
            print(f"ERRO Heatmap: {e}")

    def ao_finalizar_edicao(self, event):
        """Recalcula o heatmap assim que a edição da célula termina."""
        if hasattr(self, 'var_heatmap') and self.var_heatmap.get():
            self.aplicar_heatmap_visual()

    # SIDEBAR 
    def criar_sidebar(self):
        self.frm_side = ctk.CTkFrame(self, fg_color=CORES_CREATOR["sidebar_bg"], corner_radius=0, width=260)
        self.frm_side.grid(row=0, column=0, sticky="nsew")
        self.frm_side.grid_rowconfigure(0, weight=1)
        self.frm_side.grid_columnconfigure(0, weight=1)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Creator.Treeview", 
                        background=CORES_CREATOR["sidebar_bg"],
                        foreground="white",
                        fieldbackground=CORES_CREATOR["sidebar_bg"],
                        borderwidth=0, font=("Roboto", 11))
        style.map('Creator.Treeview', background=[('selected', '#444444')], foreground=[('selected', 'white')])

        self.tree = ttk.Treeview(self.frm_side, show="tree", style="Creator.Treeview", selectmode="browse")
        self.tree.grid(row=0, column=0, sticky="nsew", padx=10, pady=20)
        
        scroll = ctk.CTkScrollbar(self.frm_side, command=self.tree.yview, width=8, fg_color="transparent")
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.grid(row=0, column=1, sticky="ns")

        # Nós Fixos
        self.node_general = self.tree.insert("", "end", text=" ⚙️ General Settings", values=("general", "root"))
        self.node_proc = self.tree.insert("", "end", text=" 📂 Processing Times", values=("proc", "root"))
        self.node_setup = self.tree.insert("", "end", text=" 📂 Setup Times", values=("setup", "root"))
        self.node_stats = self.tree.insert("", "end", text=" 📊 Statistics", values=("stats", "root"))

        self.tree.selection_set(self.node_general)
        self.tree.bind("<<TreeviewSelect>>", self.ao_selecionar_tree)

    def criar_header_global(self):
        self.frm_header = ctk.CTkFrame(self.frm_main_container, height=80, fg_color=CORES_CREATOR["card_bg"], corner_radius=0)
        self.frm_header.grid(row=0, column=0, sticky="ew")
        
        # Inputs de Range (Min/Max)
        lbl_range = ctk.CTkLabel(self.frm_header, text="Range:", font=("Roboto", 12, "bold"))
        lbl_range.pack(side="left", padx=(15, 5))
        
        self.ent_min = ctk.CTkEntry(self.frm_header, width=50, placeholder_text="Min")
        self.ent_min.insert(0, "10")
        self.ent_min.pack(side="left", padx=2)
        
        ctk.CTkLabel(self.frm_header, text="-").pack(side="left", padx=2)
        
        self.ent_max = ctk.CTkEntry(self.frm_header, width=50, placeholder_text="Max")
        self.ent_max.insert(0, "100")
        self.ent_max.pack(side="left", padx=2)
        
        # Separador visual
        ctk.CTkFrame(self.frm_header, width=2, height=30, fg_color="gray30").pack(side="left", padx=15)

        # --- HEATMAP CONTROLS ---
        self.frm_heatmap = ctk.CTkFrame(self.frm_header, fg_color="transparent")
        self.frm_heatmap.pack(side="left", padx=(0, 15)) # Empacotado antes dos botões de Randomize

        self.var_heatmap = ctk.BooleanVar(value=False)
        self.chk_heatmap = ctk.CTkCheckBox(self.frm_heatmap, text="Heatmap", variable=self.var_heatmap, command=self.aplicar_heatmap_visual, font=("Roboto", 12, "bold"), text_color="white", fg_color="#E74C3C", hover_color="#C0392B")
        self.chk_heatmap.pack(side="left", padx=(0, 10))

        self.cor_heatmap_atual = "#E74C3C" 
        self.btn_cor_picker = ctk.CTkButton(self.frm_heatmap, text="", width=30, height=30, fg_color=self.cor_heatmap_atual, hover_color=self.cor_heatmap_atual, command=self.escolher_cor_heatmap, corner_radius=4, border_width=1, border_color="white")
        self.btn_cor_picker.pack(side="left")

        # --- BOTOES DE RANDOMIZE ---
        self.btn_rand_sel = ctk.CTkButton(self.frm_header, text="RANDOMIZE SELECTED CELLS", width=140,
                                          fg_color=CORES_CREATOR["btn_primary"], hover_color=CORES_CREATOR["btn_hover"],
                                          state="disabled", command=self.acao_randomizar_selecionado)
        self.btn_rand_sel.pack(side="left", padx=(0, 5))

        self.btn_rand_tab = ctk.CTkButton(self.frm_header, text="RANDOMIZE TAB", width=120,
                                          fg_color=CORES_CREATOR["btn_primary"], hover_color=CORES_CREATOR["btn_hover"],
                                          state="disabled", command=self.acao_randomizar_tab)
        self.btn_rand_tab.pack(side="left", padx=(0, 5))

        self.btn_rand_all_setups = ctk.CTkButton(self.frm_header, text="RANDOMIZE ALL SETUPS", width=160,
                                          fg_color=CORES_CREATOR["btn_action"], hover_color=CORES_CREATOR["btn_action_hover"],
                                          state="disabled", command=self.acao_randomizar_todos_setups_global)
        self.btn_rand_all_setups.pack(side="left", padx=(0, 10))

        # Save Button
        self.btn_save = ctk.CTkButton(self.frm_header, text="SAVE", image=self.icon_save, compound="left", width=90, fg_color="green", hover_color="darkgreen", state="disabled", command=self.acao_salvar_arquivo)
        self.btn_save.pack(side="right", padx=15)
        
        self.lbl_status = ctk.CTkLabel(self.frm_header, text="", font=("Roboto", 12, "italic"))
        self.lbl_status.pack(side="right", padx=10)

    def criar_general_view(self):
        self.frm_general = ctk.CTkFrame(self.frm_content, fg_color="transparent")
        
        ctk.CTkLabel(self.frm_general, text="GENERAL SETTINGS", font=("Roboto", 24, "bold"), text_color="white").pack(pady=(60, 30))

        box_dim = ctk.CTkFrame(self.frm_general, fg_color=CORES_CREATOR["card_bg"], corner_radius=10)
        box_dim.pack(padx=40, pady=10)
        
        ctk.CTkLabel(box_dim, text="Instance Dimensions", font=("Roboto", 14, "bold"), text_color=CORES_CREATOR["text_highlight"]).pack(padx=20, pady=15)
        
        frm_inputs = ctk.CTkFrame(box_dim, fg_color="transparent")
        frm_inputs.pack(padx=20, pady=(0, 20))
        
        ctk.CTkLabel(frm_inputs, text="Machines (M):").pack(side="left", padx=(0, 10))
        self.ent_machines = ctk.CTkEntry(frm_inputs, width=80, placeholder_text="Ex: 5")
        self.ent_machines.pack(side="left", padx=(0, 30))
        
        ctk.CTkLabel(frm_inputs, text="Jobs (N):").pack(side="left", padx=(0, 10))
        self.ent_jobs = ctk.CTkEntry(frm_inputs, width=80, placeholder_text="Ex: 20")
        self.ent_jobs.pack(side="left", padx=(0, 30))

        self.btn_gen_empty = ctk.CTkButton(self.frm_general, text="GENERATE STRUCTURE", height=45, width=300,
                                           font=("Roboto", 13, "bold"),
                                           fg_color=CORES_CREATOR["btn_action"], hover_color=CORES_CREATOR["btn_action_hover"],
                                           command=self.acao_gerar_vazia)
        self.btn_gen_empty.pack(pady=30)
        
        ctk.CTkLabel(self.frm_general, text="Note: Generating a new structure will reset all current data.", text_color="gray").pack()

    def criar_sheet_view(self):
        self.frm_sheet = ctk.CTkFrame(self.frm_content, fg_color=CORES_CREATOR["grid_bg"])
        
        frm_header = ctk.CTkFrame(self.frm_sheet, height=30, fg_color="transparent")
        frm_header.pack(fill="x", padx=10, pady=5)
        self.lbl_sheet_title = ctk.CTkLabel(frm_header, text="VIEWING MODE", font=("Roboto", 12, "bold"), text_color=CORES_CREATOR["text_highlight"])
        self.lbl_sheet_title.pack(side="left")

        self.sheet_container = ctk.CTkFrame(self.frm_sheet, fg_color=CORES_CREATOR["grid_bg"])
        self.sheet_container.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        if Sheet:
            self.sheet = Sheet(self.sheet_container, headers=[], data=[], theme="dark", empty_horizontal=0, empty_vertical=0)
            self.sheet.enable_bindings(("single_select",
                                         "row_select",
                                         "column_select",
                                         "drag_select",
                                         "arrowkeys",
                                         "edit_cell",     
                                         "delete",        
                                         "copy",          
                                         "paste",          
                                         "undo"))
            # --- FIX: Adicionado Binding do Heatmap aqui ---
            self.sheet.extra_bindings([("end_edit_cell", self.ao_finalizar_edicao)])

            self.sheet.set_options(
                table_bg = CORES_CREATOR["sheet_bg"],
                table_fg = CORES_CREATOR["sheet_fg"],
                table_grid_fg = CORES_CREATOR["sheet_grid"],
                header_bg = CORES_CREATOR["sheet_header_bg"],
                header_fg = CORES_CREATOR["sheet_header_fg"],
                index_bg = CORES_CREATOR["sheet_header_bg"], 
                index_fg = CORES_CREATOR["sheet_header_fg"],
                frame_bg = CORES_CREATOR["sheet_header_bg"],
                top_left_bg = CORES_CREATOR["sheet_header_bg"],
                selection_bg = CORES_CREATOR["sheet_select_bg"],
                header_selected_bg = CORES_CREATOR["sheet_select"],
                index_selected_bg = CORES_CREATOR["sheet_select"],
                font = ("Arial", 10, "normal"),
                header_font = ("Arial", 10, "bold"),
                index_font = ("Arial", 10, "bold"),
                default_column_width = 60 
            )
            self.sheet.pack(fill="both", expand=True)

    def criar_area_estatisticas(self):
        self.frm_stats_container = ctk.CTkScrollableFrame(self.frm_content, fg_color="transparent")
        self.frm_stats_container.grid_rowconfigure(0, weight=0) 
        self.frm_stats_container.grid_rowconfigure(1, weight=0) 
        self.frm_stats_container.grid_rowconfigure(2, weight=0) 
        self.frm_stats_container.grid_columnconfigure(0, weight=1)
        
        self.frm_controls = ctk.CTkFrame(self.frm_stats_container, fg_color="transparent")
        self.frm_controls.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))
        
        ctk.CTkLabel(self.frm_controls, text="Table Layout:", font=("Roboto", 12, "bold")).pack(side="left", padx=(0, 10))
        self.cmb_layout = ctk.CTkComboBox(self.frm_controls, values=["Horizontal", "Vertical"], variable=self.layout_var, command=self.ao_mudar_layout_tabela, width=120, state="readonly")
        self.cmb_layout.pack(side="left")
        
        self.subfrm_graphs = ctk.CTkFrame(self.frm_stats_container, fg_color="transparent")
        self.subfrm_graphs.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
        self.subfrm_table = ctk.CTkFrame(self.frm_stats_container, fg_color=CORES_CREATOR["grid_bg"], corner_radius=6)
        self.subfrm_table.grid(row=2, column=0, sticky="ew", padx=10, pady=(10, 40))

    def ao_mudar_layout_tabela(self, escolha):
        if self.selecao_atual and self.selecao_atual[0].startswith("stats"):
            tipo, tag = self.selecao_atual
            maquina = None if tag == "root" else int(tag)
            self.gerar_tabela_estatistica(maquina_foco=maquina)

    # --- CONTROLE DE VIEWS ---
    def mostrar_general(self):
        self.frm_sheet.pack_forget()
        self.frm_stats_container.pack_forget()
        self.frm_general.pack(fill="both", expand=True)
    
    def mostrar_sheet(self):
        self.frm_general.pack_forget()
        self.frm_stats_container.pack_forget()
        self.frm_sheet.pack(fill="both", expand=True)

    def mostrar_stats(self):
        self.frm_general.pack_forget()
        self.frm_sheet.pack_forget()
        self.frm_stats_container.pack(fill="both", expand=True)

    def salvar_alteracoes_da_view_atual(self):
        """Salva na memoria os dados caso o usuario tenha editado alguma celula na mao"""
        if not self.dados["created"] or not self.selecao_atual: return
        tipo, tag = self.selecao_atual
        if tipo.startswith("stats") or tipo == "general": return
        if not Sheet or not hasattr(self, 'sheet'): return

        dados_visuais = self.sheet.get_sheet_data()
        if not dados_visuais: return
        
        try:
            dados_int = [[int(c) for c in linha] for linha in dados_visuais]
        except ValueError:
            return 

        if tipo == "proc":
            self.dados["processing"] = dados_int
        elif tipo == "setup":
            try:
                maquina_id = int(tag)
                self.dados["setup"][maquina_id] = dados_int
            except ValueError:
                pass

    def ao_selecionar_tree(self, event):
        sel = self.tree.selection()
        if not sel: return
        
        self.salvar_alteracoes_da_view_atual()
        
        item = self.tree.item(sel[0])
        tipo = item['values'][0]
        tag = item['values'][1]
        
        self.selecao_atual = (tipo, tag)

        # --- CONTROLE DE VISIBILIDADE DO HEATMAP ---
        if tipo == "general" or tipo.startswith("stats"):
            self.frm_heatmap.pack_forget()
        else:
            self.frm_heatmap.pack(side="left", padx=(0, 15), before=self.btn_rand_sel) # Coloca no lugar exato
        # -------------------------------------------

        if tipo == "general":
            self.mostrar_general()
            self.btn_rand_sel.configure(state="disabled")
            self.btn_rand_tab.configure(state="disabled")
            self.btn_rand_all_setups.configure(state="disabled")
            
        elif tipo.startswith("stats"):
            if not self.dados["created"]:
                self.tree.selection_set(self.node_general)
                tk.messagebox.showwarning("Warning", "Please generate the structure first.", parent=self)
                return
                
            self.mostrar_stats()
            self.btn_rand_sel.configure(state="disabled")
            self.btn_rand_tab.configure(state="disabled")
            self.btn_rand_all_setups.configure(state="disabled")
            
            if tipo == "stats":
                self.gerar_graficos_estatisticas(maquina_idx=None)
                self.gerar_tabela_estatistica(maquina_foco=None)
            else:
                try:
                    m_idx = int(tag)
                    self.gerar_graficos_estatisticas(maquina_idx=m_idx)
                    self.gerar_tabela_estatistica(maquina_foco=m_idx)
                except ValueError: pass

        else:
            if not self.dados["created"]:
                self.tree.selection_set(self.node_general)
                tk.messagebox.showwarning("Warning", "Please generate the structure first.", parent=self)
                return
            
            self.btn_rand_sel.configure(state="normal")
            self.btn_rand_tab.configure(state="normal")
            
            if tipo == "proc":
                self.btn_rand_all_setups.configure(state="disabled")
            else:
                self.btn_rand_all_setups.configure(state="normal")
            
            self.mostrar_sheet()
            if tipo == "proc":
                self.carregar_proc_sheet()
            elif tipo == "setup" and tag != "root":
                self.carregar_setup_sheet(int(tag))

    # =========================================================================
    # --- FUNÇÕES DE MATEMÁTICA E RENDERIZAÇÃO ESTATÍSTICA ---
    # =========================================================================
    def calcular_percentil(self, dados_lista, percentil=0.95):
        if not dados_lista: return 0
        dados_sorted = sorted(dados_lista)
        k = (len(dados_lista) - 1) * percentil
        f = math.floor(k)
        c = math.ceil(k)
        if f == c: return dados_sorted[int(k)]
        d0 = dados_sorted[int(f)] * (c - k)
        d1 = dados_sorted[int(c)] * (k - f)
        return d0 + d1

    def _get_dados_raw(self, tipo_dado, maquina_idx):
        dados_flat = []
        if tipo_dado == "proc":
            if maquina_idx is None:
                try: dados_flat = np.array(self.dados["processing"]).flatten().tolist()
                except: pass
            else:
                try: dados_flat = self.dados["processing"][int(maquina_idx)]
                except: pass
        else: 
            s_dict = self.dados.get("setup", {})
            if maquina_idx is None: 
                try:
                    all_setups = []
                    for matriz in s_dict.values():
                        vals = [x for x in np.array(matriz).flatten() if x > 0]
                        all_setups.extend(vals)
                    dados_flat = all_setups
                except: pass
            else: 
                matriz = None
                try: matriz = s_dict.get(int(maquina_idx))
                except: pass
                if matriz is None: matriz = s_dict.get(str(maquina_idx))

                if matriz is not None:
                    if isinstance(matriz, list):
                        try:
                            flat_vals = np.array(matriz).flatten()
                            filtrados = [x for x in flat_vals if x > 0]
                            if len(filtrados) == 0: dados_flat = [0]
                            else: dados_flat = filtrados
                        except Exception: dados_flat = []
        return dados_flat

    def _calcular_stats(self, lista_valores):
        if not lista_valores: return None
        try:
            dados_clean = [float(x) for x in lista_valores]
            n = len(dados_clean)
            if n < 2:
                val = dados_clean[0]
                return {'count': n, 'min': val, 'max': val, 'mean': val, 'median': val, 'stdev': 0.0, 'var': 0.0, 'cv': 0.0, 'p95': val}

            media = statistics.mean(dados_clean)
            desvio = statistics.stdev(dados_clean)
            cv = (desvio / media * 100) if abs(media) > 1e-9 else 0.0
            
            stats = {
                'count': n,
                'min': min(dados_clean),
                'max': max(dados_clean),
                'mean': media,
                'median': statistics.median(dados_clean),
                'stdev': desvio,
                'var': statistics.variance(dados_clean),
                'cv': cv,
                'p95': self.calcular_percentil(dados_clean, 0.95)
            }
            return stats
        except Exception:
            return None

    def gerar_graficos_estatisticas(self, maquina_idx=None):
        for w in self.subfrm_graphs.winfo_children(): w.destroy()
        if self.fig_stats: plt.close(self.fig_stats); self.fig_stats = None
        if not self.dados["created"]: return

        proc_flat = self._get_dados_raw("proc", maquina_idx)
        setup_flat = self._get_dados_raw("setup", maquina_idx)
        
        titulo_sufixo = "Global" if maquina_idx is None else f"Machine {maquina_idx}"

        plt.style.use('dark_background')
        
        self.fig_stats, axes = plt.subplots(2, 2, figsize=(10, 6), dpi=100, 
                                            sharex='col', 
                                            gridspec_kw={'height_ratios': [0.60, 0.40], 'hspace': 0.4, 'wspace': 0.2})
        
        self.fig_stats.patch.set_facecolor(CORES_CREATOR["main_bg"]) 
        (ax_hist_p, ax_hist_s), (ax_box_p, ax_box_s) = axes
        cor_proc, cor_setup = ('#9C27B0', '#FF9800') if maquina_idx is not None else ('#5CAEC4', '#E74C3C')
        cor_grid = CORES_CREATOR["grid_bg"]

        # --- GRÁFICO 1: Processing Times ---
        ax_hist_p.set_facecolor(cor_grid)
        if len(proc_flat) > 0:
            ax_hist_p.hist(proc_flat, bins=15, color=cor_proc, edgecolor='black', alpha=0.8)
            media_p = np.mean(proc_flat)
            ax_hist_p.axvline(media_p, color='white', linestyle='dashed', linewidth=1, label=f'Avg: {media_p:.1f}')
            ax_hist_p.legend(fontsize=7, facecolor=cor_grid, edgecolor="white", loc='upper right')
            
        ax_hist_p.set_title(f"Processing Times ({titulo_sufixo})", fontsize=10, color="white", fontweight="bold")
        ax_hist_p.set_ylabel("Freq.", fontsize=8, color="gray")
        ax_hist_p.grid(axis='y', alpha=0.2, linestyle='--')
        ax_hist_p.tick_params(axis='x', labelbottom=True) 
        
        ax_box_p.set_facecolor(cor_grid)
        if len(proc_flat) > 0:
            props = dict(color='white')
            flier_props = dict(marker='o', markerfacecolor='white', markersize=3, linestyle='none', markeredgecolor='none')
            ax_box_p.boxplot(proc_flat, vert=False, patch_artist=True, 
                             boxprops=dict(facecolor=cor_proc, alpha=0.6), 
                             medianprops=props, capprops=props, whiskerprops=props, flierprops=flier_props,
                             widths=0.5)
        ax_box_p.set_yticks([]); ax_box_p.set_xlabel("Time Unit", fontsize=9, color="gray")
        ax_box_p.grid(axis='x', alpha=0.2, linestyle='--')
        ax_box_p.set_title("Distribution Boxplot", fontsize=9, color="gray", pad=5)

        # --- GRÁFICO 2: Setup Times ---
        ax_hist_s.set_facecolor(cor_grid)
        if len(setup_flat) > 0:
            ax_hist_s.hist(setup_flat, bins=20, color=cor_setup, edgecolor='black', alpha=0.8)
            media_s = np.mean(setup_flat)
            ax_hist_s.axvline(media_s, color='white', linestyle='dashed', linewidth=1, label=f'Avg: {media_s:.1f}')
            ax_hist_s.legend(fontsize=7, facecolor=cor_grid, edgecolor="white", loc='upper right')
        else: 
            ax_hist_s.text(0.5, 0.5, "No Data", ha='center', va='center', color='gray')
            
        ax_hist_s.set_title(f"Setup Times ({titulo_sufixo})", fontsize=10, color="white", fontweight="bold")
        ax_hist_s.grid(axis='y', alpha=0.2, linestyle='--')
        ax_hist_s.tick_params(axis='x', labelbottom=True)

        ax_box_s.set_facecolor(cor_grid)
        if len(setup_flat) > 0:
            props = dict(color='white')
            flier_props = dict(marker='o', markerfacecolor='white', markersize=3, linestyle='none', markeredgecolor='none')
            ax_box_s.boxplot(setup_flat, vert=False, patch_artist=True, 
                             boxprops=dict(facecolor=cor_setup, alpha=0.6), 
                             medianprops=props, capprops=props, whiskerprops=props, flierprops=flier_props,
                             widths=0.5)
        ax_box_s.set_yticks([]); ax_box_s.set_xlabel("Time Unit", fontsize=9, color="gray")
        ax_box_s.grid(axis='x', alpha=0.2, linestyle='--')
        ax_box_s.set_title("Distribution Boxplot", fontsize=9, color="gray", pad=5)

        self.fig_stats.subplots_adjust(left=0.08, right=0.95, top=0.92, bottom=0.15, wspace=0.2, hspace=0.4)

        self.canvas_stats = FigureCanvasTkAgg(self.fig_stats, master=self.subfrm_graphs)
        self.canvas_stats.draw()
        self.canvas_stats.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
        
        self.toolbar_stats = CustomToolbar(self.canvas_stats, self.subfrm_graphs)
        self.toolbar_stats.update(); self.toolbar_stats.pack(side="bottom", fill="x", pady=5)

    def gerar_tabela_estatistica(self, maquina_foco=None):
        for w in self.subfrm_table.winfo_children(): w.destroy()
        if not self.dados["created"]: return

        layout = self.layout_var.get()
        
        C_PROC = "#5CAEC4" if maquina_foco is None else "#9C27B0"
        C_SETUP = "#E74C3C" if maquina_foco is None else "#FF9800"
        
        suffix = "(Global)" if maquina_foco is None else f"(Machine {maquina_foco})"
        t_proc = f"PROCESSING TIMES {suffix}"
        t_setup = f"SETUP TIMES {suffix}"
        
        use_side_by_side = (maquina_foco is not None)
        
        if use_side_by_side:
            frm_container = ctk.CTkFrame(self.subfrm_table, fg_color="transparent")
            frm_container.pack(fill="both", expand=True)
            frm_container.grid_columnconfigure(0, weight=1); frm_container.grid_columnconfigure(1, weight=1)
            
            f_left = ctk.CTkFrame(frm_container, fg_color="transparent")
            f_left.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
            
            f_right = ctk.CTkFrame(frm_container, fg_color="transparent")
            f_right.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
            
            self._construir_tabela_dinamica(f_left, t_proc, "proc", maquina_foco, C_PROC, layout)
            self._construir_tabela_dinamica(f_right, t_setup, "setup", maquina_foco, C_SETUP, layout)
        else:
            f_top = ctk.CTkFrame(self.subfrm_table, fg_color="transparent")
            f_top.pack(fill="x", pady=(0, 20))
            self._construir_tabela_dinamica(f_top, t_proc, "proc", maquina_foco, C_PROC, layout)
            
            ttk.Separator(self.subfrm_table, orient="horizontal").pack(fill="x", padx=20, pady=10)
            
            f_bot = ctk.CTkFrame(self.subfrm_table, fg_color="transparent")
            f_bot.pack(fill="x", pady=(10, 0))
            self._construir_tabela_dinamica(f_bot, t_setup, "setup", maquina_foco, C_SETUP, layout)

    def _construir_tabela_dinamica(self, parent, titulo, tipo_dado, maquina_foco, cor_titulo, layout):
        ctk.CTkLabel(parent, text=titulo, font=("Roboto", 13, "bold"), text_color=cor_titulo).pack(pady=(0, 5), anchor="w")
        grid = ctk.CTkFrame(parent, fg_color="#1A1A1D", border_width=1, border_color="#333333")
        grid.pack(fill="x", expand=True)

        lista_entidades = []
        if maquina_foco is None:
            lista_entidades.append(("GLOBAL", self._get_dados_raw(tipo_dado, None), False))
            for m in range(self.dados["M"]):
                lista_entidades.append((f"M{m}", self._get_dados_raw(tipo_dado, m), False))
        else:
            lista_entidades.append(("Current", self._get_dados_raw(tipo_dado, maquina_foco), False))

        cache_stats = []
        medias_maquinas = []
        for nome_ent, dados_raw, _ in lista_entidades:
            st = self._calcular_stats(dados_raw)
            cache_stats.append(st)
            if st is not None and nome_ent not in ("GLOBAL", "Current"):
                medias_maquinas.append(st['mean'])

        min_mean = min(medias_maquinas) if medias_maquinas else None
        max_mean = max(medias_maquinas) if len(medias_maquinas) > 1 else None

        if layout == "Horizontal":
            headers = ["Scope"] + [item[0] for item in self.STATS_CONFIG]
            for i, h in enumerate(headers):
                bg = "#333333"
                lbl = ctk.CTkLabel(grid, text=h, font=("Roboto", 11, "bold"), text_color="white", fg_color=bg, corner_radius=4)
                lbl.grid(row=0, column=i, sticky="ew", padx=1, pady=1, ipady=3)
                grid.grid_columnconfigure(i, weight=1)

            for r_idx, (nome_entidade, _, destaque) in enumerate(lista_entidades):
                row = r_idx + 1
                stats = cache_stats[r_idx]
                bg_row = "#1F1F1F" if destaque else ("#2b2b2b" if row % 2 == 0 else "transparent")
                fg_row = cor_titulo if destaque else ("silver" if row % 2 == 0 else "gray70")
                ctk.CTkLabel(grid, text=nome_entidade, font=("Roboto", 11), text_color=fg_row, fg_color=bg_row).grid(row=row, column=0, sticky="ew", padx=1, pady=1)
                
                if stats:
                    for c_idx, (_, key, fmt) in enumerate(self.STATS_CONFIG):
                        val_raw = stats[key]
                        val_txt = f"{val_raw:{fmt}}" if fmt else str(val_raw)
                        if key == 'cv': val_txt += "%"
                        cor_cell = fg_row
                        font_w = "normal"
                        
                        if key == 'mean' and nome_entidade not in ("GLOBAL", "Current") and min_mean != max_mean:
                            if val_raw == min_mean: cor_cell = "#2ECC71"; font_w = "bold"
                            elif val_raw == max_mean: cor_cell = "#E74C3C"; font_w = "bold"
                        
                        ctk.CTkLabel(grid, text=val_txt, font=("Roboto", 11, font_w), text_color=cor_cell, fg_color=bg_row).grid(row=row, column=c_idx+1, sticky="ew", padx=1, pady=1)
                else:
                    for c_idx in range(len(self.STATS_CONFIG)):
                        ctk.CTkLabel(grid, text="-", text_color="gray", fg_color=bg_row).grid(row=row, column=c_idx+1, sticky="ew", padx=1, pady=1)
        else:
            ctk.CTkLabel(grid, text="Metric", font=("Roboto", 11, "bold"), text_color="white", fg_color="#333333").grid(row=0, column=0, sticky="ew", padx=1, pady=1, ipady=3)
            grid.grid_columnconfigure(0, weight=0, minsize=80) 
            
            for i, (nome_ent, _, _) in enumerate(lista_entidades):
                ctk.CTkLabel(grid, text=nome_ent, font=("Roboto", 11, "bold"), text_color="white", fg_color="#333333").grid(row=0, column=i+1, sticky="ew", padx=1, pady=1, ipady=3)
                grid.grid_columnconfigure(i+1, weight=1)

            for r_idx, (label_stat, key, fmt) in enumerate(self.STATS_CONFIG):
                row = r_idx + 1
                bg_row = "#2b2b2b" if row % 2 == 0 else "transparent"
                ctk.CTkLabel(grid, text=label_stat, font=("Roboto", 11, "bold"), text_color="silver", fg_color=bg_row, anchor="w").grid(row=row, column=0, sticky="ew", padx=(10,5), pady=1)
                
                for c_idx, stats in enumerate(cache_stats):
                    val_txt = "-"
                    cor_cell = "silver"
                    font_w = "normal"
                    nome_entidade = lista_entidades[c_idx][0]
                    
                    if stats:
                        val_raw = stats[key]
                        val_txt = f"{val_raw:{fmt}}" if fmt else str(val_raw)
                        if key == 'cv': val_txt += "%"
                        
                        if key == 'mean' and nome_entidade not in ("GLOBAL", "Current") and min_mean != max_mean:
                            if val_raw == min_mean: cor_cell = "#2ECC71"; font_w = "bold"
                            elif val_raw == max_mean: cor_cell = "#E74C3C"; font_w = "bold"
                            
                    ctk.CTkLabel(grid, text=val_txt, font=("Roboto", 11, font_w), text_color=cor_cell, fg_color=bg_row).grid(row=row, column=c_idx+1, sticky="ew", padx=1, pady=1)

    # --- GERADOR E COMANDOS DE DADOS ---
    def _get_range(self):
        try:
            v_min = int(self.ent_min.get())
            v_max = int(self.ent_max.get())
            if v_min > v_max: raise ValueError
            return v_min, v_max
        except:
            self.lbl_status.configure(text="Error: Invalid Range", text_color="red")
            return None, None

    def acao_gerar_vazia(self):
        if self.dados["created"]:
            try:
                confirm = tk.messagebox.askyesno("Confirm Reset", "Are you sure you want to generate a new structure?\nAll current data will be lost.", parent=self)
                if not confirm: return
            except tk.TclError: return

        try:
            M = int(self.ent_machines.get())
            N = int(self.ent_jobs.get())
            if M <= 0 or N <= 0: raise ValueError
        except:
            self.lbl_status.configure(text="Error: Invalid M/N inputs", text_color="red")
            return

        self.dados["M"] = M
        self.dados["N"] = N
        self.dados["processing"] = [[0]*N for _ in range(M)]
        self.dados["setup"] = {m: [[0]*N for _ in range(N)] for m in range(M)}
        self.dados["created"] = True

        # Atualiza a arvore
        filhos_setup = self.tree.get_children(self.node_setup)
        for f in filhos_setup: self.tree.delete(f)
        filhos_stats = self.tree.get_children(self.node_stats)
        for f in filhos_stats: self.tree.delete(f)
        
        for m in range(M):
            self.tree.insert(self.node_setup, "end", text=f"    📁 M{m}", values=("setup", f"{m}"))
            self.tree.insert(self.node_stats, "end", text=f"    📊 M{m} Stats", values=("stats_mach", f"{m}"))

        self.btn_rand_all_setups.configure(state="normal")
        self.btn_save.configure(state="normal")
        self.lbl_status.configure(text=f"Structure ({M}x{N}) generated", text_color=CORES_CREATOR["success_text"])
        
        self.tree.item(self.node_setup, open=True)
        self.selecao_atual = ("proc", "root")     
        self.tree.selection_set(self.node_proc)   
        self.carregar_proc_sheet()                
        self.mostrar_sheet()                      
        
        self.btn_rand_sel.configure(state="normal")
        self.btn_rand_tab.configure(state="normal")

    def acao_randomizar_selecionado(self):
        if not self.dados["created"] or not Sheet: return
        v_min, v_max = self._get_range()
        if v_min is None: return

        try: selecionados = self.sheet.get_selected_cells(get_rows=True, get_columns=True, sort_by_row=True)
        except: return

        if not selecionados:
            self.lbl_status.configure(text="No cells selected.", text_color="orange")
            return

        tipo, tag = self.selecao_atual
        count = 0
        for row, col in selecionados:
            if tipo == "setup" and row == col: novo_valor = 0
            else: novo_valor = random.randint(v_min, v_max)

            self.sheet.set_cell_data(row, col, value=novo_valor, redraw=False)
            if tipo == "proc": self.dados["processing"][row][col] = novo_valor
            elif tipo == "setup": self.dados["setup"][int(tag)][row][col] = novo_valor
            count += 1

        # Atualiza heatmap
        if hasattr(self, 'var_heatmap') and self.var_heatmap.get():
            self.aplicar_heatmap_visual()
        else:
            self.sheet.refresh()
            
        self.lbl_status.configure(text=f"Randomized {count} selected cells.", text_color=CORES_CREATOR["success_text"])

    def acao_randomizar_tab(self):
        if not self.dados["created"]: return
        v_min, v_max = self._get_range()
        if v_min is None: return

        tipo, tag = self.selecao_atual
        N, M = self.dados["N"], self.dados["M"]
        
        if tipo == "proc":
            for r in range(M):
                for c in range(N):
                    self.dados["processing"][r][c] = random.randint(v_min, v_max)
            self.carregar_proc_sheet()
            self.lbl_status.configure(text="Tab: Processing Times randomized.", text_color=CORES_CREATOR["success_text"])

        elif tipo == "setup" and tag != "root":
            m_id = int(tag)
            for r in range(N):
                for c in range(N):
                    if r == c: self.dados["setup"][m_id][r][c] = 0
                    else: self.dados["setup"][m_id][r][c] = random.randint(v_min, v_max)
            self.carregar_setup_sheet(m_id)
            self.lbl_status.configure(text=f"Tab: Setup Times for M{m_id} randomized.", text_color=CORES_CREATOR["success_text"])

    def acao_randomizar_todos_setups_global(self):
        if not self.dados["created"]: return
        v_min, v_max = self._get_range()
        if v_min is None: return

        M, N = self.dados["M"], self.dados["N"]
        for m in range(M):
            for r in range(N):
                for c in range(N):
                    if r == c: self.dados["setup"][m][r][c] = 0
                    else: self.dados["setup"][m][r][c] = random.randint(v_min, v_max)

        tipo, tag = self.selecao_atual
        if tipo == "setup" and tag != "root":
            self.carregar_setup_sheet(int(tag))

        self.lbl_status.configure(text=f"SUCCESS: Randomized setups for ALL {M} machines.", text_color=CORES_CREATOR["success_text"])

    def acao_salvar_arquivo(self):
        if not self.dados["created"]: return
        self.salvar_alteracoes_da_view_atual() # Garante que os ultimos numeros digitados vao pro txt
        
        nome_sugerido = f"I_{self.dados['N']}_{self.dados['M']}_Generated.txt"
        caminho = filedialog.asksaveasfilename(parent=self, initialfile=nome_sugerido, defaultextension=".txt", filetypes=[("Text Files", "*.txt")])
        if not caminho: return

        try:
            N, M = self.dados["N"], self.dados["M"]
            p_matrix = self.dados["processing"]
            s_dict = self.dados["setup"]

            with open(caminho, "w") as f:
                f.write(f"{N}\t{M}\t1\n"); f.write(f"{M}\n")
                for j in range(N):
                    linha_txt = []
                    for m in range(M): linha_txt.append(f"{m}\t{p_matrix[m][j]}")
                    f.write("\t".join(linha_txt) + "\n")
                f.write("SSD\n")
                for m in range(M):
                    f.write(f"M{m}\n")
                    matriz = s_dict[m]
                    for row in matriz:
                        f.write("\t".join([str(v) for v in row]) + "\n")
            
            self.lbl_status.configure(text=f"Saved to: {os.path.basename(caminho)}", text_color=CORES_CREATOR["success_text"])
            tk.messagebox.showinfo("Success", "Instance saved successfully!", parent=self)

        except Exception as e:
            tk.messagebox.showerror("Error", f"Failed to save:\n{e}", parent=self)

    def carregar_proc_sheet(self):
        if not Sheet: return
        self.lbl_sheet_title.configure(text="PREVIEW: PROCESSING TIMES")
        dados = self.dados["processing"]
        N, M = self.dados["N"], self.dados["M"]
        self.sheet.headers([f"J{i}" for i in range(N)])
        self.sheet.row_index([f"M{i}" for i in range(M)])
        self.sheet.set_sheet_data(dados)
        
        if hasattr(self, 'var_heatmap') and self.var_heatmap.get():
            self.aplicar_heatmap_visual()

    def carregar_setup_sheet(self, m_id):
        if not Sheet: return
        self.lbl_sheet_title.configure(text=f"PREVIEW: SETUP TIMES (M{m_id})")
        dados = self.dados["setup"][m_id]
        N = self.dados["N"]
        self.sheet.headers([f"J{i}" for i in range(N)])
        self.sheet.row_index([f"J{i}" for i in range(N)])
        self.sheet.set_sheet_data(dados)
        
        if hasattr(self, 'var_heatmap') and self.var_heatmap.get():
            self.aplicar_heatmap_visual()

def abrir_creator_janela(root_parent=None):
    if root_parent: app = InstanceCreator(root_parent)
    else: app = InstanceCreator(None); app.mainloop()

if __name__ == "__main__":
    ctk.set_appearance_mode("Dark")
    abrir_creator_janela()