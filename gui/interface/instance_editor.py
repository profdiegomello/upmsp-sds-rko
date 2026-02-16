import customtkinter as ctk
from tkinter import ttk, filedialog, messagebox
import tkinter as tk
import os
from tkinter.colorchooser import askcolor
import sys
import statistics 
import math 

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import numpy as np

# Tenta importar o tksheet
try:
    from tksheet import Sheet
except ImportError:
    print("ERRO CRÍTICO: Biblioteca 'tksheet' não instalada.")
    Sheet = None 

# Toolbar customizada para corrigir o foco da janela ao salvar
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

CORES_EDITOR = {
    "sidebar_bg": "#2B2B30",       
    "main_bg": "#1A1A1D",          
    "header_bg": "#1A1A1D",        
    "btn_primary": "#3A5F75",      
    "btn_hover": "#4A7A95",
    "text_highlight": "#5CAEC4",
    "grid_bg": "#151516",
    
    # Cores tksheet
    "sheet_bg": "#151516",             
    "sheet_fg": "#E0E0E0",             
    "sheet_header_bg": "#2D2D35",      
    "sheet_header_fg": "#5CAEC4",      
    "sheet_grid": "#333333",           
    "sheet_select": "#6D28D9",         
    "sheet_select_bg": "#3c3c42",
}

class InstanceEditor(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)

        self.parent_app = parent 
        self.protocol("WM_DELETE_WINDOW", self.ao_fechar)
        
        self.title("RKO Instance Editor")
        self.geometry("1200x800") 
        
        self.dados_instancia = {
            "loaded": False,
            "N": 0, 
            "M": 0, 
            "processing": [], 
            "setup": {}       
        }
        
        self.view_atual = None
        self.canvas_stats = None 
        self.fig_stats = None
        self.toolbar_stats = None

        if os.name == 'nt':
            try: self.after(200, lambda: self.iconbitmap())
            except: pass
        self.focus_force()

        # Layout
        self.grid_columnconfigure(0, weight=0, minsize=260) 
        self.grid_columnconfigure(1, weight=1)              
        self.grid_rowconfigure(0, weight=1)
        
        # --- CONFIGURAÇÃO DE ORDEM E VARIÁVEL DE LAYOUT ---
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

        self.criar_sidebar()

        self.frm_main = ctk.CTkFrame(self, fg_color=CORES_EDITOR["main_bg"], corner_radius=0)
        self.frm_main.grid(row=0, column=1, sticky="nsew")
        self.frm_main.grid_rowconfigure(2, weight=1) 
        self.frm_main.grid_columnconfigure(0, weight=1)

        self.criar_header_botoes()
        self.criar_info_block()
        self.criar_tabela_sheet()
        self.criar_area_estatisticas()
        
    def _get_cor_heatmap(self, valor, v_min, v_max):
        """Retorna cor interpolada: Cinza Claro -> Cor Selecionada."""
        if v_max == v_min: return None
        
        try:
            ratio = (valor - v_min) / (v_max - v_min)
        except ZeroDivisionError:
            return None
        
        # Cor Inicial (Baixo): Cinza Claro (Gelo/Fundo Neutro)
        # Usando (230, 230, 230) dá um cinza bem claro, quase branco
        start_rgb = (230, 230, 230) 
        
        # Cor Final (Alto): A cor escolhida pelo usuário
        end_rgb = self.hex_to_rgb(self.cor_heatmap_atual)
        
        # Interpolação Linear Simples
        r = int(start_rgb[0] + (end_rgb[0] - start_rgb[0]) * ratio)
        g = int(start_rgb[1] + (end_rgb[1] - start_rgb[1]) * ratio)
        b = int(start_rgb[2] + (end_rgb[2] - start_rgb[2]) * ratio)
            
        return f"#{r:02x}{g:02x}{b:02x}"

    def hex_to_rgb(self, hex_color):
        """Converte '#RRGGBB' para tupla (r, g, b)"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def escolher_cor_heatmap(self):
        # Abre o seletor nativo
        color = askcolor(color=self.cor_heatmap_atual, title="Choose Heatmap Max Color", parent=self)[1]

        
        if color:
            self.cor_heatmap_atual = color
            
            # Atualiza a cor do botãozinho
            self.btn_cor_picker.configure(fg_color=color, hover_color=color)
            
            # Atualiza a cor do checkbox para combinar
            self.chk_heatmap.configure(fg_color=color)
            
            # Se o heatmap estiver ligado, reaplica imediatamente
            if self.var_heatmap.get():
                self.aplicar_heatmap_visual()

    def aplicar_heatmap_visual(self):
        if not self.sheet or not self.dados_instancia["loaded"]: return
        
        try:
            self.sheet.dehighlight_all() 
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
                        if v == 0 and self.view_atual[0] == "setup":
                            continue
                            
                        # Pega a cor de fundo calculada
                        cor_bg_hex = self._get_cor_heatmap(v, v_min, v_max)
                        
                        if cor_bg_hex:
                            # Calcula LUMINOSIDADE para decidir a cor do texto
                            # Converte hex de volta para RGB para calcular
                            bg_rgb = self.hex_to_rgb(cor_bg_hex)
                            
                            # Fórmula de Luminância (Percepção humana)
                            luminance = (0.299 * bg_rgb[0] + 0.587 * bg_rgb[1] + 0.114 * bg_rgb[2])
                            
                            # Se for escuro (< 128), texto branco. Se claro, texto preto.
                            # Usamos 100 como limiar para garantir bom contraste em cores médias
                            cor_texto = "white" if luminance < 130 else "black"
                            
                            self.sheet.highlight_cells(
                                row=r_idx, 
                                column=c_idx, 
                                bg=cor_bg_hex, 
                                fg=cor_texto,
                                redraw=False
                            )
                            
                    except ValueError: pass 

            self.sheet.refresh() 
            
        except Exception as e:
            print(f"ERRO Heatmap: {e}")

    def ao_fechar(self):
        self.destroy()
   
    def salvar_alteracoes_da_view_atual(self):
        if not self.dados_instancia["loaded"] or not self.view_atual: return
        tipo, tag = self.view_atual
        if tipo == "stats" or tipo == "stats_mach": return

        dados_visuais = self.sheet.get_sheet_data()
        try:
            dados_int = [[int(c) for c in linha] for linha in dados_visuais]
        except ValueError:
            messagebox.showerror("Format Error", "All cells must contain integer numbers.")
            return

        if tipo == "proc":
            self.dados_instancia["processing"] = dados_int
        elif tipo == "setup":
            try:
                maquina_id = int(tag)
                self.dados_instancia["setup"][maquina_id] = dados_int
            except ValueError:
                pass

    def criar_sidebar(self):
        self.frm_side = ctk.CTkFrame(self, fg_color=CORES_EDITOR["sidebar_bg"], corner_radius=0, width=260)
        self.frm_side.grid(row=0, column=0, sticky="nsew")
        self.frm_side.grid_rowconfigure(0, weight=1)
        self.frm_side.grid_columnconfigure(0, weight=1)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Sidebar.Treeview", background=CORES_EDITOR["sidebar_bg"], foreground="white", fieldbackground=CORES_EDITOR["sidebar_bg"], borderwidth=0, font=("Roboto", 11))
        style.map('Sidebar.Treeview', background=[('selected', '#444444')], foreground=[('selected', 'white')])

        self.tree_side = ttk.Treeview(self.frm_side, show="tree", style="Sidebar.Treeview", selectmode="browse")
        self.tree_side.grid(row=0, column=0, sticky="nsew", padx=10, pady=20)
        
        scroll_y = ctk.CTkScrollbar(self.frm_side, command=self.tree_side.yview, width=8, fg_color="transparent")
        self.tree_side.configure(yscrollcommand=scroll_y.set)
        scroll_y.grid(row=0, column=1, sticky="ns")

        self.node_proc = self.tree_side.insert("", "end", text=" 📂 Processing Times", open=True, values=("proc", "all"))
        self.node_setup = self.tree_side.insert("", "end", text=" 📂 Setup Times", open=True, values=("setup_root", "none"))
        self.node_stats = self.tree_side.insert("", "end", text=" 📊 Statistics", values=("stats", "all"))
        
        self.tree_side.bind("<<TreeviewSelect>>", self.ao_selecionar_sidebar)

    def criar_header_botoes(self):
        frm_btns = ctk.CTkFrame(self.frm_main, fg_color="transparent", height=50)
        frm_btns.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        
        # Botões Load/Save
        btn_load = ctk.CTkButton(frm_btns, text="LOAD INSTANCE", fg_color=CORES_EDITOR["btn_primary"], hover_color=CORES_EDITOR["btn_hover"], width=120, height=35, font=("Roboto", 12, "bold"), command=self.acao_load_instance)
        btn_load.pack(side="left", padx=(0, 10))
        
        btn_save = ctk.CTkButton(frm_btns, text="SAVE", fg_color=CORES_EDITOR["btn_primary"], hover_color=CORES_EDITOR["btn_hover"], width=80, height=35, font=("Roboto", 12, "bold"), command=self.acao_save_instance)
        btn_save.pack(side="left", padx=(0, 20))

        # --- HEATMAP CONTROLS ---
        
        # 1. Checkbox
        self.var_heatmap = ctk.BooleanVar(value=False)
        self.chk_heatmap = ctk.CTkCheckBox(
            frm_btns, 
            text="Heatmap", 
            variable=self.var_heatmap,
            command=self.aplicar_heatmap_visual,
            font=("Roboto", 12, "bold"),
            text_color="white",
            fg_color="#E74C3C", # Será atualizado dinamicamente
            hover_color="#C0392B"
        )
        self.chk_heatmap.pack(side="left", padx=(0, 10))

        # 2. Cor Padrão Inicial (Vermelho Crítico)
        self.cor_heatmap_atual = "#E74C3C" 

        # 3. Botão "Color Picker" (Quadrado colorido)
        self.btn_cor_picker = ctk.CTkButton(
            frm_btns,
            text="", # Sem texto, só cor
            width=30,
            height=30,
            fg_color=self.cor_heatmap_atual, # Mostra a cor atual
            hover_color=self.cor_heatmap_atual, # (Opcional: escurecer um pouco)
            command=self.escolher_cor_heatmap,
            corner_radius=4,
            border_width=1,
            border_color="white"
        )
        self.btn_cor_picker.pack(side="left")

    def criar_info_block(self):
        frm_info = ctk.CTkFrame(self.frm_main, fg_color="transparent")
        frm_info.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 15))
        ctk.CTkLabel(frm_info, text="INSTANCE:", text_color="white", font=("Roboto", 12, "bold")).pack(side="left", padx=(0, 5))
        self.lbl_val_nome = ctk.CTkLabel(frm_info, text="---", text_color=CORES_EDITOR["text_highlight"], font=("Roboto", 12, "bold"))
        self.lbl_val_nome.pack(side="left", padx=(0, 25))
        ctk.CTkLabel(frm_info, text="MACHINES:", text_color="white", font=("Roboto", 12, "bold")).pack(side="left", padx=(0, 5))
        self.lbl_val_mach = ctk.CTkLabel(frm_info, text="-", text_color=CORES_EDITOR["text_highlight"], font=("Roboto", 12, "bold"))
        self.lbl_val_mach.pack(side="left", padx=(0, 25))
        ctk.CTkLabel(frm_info, text="JOBS:", text_color="white", font=("Roboto", 12, "bold")).pack(side="left", padx=(0, 5))
        self.lbl_val_jobs = ctk.CTkLabel(frm_info, text="-", text_color=CORES_EDITOR["text_highlight"], font=("Roboto", 12, "bold"))
        self.lbl_val_jobs.pack(side="left", padx=(0, 20))
        self.lbl_context = ctk.CTkLabel(frm_info, text="", text_color="gray60", font=("Roboto", 11, "italic"))
        self.lbl_context.pack(side="right", padx=10)

    def criar_tabela_sheet(self):
        self.frm_table_container = ctk.CTkFrame(self.frm_main, fg_color=CORES_EDITOR["grid_bg"], border_width=1, border_color="#333333", corner_radius=4)
        self.frm_table_container.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.frm_table_container.grid_rowconfigure(0, weight=1)
        self.frm_table_container.grid_columnconfigure(0, weight=1)
        if Sheet:
            self.sheet = Sheet(self.frm_table_container, headers=[], data=[], theme="dark", empty_horizontal=0, empty_vertical=0, header_height=30)
            self.sheet.enable_bindings(("single_select", "row_select", "column_select", "drag_select", "row_height_resize", "column_width_resize", "arrowkeys", "right_click_popup_menu", "rc_select", "copy", "cut", "paste", "delete", "undo", "edit_cell"))
            self.sheet.set_options(table_bg=CORES_EDITOR["sheet_bg"], table_fg=CORES_EDITOR["sheet_fg"], table_grid_fg=CORES_EDITOR["sheet_grid"], header_bg=CORES_EDITOR["sheet_header_bg"], header_fg=CORES_EDITOR["sheet_header_fg"], index_bg=CORES_EDITOR["sheet_header_bg"], index_fg=CORES_EDITOR["sheet_header_fg"], frame_bg=CORES_EDITOR["sheet_header_bg"], top_left_bg=CORES_EDITOR["sheet_header_bg"], selection_bg=CORES_EDITOR["sheet_select_bg"], header_selected_bg=CORES_EDITOR["sheet_select"], index_selected_bg=CORES_EDITOR["sheet_select"], font=("Arial", 10, "normal"), header_font=("Arial", 10, "bold"), index_font=("Arial", 10, "bold"), default_column_width=60)
            self.sheet.grid(row=0, column=0, sticky="nsew")

    def criar_area_estatisticas(self):
        self.frm_stats_container = ctk.CTkScrollableFrame(self.frm_main, fg_color="transparent")
        self.frm_stats_container.grid_rowconfigure(0, weight=0) # Controles
        self.frm_stats_container.grid_rowconfigure(1, weight=0) # Gráficos
        self.frm_stats_container.grid_rowconfigure(2, weight=0) # Tabelas
        self.frm_stats_container.grid_columnconfigure(0, weight=1)
        
        # --- BARRA DE CONTROLE ---
        self.frm_controls = ctk.CTkFrame(self.frm_stats_container, fg_color="transparent")
        self.frm_controls.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))
        
        ctk.CTkLabel(self.frm_controls, text="Table Layout:", font=("Roboto", 12, "bold")).pack(side="left", padx=(0, 10))
        
        self.cmb_layout = ctk.CTkComboBox(
            self.frm_controls, 
            values=["Horizontal", "Vertical"],
            variable=self.layout_var,
            command=self.ao_mudar_layout_tabela,
            width=120,
            state="readonly"
        )
        self.cmb_layout.pack(side="left")
        
        self.subfrm_graphs = ctk.CTkFrame(self.frm_stats_container, fg_color="transparent")
        self.subfrm_graphs.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
        
        self.subfrm_table = ctk.CTkFrame(self.frm_stats_container, fg_color=CORES_EDITOR["grid_bg"], corner_radius=6)
        self.subfrm_table.grid(row=2, column=0, sticky="ew", padx=10, pady=(10, 40))

    def ao_mudar_layout_tabela(self, escolha):
        if self.view_atual and self.view_atual[0].startswith("stats"):
            tipo, tag = self.view_atual
            maquina = None if tag == "all" else int(tag)
            self.gerar_tabela_estatistica(maquina_foco=maquina)

    def calcular_percentil(self, dados, percentil=0.95):
        """Calcula o percentil P de uma lista de dados."""
        if not dados: return 0
        dados_sorted = sorted(dados)
        k = (len(dados) - 1) * percentil
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return dados_sorted[int(k)]
        d0 = dados_sorted[int(f)] * (c - k)
        d1 = dados_sorted[int(c)] * (k - f)
        return d0 + d1

    def _get_dados_raw(self, tipo_dado, maquina_idx):
        dados = []
        
        # --- PROCESSING TIMES ---
        if tipo_dado == "proc":
            if maquina_idx is None:
                try: dados = np.array(self.dados_instancia["processing"]).flatten().tolist()
                except: pass
            else:
                try: 
                    m_idx = int(maquina_idx)
                    dados = self.dados_instancia["processing"][m_idx]
                except: pass
        
        # --- SETUP TIMES ---
        else: 
            s_dict = self.dados_instancia.get("setup", {})
            
            # GLOBAL SETUP
            if maquina_idx is None: 
                try:
                    all_setups = []
                    for matriz in s_dict.values():
                        vals = [x for x in np.array(matriz).flatten() if x > 0]
                        all_setups.extend(vals)
                    dados = all_setups
                except: pass
            
            # LOCAL SETUP
            else: 
                matriz = None
                
                # 1. Busca Direta
                try: matriz = s_dict.get(int(maquina_idx))
                except: pass
                
                if matriz is None: matriz = s_dict.get(str(maquina_idx))

                # 2. Processamento
                if matriz is not None:
                    if isinstance(matriz, list):
                        try:
                            flat_vals = np.array(matriz).flatten()
                            filtrados = [x for x in flat_vals if x > 0]
                            
                            if len(filtrados) == 0:
                                # Matriz só tem zeros. Retorna [0] para evitar 'No Data'.
                                dados = [0]
                            else:
                                dados = filtrados
                        except Exception:
                            dados = []
                    else:
                        dados = []
                else:
                    dados = []
                    
        return dados

    def gerar_graficos_estatisticas(self, maquina_idx=None):
        """Gera histogramas e boxplots."""
        
        for w in self.subfrm_graphs.winfo_children(): w.destroy()
        if self.fig_stats: plt.close(self.fig_stats); self.fig_stats = None
        if not self.dados_instancia["loaded"]: return

        proc_flat = self._get_dados_raw("proc", maquina_idx)
        setup_flat = self._get_dados_raw("setup", maquina_idx)
        
        titulo_sufixo = "Global" if maquina_idx is None else f"Machine {maquina_idx}"

        plt.style.use('dark_background')
        
        self.fig_stats, axes = plt.subplots(2, 2, figsize=(10, 6), dpi=100, 
                                            sharex='col', 
                                            gridspec_kw={'height_ratios': [0.60, 0.40], 'hspace': 0.4, 'wspace': 0.2})
        
        self.fig_stats.patch.set_facecolor(CORES_EDITOR["main_bg"]) 
        (ax_hist_p, ax_hist_s), (ax_box_p, ax_box_s) = axes
        cor_proc, cor_setup = ('#9C27B0', '#FF9800') if maquina_idx is not None else ('#5CAEC4', '#E74C3C')
        cor_grid = CORES_EDITOR["grid_bg"]

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

    def _construir_tabela_horizontal(self, parent, titulo, tipo_dado, maquina_foco, cor_titulo):
        ctk.CTkLabel(parent, text=titulo, font=("Roboto", 13, "bold"), text_color=cor_titulo).pack(pady=(0, 5), anchor="w")
        
        grid = ctk.CTkFrame(parent, fg_color="transparent")
        grid.pack(fill="x", expand=True)

        cols = ["Scope"] + [item[0] for item in self.STATS_CONFIG]
        for i, c in enumerate(cols):
            lbl = ctk.CTkLabel(grid, text=c, font=("Roboto", 11, "bold"), text_color="white", fg_color="#333333", corner_radius=4)
            lbl.grid(row=0, column=i, sticky="ew", padx=1, pady=1, ipady=3)
            grid.grid_columnconfigure(i, weight=1)

        row_counter = 1
        
        def add_row(nome, dados_raw, destaque):
            stats = self._calcular_stats(dados_raw)
            if not stats: return
            
            valores_fmt = [nome]
            for _, key, fmt in self.STATS_CONFIG:
                val = stats[key]
                txt = f"{val:{fmt}}" if fmt else str(val)
                if key == 'cv': txt += "%"
                valores_fmt.append(txt)

            bg = "#1F1F1F" if destaque else ("#2b2b2b" if row_counter % 2 == 0 else "transparent")
            fg = cor_titulo if destaque else ("silver" if row_counter % 2 == 0 else "gray70")

            for j, val in enumerate(valores_fmt):
                cor_txt = fg
                # Coluna CV é a última
                if j == 9: 
                    cv_val = stats['cv']
                    if cv_val > 15: cor_txt = "#E74C3C"
                    elif cv_val < 5: cor_txt = "#2ECC71"
                
                ctk.CTkLabel(grid, text=val, font=("Roboto", 11), text_color=cor_txt, fg_color=bg).grid(row=row_counter, column=j, sticky="ew", padx=1, pady=1)

        # 1. Linha Global
        raw_global = self._get_dados_raw(tipo_dado, None)
        add_row("GLOBAL", raw_global, False) 
        row_counter += 1

        # 2. Linhas por Máquina
        for m in range(self.dados_instancia["M"]):
            raw_m = self._get_dados_raw(tipo_dado, m)
            add_row(f"Machine {m}", raw_m, False)
            row_counter += 1

    def _renderizar_modo_global(self):
        # Tabela 1: Processing
        COR_PROC_GLOBAL = "#5CAEC4" 
        frm_proc = ctk.CTkFrame(self.subfrm_table, fg_color="transparent")
        frm_proc.pack(fill="x", expand=True, padx=0, pady=(0, 20))
        self._construir_tabela_horizontal(frm_proc, "PROCESSING TIMES (Global Breakdown)", "proc", None, COR_PROC_GLOBAL)

        ttk.Separator(self.subfrm_table, orient="horizontal").pack(fill="x", padx=20, pady=10)

        # Tabela 2: Setup
        COR_SETUP_GLOBAL = "#E74C3C"
        frm_setup = ctk.CTkFrame(self.subfrm_table, fg_color="transparent")
        frm_setup.pack(fill="x", expand=True, padx=0, pady=(10, 0))
        self._construir_tabela_horizontal(frm_setup, "SETUP TIMES (Global Breakdown)", "setup", None, COR_SETUP_GLOBAL)    

    def _renderizar_modo_maquina(self, maquina_foco):
        # Container para colocar lado a lado
        frm_container = ctk.CTkFrame(self.subfrm_table, fg_color="transparent")
        frm_container.pack(fill="both", expand=True, padx=0, pady=0)
        frm_container.grid_columnconfigure(0, weight=1)
        frm_container.grid_columnconfigure(1, weight=1)

        # Cores Locais
        COR_PROC_LOCAL = "#9C27B0"
        COR_SETUP_LOCAL = "#FF9800"

        # Lado Esquerdo: Processing
        frm_left = ctk.CTkFrame(frm_container, fg_color="transparent")
        frm_left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self._construir_tabela_vertical(frm_left, f"PROCESSING (Machine {maquina_foco})", "proc", maquina_foco, COR_PROC_LOCAL)

        # Lado Direito: Setup
        frm_right = ctk.CTkFrame(frm_container, fg_color="transparent")
        frm_right.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        self._construir_tabela_vertical(frm_right, f"SETUP (Machine {maquina_foco})", "setup", maquina_foco, COR_SETUP_LOCAL)

    def _construir_tabela_vertical(self, parent, titulo, tipo_dado, maquina_idx, cor_titulo):
        ctk.CTkLabel(parent, text=titulo, font=("Roboto", 13, "bold"), text_color=cor_titulo).pack(pady=(0, 5), anchor="w")
        
        grid = ctk.CTkFrame(parent, fg_color="#1A1A1D", border_width=1, border_color="#333333")
        grid.pack(fill="x", expand=True)
        grid.grid_columnconfigure(1, weight=1)

        raw_data = self._get_dados_raw(tipo_dado, maquina_idx)
        stats = self._calcular_stats(raw_data)

        if not stats:
            ctk.CTkLabel(grid, text="No Data Available", text_color="gray").pack(pady=10)
            return

        for i, (label, key, fmt) in enumerate(self.STATS_CONFIG):
            bg = "#252525" if i % 2 == 0 else "transparent"
            lbl_k = ctk.CTkLabel(grid, text=label, font=("Roboto", 11, "bold"), text_color="silver", fg_color=bg, anchor="w")
            lbl_k.grid(row=i, column=0, sticky="ew", padx=(10, 5), pady=1, ipady=2)
            
            val_raw = stats[key]
            val_txt = f"{val_raw:{fmt}}" if fmt else str(val_raw)
            if key == 'cv': val_txt += "%"
            
            cor_val = "white"
            if key == 'cv':
                if val_raw > 15: cor_val = "#E74C3C"
                elif val_raw < 5: cor_val = "#2ECC71"
            
            lbl_v = ctk.CTkLabel(grid, text=val_txt, font=("Roboto", 11), text_color=cor_val, fg_color=bg, anchor="e")
            lbl_v.grid(row=i, column=1, sticky="ew", padx=(5, 10), pady=1)

    def _calcular_stats(self, lista_valores):
        """Calcula o dict de estatísticas com conversão segura de tipos."""
        if not lista_valores: return None
        
        try:
            # Converte para float nativo para evitar erros do Statistics com Numpy
            dados_clean = [float(x) for x in lista_valores]
            n = len(dados_clean)
            
            if n < 2:
                val = dados_clean[0]
                return {
                    'count': n, 'min': val, 'max': val, 'mean': val, 'median': val,
                    'stdev': 0.0, 'var': 0.0, 'cv': 0.0, 'p95': val
                }

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

    def gerar_tabela_estatistica(self, maquina_foco=None):
        for w in self.subfrm_table.winfo_children(): w.destroy()
        if not self.dados_instancia["loaded"]: return

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
            for m in range(self.dados_instancia["M"]):
                lista_entidades.append((f"M{m}", self._get_dados_raw(tipo_dado, m), False))
        else:
            lista_entidades.append(("Current", self._get_dados_raw(tipo_dado, maquina_foco), False))

        if layout == "Horizontal":
            headers = ["Scope"] + [item[0] for item in self.STATS_CONFIG]
            for i, h in enumerate(headers):
                bg = "#333333"
                lbl = ctk.CTkLabel(grid, text=h, font=("Roboto", 11, "bold"), text_color="white", fg_color=bg, corner_radius=4)
                lbl.grid(row=0, column=i, sticky="ew", padx=1, pady=1, ipady=3)
                grid.grid_columnconfigure(i, weight=1)

            for r_idx, (nome_entidade, dados_raw, destaque) in enumerate(lista_entidades):
                row = r_idx + 1
                stats = self._calcular_stats(dados_raw)
                
                bg_row = "#1F1F1F" if destaque else ("#2b2b2b" if row % 2 == 0 else "transparent")
                fg_row = cor_titulo if destaque else ("silver" if row % 2 == 0 else "gray70")
                
                ctk.CTkLabel(grid, text=nome_entidade, font=("Roboto", 11), text_color=fg_row, fg_color=bg_row).grid(row=row, column=0, sticky="ew", padx=1, pady=1)
                
                if stats:
                    for c_idx, (_, key, fmt) in enumerate(self.STATS_CONFIG):
                        val_raw = stats[key]
                        val_txt = f"{val_raw:{fmt}}" if fmt else str(val_raw)
                        if key == 'cv': val_txt += "%"
                        
                        cor_cell = fg_row
                        if key == 'cv':
                            if val_raw > 15: cor_cell = "#E74C3C"
                            elif val_raw < 5: cor_cell = "#2ECC71"
                        
                        ctk.CTkLabel(grid, text=val_txt, font=("Roboto", 11), text_color=cor_cell, fg_color=bg_row).grid(row=row, column=c_idx+1, sticky="ew", padx=1, pady=1)
                else:
                    for c_idx in range(len(self.STATS_CONFIG)):
                        ctk.CTkLabel(grid, text="-", text_color="gray", fg_color=bg_row).grid(row=row, column=c_idx+1, sticky="ew", padx=1, pady=1)

        else:
            ctk.CTkLabel(grid, text="Metric", font=("Roboto", 11, "bold"), text_color="white", fg_color="#333333").grid(row=0, column=0, sticky="ew", padx=1, pady=1, ipady=3)
            grid.grid_columnconfigure(0, weight=0, minsize=80) 
            
            for i, (nome_ent, _, _) in enumerate(lista_entidades):
                ctk.CTkLabel(grid, text=nome_ent, font=("Roboto", 11, "bold"), text_color="white", fg_color="#333333").grid(row=0, column=i+1, sticky="ew", padx=1, pady=1, ipady=3)
                grid.grid_columnconfigure(i+1, weight=1)

            cache_stats = []
            for _, dados_raw, _ in lista_entidades:
                cache_stats.append(self._calcular_stats(dados_raw))

            for r_idx, (label_stat, key, fmt) in enumerate(self.STATS_CONFIG):
                row = r_idx + 1
                bg_row = "#2b2b2b" if row % 2 == 0 else "transparent"
                
                ctk.CTkLabel(grid, text=label_stat, font=("Roboto", 11, "bold"), text_color="silver", fg_color=bg_row, anchor="w").grid(row=row, column=0, sticky="ew", padx=(10,5), pady=1)
                
                for c_idx, stats in enumerate(cache_stats):
                    val_txt = "-"
                    cor_cell = "gray"
                    
                    if stats:
                        val_raw = stats[key]
                        val_txt = f"{val_raw:{fmt}}" if fmt else str(val_raw)
                        if key == 'cv': val_txt += "%"
                        
                        cor_cell = "silver"
                        if key == 'cv':
                            if val_raw > 15: cor_cell = "#E74C3C"
                            elif val_raw < 5: cor_cell = "#2ECC71"
                            
                    ctk.CTkLabel(grid, text=val_txt, font=("Roboto", 11), text_color=cor_cell, fg_color=bg_row).grid(row=row, column=c_idx+1, sticky="ew", padx=1, pady=1)

    def ao_selecionar_sidebar(self, event):
        sel = self.tree_side.selection()
        if not sel: return
        self.salvar_alteracoes_da_view_atual()

        item = self.tree_side.item(sel[0])
        tipo = item['values'][0]; tag = item['values'][1]  

        if not self.dados_instancia["loaded"]: return

        if tipo == "stats" or tipo == "stats_mach":
            self.frm_table_container.grid_forget()
            self.frm_stats_container.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 20))
            
            if tipo == "stats":
                self.view_atual = ("stats", "all")
                self.lbl_context.configure(text="Viewing: Global Statistics")
                self.gerar_graficos_estatisticas(maquina_idx=None)
                self.gerar_tabela_estatistica(maquina_foco=None)
            else:
                try:
                    m_idx = int(tag)
                    self.view_atual = ("stats_mach", tag)
                    self.lbl_context.configure(text=f"Viewing: Machine {m_idx} Statistics")
                    self.gerar_graficos_estatisticas(maquina_idx=m_idx)
                    self.gerar_tabela_estatistica(maquina_foco=m_idx)
                except ValueError: pass
            
        else:
            self.frm_stats_container.grid_forget()
            self.frm_table_container.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 20))

            if tipo == "proc": self.exibir_processing_times()
            elif tipo == "setup" and tag != "none": self.exibir_setup_times(int(tag))

    def exibir_processing_times(self, manter_scroll=False):
        if not Sheet or not self.dados_instancia["loaded"]: return
        
        # Salva scroll atual se pedido
        y_scroll = self.sheet.yview()[0] if manter_scroll and hasattr(self.sheet, 'yview') else 0
        x_scroll = self.sheet.xview()[0] if manter_scroll and hasattr(self.sheet, 'xview') else 0

        self.view_atual = ("proc", "all")
        dados = self.dados_instancia["processing"]
        n_jobs = self.dados_instancia["N"]; n_maquinas = self.dados_instancia["M"]
        col_headers = [f"J{i}" for i in range(n_jobs)]
        row_indices = [f"M{i}" for i in range(n_maquinas)]
        
        self.lbl_context.configure(text="Editing: Processing Times")
        self.sheet.headers(col_headers)
        self.sheet.row_index(row_indices)
        self.sheet.set_sheet_data(dados) # Isso reseta as cores automaticamente
        
        # Reaplica Heatmap se estiver ativado
        if self.var_heatmap.get():
            self.aplicar_heatmap_visual()

        # Restaura scroll
        if manter_scroll:
            try:
                self.sheet.yview_moveto(y_scroll)
                self.sheet.xview_moveto(x_scroll)
            except: pass

    def exibir_setup_times(self, maquina_idx, manter_scroll=False):
        if not Sheet or not self.dados_instancia["loaded"]: return
        
        # Salva scroll atual
        y_scroll = self.sheet.yview()[0] if manter_scroll and hasattr(self.sheet, 'yview') else 0
        x_scroll = self.sheet.xview()[0] if manter_scroll and hasattr(self.sheet, 'xview') else 0

        self.view_atual = ("setup", str(maquina_idx))
        dados = self.dados_instancia["setup"].get(maquina_idx, [])
        if not dados:
            n_jobs = self.dados_instancia["N"]; dados = [[0]*n_jobs for _ in range(n_jobs)]
            self.dados_instancia["setup"][maquina_idx] = dados
            
        n_jobs = self.dados_instancia["N"]
        headers = [f"J{i}" for i in range(n_jobs)]; row_indices = [f"J{i}" for i in range(n_jobs)]
        
        self.lbl_context.configure(text=f"Editing: Setup Times (Machine {maquina_idx})")
        self.sheet.headers(headers)
        self.sheet.row_index(row_indices)
        self.sheet.set_sheet_data(dados) # Reseta cores
        
        # Reaplica Heatmap se estiver ativado
        if self.var_heatmap.get():
            self.aplicar_heatmap_visual()

        # Restaura scroll
        if manter_scroll:
            try:
                self.sheet.yview_moveto(y_scroll)
                self.sheet.xview_moveto(x_scroll)
            except: pass

    def acao_save_instance(self):
        if not self.dados_instancia["loaded"]: return
        self.salvar_alteracoes_da_view_atual()
        nome_sugerido = f"MODIFIED_{self.dados_instancia.get('nome', 'instance.txt')}"
        caminho = filedialog.asksaveasfilename(parent=self, initialfile=nome_sugerido, defaultextension=".txt", filetypes=[("Text Files", "*.txt")])
        if not caminho: return
        try:
            N = self.dados_instancia["N"]; M = self.dados_instancia["M"]
            p_matrix = self.dados_instancia["processing"]; s_dict = self.dados_instancia["setup"]
            with open(caminho, "w") as f:
                f.write(f"{N}\t{M}\t1\n"); f.write(f"{M}\n") 
                for j in range(N): 
                    linha_txt = []
                    for m in range(M): 
                        tempo = p_matrix[m][j]; linha_txt.append(f"{m}\t{tempo}")
                    f.write("\t".join(linha_txt) + "\n")
                f.write("SSD\n")
                for m in range(M):
                    f.write(f"M{m}\n"); matriz = s_dict.get(m, [])
                    if not matriz: matriz = [[0]*N for _ in range(N)]
                    for row in matriz:
                        linha_valores = [str(v) for v in row]
                        f.write("\t".join(linha_valores) + "\n")
            messagebox.showinfo("Saved", "Instance saved successfully!", parent=self)
        except Exception as e: messagebox.showerror("Error", f"Failed to save file:\n{e}")

    def acao_load_instance(self):
        caminho = filedialog.askopenfilename(parent=self, filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
        if not caminho: return
        try:
            with open(caminho, 'r') as f: 
                # Remove espaços em branco das extremidades e linhas vazias
                linhas = [l.strip() for l in f.readlines() if l.strip()]
            
            if not linhas: return
            
            # --- HEADER & PROCESSING TIMES ---
            cabecalho = list(map(int, linhas[0].split()))
            n_jobs = cabecalho[0]
            n_maquinas = cabecalho[1]
            
            segunda_linha = list(map(int, linhas[1].split()))
            inicio_proc = 2 if len(segunda_linha) == 1 else 1
            
            matriz_proc = [[0]*n_jobs for _ in range(n_maquinas)]
            
            for j in range(n_jobs):
                if (inicio_proc + j) >= len(linhas): break
                linha_raw = list(map(int, linhas[inicio_proc + j].split()))
                
                # Parsing: maquina tempo maquina tempo ...
                for k in range(0, len(linha_raw), 2):
                    if k+1 >= len(linha_raw): break
                    maq_idx = linha_raw[k]
                    tempo = linha_raw[k+1]
                    if maq_idx < n_maquinas: 
                        matriz_proc[maq_idx][j] = tempo
            
            # --- SETUP TIMES (PARSER ROBUSTO) ---
            setups = {} 
            
            # 1. Encontrar a linha "SSD"
            idx_ssd = -1
            for i in range(len(linhas)):
                if "SSD" in linhas[i].upper(): # Procura SSD em qualquer lugar (case insensitive)
                    idx_ssd = i
                    break
            
            if idx_ssd != -1:
                idx_atual = idx_ssd + 1
                
                while idx_atual < len(linhas):
                    conteudo = linhas[idx_atual].upper().replace(" ", "") # Remove espaços e normaliza
                    
                    # Verifica se a linha parece um cabeçalho de máquina (Ex: "M0", "M1", "MACHINE0")
                    if conteudo.startswith("M"):
                        try:
                            # Tenta extrair o número removendo 'M' ou 'MACHINE'
                            raw_num = conteudo.replace("MACHINE", "").replace("M", "")
                            maquina_id = int(raw_num)
                            
                            # Lê as próximas N linhas como a matriz dessa máquina
                            idx_atual += 1 # Pula a linha do "M..."
                            matriz_m = []
                            
                            for _ in range(n_jobs):
                                if idx_atual >= len(linhas): break
                                vals = list(map(int, linhas[idx_atual].split()))
                                matriz_m.append(vals)
                                idx_atual += 1
                                
                            setups[maquina_id] = matriz_m
                            # Não incrementa idx_atual aqui pois o loop for já o fez
                            continue 
                            
                        except ValueError:
                            idx_atual += 1
                    else:
                        # Se não é linha de máquina, avança
                        idx_atual += 1
            else:
                print("DEBUG: Nenhum bloco 'SSD' encontrado no arquivo.")

            self.dados_instancia = {
                "loaded": True, 
                "nome": os.path.basename(caminho), 
                "N": n_jobs, 
                "M": n_maquinas, 
                "processing": matriz_proc, 
                "setup": setups
            }
            self.atualizar_interface_pos_load()
            
        except Exception as e: 
            messagebox.showerror("Error", f"Failed to parse instance:\n{e}")

    def atualizar_interface_pos_load(self):
        dados = self.dados_instancia
        self.lbl_val_nome.configure(text=dados['nome'])
        self.lbl_val_mach.configure(text=str(dados['M'])); self.lbl_val_jobs.configure(text=str(dados['N']))
        filhos_setup = self.tree_side.get_children(self.node_setup); 
        for f in filhos_setup: self.tree_side.delete(f)
        filhos_stats = self.tree_side.get_children(self.node_stats)
        for f in filhos_stats: self.tree_side.delete(f)
        for m in range(dados['M']):
            self.tree_side.insert(self.node_setup, "end", text=f"    📁 M{m}", values=("setup", f"{m}"))
            self.tree_side.insert(self.node_stats, "end", text=f"    📊 M{m} Stats", values=("stats_mach", f"{m}"))
        self.exibir_processing_times()
        self.tree_side.item(self.node_stats, open=True); self.tree_side.item(self.node_setup, open=False); self.tree_side.selection_set(self.node_proc)

def abrir_editor_janela(root_parent=None):
    if root_parent: app = InstanceEditor(root_parent)
    else: app = InstanceEditor(None); app.mainloop()

if __name__ == "__main__": ctk.set_appearance_mode("Dark"); abrir_editor_janela()