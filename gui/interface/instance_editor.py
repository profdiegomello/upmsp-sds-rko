import customtkinter as ctk
from tkinter import ttk, filedialog, messagebox
import tkinter as tk
import os
import sys

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np

# Tenta importar o tksheet
try:
    from tksheet import Sheet
except ImportError:
    print("ERRO CRÍTICO: Biblioteca 'tksheet' não instalada.")
    Sheet = None 

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
        self.geometry("1100x700")
        
        # Variaveis de Estado
        self.dados_instancia = {
            "loaded": False,
            "N": 0, # Jobs
            "M": 0, # Maquinas
            "processing": [], # Matriz MxN
            "setup": {}       
        }
        
        self.view_atual = None
        self.canvas_stats = None # Referencia para o canvas do matplotlib
        self.fig_stats = None

        if os.name == 'nt':
            try: self.after(200, lambda: self.iconbitmap())
            except: pass
        self.focus_force()

        # Layout
        self.grid_columnconfigure(0, weight=0, minsize=260) 
        self.grid_columnconfigure(1, weight=1)              
        self.grid_rowconfigure(0, weight=1)

        self.criar_sidebar()

        self.frm_main = ctk.CTkFrame(self, fg_color=CORES_EDITOR["main_bg"], corner_radius=0)
        self.frm_main.grid(row=0, column=1, sticky="nsew")
        self.frm_main.grid_rowconfigure(2, weight=1) 
        self.frm_main.grid_columnconfigure(0, weight=1)

        self.criar_header_botoes()
        self.criar_info_block()
        
        # Container da Tabela (Sheet)
        self.criar_tabela_sheet()
        
        # Container dos Gráficos (Statistics) - Inicialmente oculto
        self.criar_area_estatisticas()
        
    def ao_fechar(self):
        self.destroy()
   
    def salvar_alteracoes_da_view_atual(self):
        """Salva o que está na tela (Sheet) para a memória antes de trocar de aba"""
        if not self.dados_instancia["loaded"] or not self.view_atual:
            return

        tipo, tag = self.view_atual
        
        # Se estivermos vendo estatísticas, não há o que salvar da visualização
        if tipo == "stats":
            return

        dados_visuais = self.sheet.get_sheet_data()
        
        try:
            dados_int = [[int(c) for c in linha] for linha in dados_visuais]
        except ValueError:
            messagebox.showerror("Format Error", "All cells must contain integer numbers.")
            return

        if tipo == "proc":
            self.dados_instancia["processing"] = dados_int
            
        elif tipo == "setup":
            maquina_id = int(tag)
            self.dados_instancia["setup"][maquina_id] = dados_int

    def criar_sidebar(self):
        self.frm_side = ctk.CTkFrame(self, fg_color=CORES_EDITOR["sidebar_bg"], corner_radius=0, width=260)
        self.frm_side.grid(row=0, column=0, sticky="nsew")
        self.frm_side.grid_rowconfigure(0, weight=1)
        self.frm_side.grid_columnconfigure(0, weight=1)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Sidebar.Treeview", 
                        background=CORES_EDITOR["sidebar_bg"],
                        foreground="white",
                        fieldbackground=CORES_EDITOR["sidebar_bg"],
                        borderwidth=0, font=("Roboto", 11))
        style.map('Sidebar.Treeview', background=[('selected', '#444444')], foreground=[('selected', 'white')])

        self.tree_side = ttk.Treeview(self.frm_side, show="tree", style="Sidebar.Treeview", selectmode="browse")
        self.tree_side.grid(row=0, column=0, sticky="nsew", padx=10, pady=20)
        
        scroll_y = ctk.CTkScrollbar(self.frm_side, command=self.tree_side.yview, width=8, fg_color="transparent")
        self.tree_side.configure(yscrollcommand=scroll_y.set)
        scroll_y.grid(row=0, column=1, sticky="ns")

        # Nós da árvore
        self.node_proc = self.tree_side.insert("", "end", text=" 📂 Processing Times", open=True, values=("proc", "all"))
        self.node_setup = self.tree_side.insert("", "end", text=" 📂 Setup Times", open=True, values=("setup_root", "none"))
        
        # --- NOVO NÓ DE ESTATÍSTICAS ---
        self.node_stats = self.tree_side.insert("", "end", text=" 📊 Statistics", values=("stats", "all"))
        
        self.tree_side.bind("<<TreeviewSelect>>", self.ao_selecionar_sidebar)

    def criar_header_botoes(self):
        frm_btns = ctk.CTkFrame(self.frm_main, fg_color="transparent", height=50)
        frm_btns.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        
        btn_load = ctk.CTkButton(frm_btns, text="LOAD INSTANCE", fg_color=CORES_EDITOR["btn_primary"], hover_color=CORES_EDITOR["btn_hover"], width=120, height=35, font=("Roboto", 12, "bold"), command=self.acao_load_instance)
        btn_load.pack(side="left", padx=(0, 10))
        
        btn_save = ctk.CTkButton(frm_btns, text="SAVE", fg_color=CORES_EDITOR["btn_primary"], hover_color=CORES_EDITOR["btn_hover"], width=80, height=35, font=("Roboto", 12, "bold"), command=self.acao_save_instance)
        btn_save.pack(side="left")

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
        # Frame container para a Tabela (Sheet)
        self.frm_table_container = ctk.CTkFrame(self.frm_main, fg_color=CORES_EDITOR["grid_bg"], border_width=1, border_color="#333333", corner_radius=4)
        # Grid inicialmente posicionado
        self.frm_table_container.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.frm_table_container.grid_rowconfigure(0, weight=1)
        self.frm_table_container.grid_columnconfigure(0, weight=1)

        if Sheet:
            self.sheet = Sheet(self.frm_table_container,
                               headers=[], 
                               data=[], 
                               theme="dark", 
                               empty_horizontal=0, 
                               empty_vertical=0,
                               header_height=30)
            
            self.sheet.enable_bindings(("single_select", "row_select", "column_select", "drag_select",
                                        "row_height_resize", "column_width_resize", "arrowkeys",
                                        "right_click_popup_menu", "rc_select", "copy", "cut", "paste", "delete", "undo", "edit_cell"))
            
            self.sheet.set_options(
                table_bg = CORES_EDITOR["sheet_bg"],
                table_fg = CORES_EDITOR["sheet_fg"],
                table_grid_fg = CORES_EDITOR["sheet_grid"],
                header_bg = CORES_EDITOR["sheet_header_bg"],
                header_fg = CORES_EDITOR["sheet_header_fg"],
                index_bg = CORES_EDITOR["sheet_header_bg"], 
                index_fg = CORES_EDITOR["sheet_header_fg"],
                frame_bg = CORES_EDITOR["sheet_header_bg"],
                top_left_bg = CORES_EDITOR["sheet_header_bg"],
                selection_bg = CORES_EDITOR["sheet_select_bg"],
                header_selected_bg = CORES_EDITOR["sheet_select"],
                index_selected_bg = CORES_EDITOR["sheet_select"],
                font = ("Arial", 10, "normal"),
                header_font = ("Arial", 10, "bold"),
                index_font = ("Arial", 10, "bold"),
                default_column_width = 60 
            )
            self.sheet.grid(row=0, column=0, sticky="nsew")

    def criar_area_estatisticas(self):
        """Cria o frame onde os gráficos serão exibidos, mas o mantém oculto inicialmente"""
        self.frm_stats_container = ctk.CTkFrame(self.frm_main, fg_color="transparent")
        # Nota: Não fazemos .grid() aqui ainda, faremos na troca de visualização
        self.frm_stats_container.grid_rowconfigure(0, weight=1)
        self.frm_stats_container.grid_columnconfigure(0, weight=1)

    # logica de graficos
    def gerar_graficos_estatisticas(self, maquina_idx=None):
        """
        Gera histogramas e boxplots separados.
        CORREÇÃO: Agora fecha a figura anterior para liberar memória.
        """
        # Limpeza de Widgets (Visual)
        for widget in self.frm_stats_container.winfo_children():
            widget.destroy()

        # Limpeza do Matplotlib (Memoria) 
        if self.fig_stats:
            plt.close(self.fig_stats)
            self.fig_stats = None

        if not self.dados_instancia["loaded"]:
            ctk.CTkLabel(self.frm_stats_container, text="No instance loaded.", font=("Roboto", 16)).pack(expand=True)
            return

        # PREPARACAO DOS DADOS 
        proc_flat = []
        setup_flat = []
        titulo_sufixo = "Global"

        if maquina_idx is None:
            titulo_sufixo = "Global"
            raw_proc = self.dados_instancia["processing"]
            if raw_proc:
                try: proc_flat = np.array(raw_proc).flatten()
                except: pass
            raw_setup = self.dados_instancia["setup"]
            if raw_setup:
                try:
                    all_setups = []
                    for matriz in raw_setup.values():
                        all_setups.extend(np.array(matriz).flatten())
                    setup_flat = [x for x in all_setups if x > 0]
                except: pass
        else:
            titulo_sufixo = f"Machine {maquina_idx}"
            try:
                if maquina_idx < len(self.dados_instancia["processing"]):
                    linha_proc = self.dados_instancia["processing"][maquina_idx]
                    proc_flat = np.array(linha_proc)
            except: pass
            try:
                matriz_setup = self.dados_instancia["setup"].get(maquina_idx, [])
                if matriz_setup:
                    flat_setup_local = np.array(matriz_setup).flatten()
                    setup_flat = [x for x in flat_setup_local if x > 0]
            except: pass

        # CONFIGURACAO MATPLOTLIB 
        plt.style.use('dark_background')
        
        self.fig_stats, axes = plt.subplots(2, 2, figsize=(10, 6), dpi=100, 
                                 sharex='col', 
                                 gridspec_kw={'height_ratios': [0.60, 0.40], 'hspace': 0.4, 'wspace': 0.2})
        
        self.fig_stats.patch.set_facecolor(CORES_EDITOR["main_bg"]) 

        (ax_hist_p, ax_hist_s), (ax_box_p, ax_box_s) = axes

        cor_proc = '#9C27B0' if maquina_idx is not None else '#5CAEC4'
        cor_setup = '#FF9800' if maquina_idx is not None else '#E74C3C'
        cor_grid_bg = CORES_EDITOR["grid_bg"]

        # COLUNA 1: PROCESSING TIMES 
        ax_hist_p.set_facecolor(cor_grid_bg)
        if len(proc_flat) > 0:
            ax_hist_p.hist(proc_flat, bins=15, color=cor_proc, edgecolor='black', alpha=0.8)
            media_p = np.mean(proc_flat)
            ax_hist_p.axvline(media_p, color='white', linestyle='dashed', linewidth=1, label=f'Avg: {media_p:.1f}')
            ax_hist_p.legend(fontsize=7, facecolor=cor_grid_bg, edgecolor="white", loc='upper right')

        ax_hist_p.set_title(f"Processing Times ({titulo_sufixo})", fontsize=10, color="white", fontweight="bold")
        ax_hist_p.set_ylabel("Freq.", fontsize=8, color="gray")
        ax_hist_p.grid(axis='y', alpha=0.2, linestyle='--')
        ax_hist_p.tick_params(axis='x', labelbottom=True) 

        ax_box_p.set_facecolor(cor_grid_bg)
        if len(proc_flat) > 0:
            props = dict(color='white')
            flier_props = dict(marker='o', markerfacecolor='white', markersize=3, linestyle='none', markeredgecolor='none')
            
            ax_box_p.boxplot(proc_flat, vert=False, patch_artist=True, 
                             boxprops=dict(facecolor=cor_proc, alpha=0.6),
                             medianprops=props, capprops=props, whiskerprops=props, flierprops=flier_props,
                             widths=0.5)
            
        ax_box_p.set_xlabel("Time Unit", fontsize=9, color="gray")
        ax_box_p.set_yticks([]) 
        ax_box_p.grid(axis='x', alpha=0.2, linestyle='--')
        ax_box_p.set_title("Distribution Boxplot", fontsize=9, color="gray", pad=5)

        # COLUNA 2: SETUP TIMES 
        ax_hist_s.set_facecolor(cor_grid_bg)
        if len(setup_flat) > 0:
            ax_hist_s.hist(setup_flat, bins=20, color=cor_setup, edgecolor='black', alpha=0.8)
            media_s = np.mean(setup_flat)
            ax_hist_s.axvline(media_s, color='white', linestyle='dashed', linewidth=1, label=f'Avg: {media_s:.1f}')
            ax_hist_s.legend(fontsize=7, facecolor=cor_grid_bg, edgecolor="white", loc='upper right')
        else:
            ax_hist_s.text(0.5, 0.5, "No Data", ha='center', va='center', color='gray')

        ax_hist_s.set_title(f"Setup Times ({titulo_sufixo})", fontsize=10, color="white", fontweight="bold")
        ax_hist_s.grid(axis='y', alpha=0.2, linestyle='--')
        ax_hist_s.tick_params(axis='x', labelbottom=True)

        ax_box_s.set_facecolor(cor_grid_bg)
        if len(setup_flat) > 0:
            props = dict(color='white')
            flier_props = dict(marker='o', markerfacecolor='white', markersize=3, linestyle='none', markeredgecolor='none')
            ax_box_s.boxplot(setup_flat, vert=False, patch_artist=True,
                             boxprops=dict(facecolor=cor_setup, alpha=0.6),
                             medianprops=props, capprops=props, whiskerprops=props, flierprops=flier_props,
                             widths=0.5)
            
        ax_box_s.set_xlabel("Time Unit", fontsize=9, color="gray")
        ax_box_s.set_yticks([])
        ax_box_s.grid(axis='x', alpha=0.2, linestyle='--')
        ax_box_s.set_title("Distribution Boxplot", fontsize=9, color="gray", pad=5)

        self.fig_stats.subplots_adjust(left=0.08, right=0.95, top=0.92, bottom=0.15, wspace=0.2, hspace=0.4)
        
        # Renderiza
        self.canvas_stats = FigureCanvasTkAgg(self.fig_stats, master=self.frm_stats_container)
        self.canvas_stats.draw()
        self.canvas_stats.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

    def ao_selecionar_sidebar(self, event):
        sel = self.tree_side.selection()
        if not sel: return
        
        # Salva o que estava sendo editado antes de mudar
        self.salvar_alteracoes_da_view_atual()

        item = self.tree_side.item(sel[0])
        tipo = item['values'][0] 
        tag = item['values'][1]  

        if not self.dados_instancia["loaded"]: return

        # LOGICA DE TROCA DE VISUALIZACAO
        
        if tipo == "stats" or tipo == "stats_mach":
            # Esconde Tabela, Mostra Gráficos
            self.frm_table_container.grid_forget()
            self.frm_stats_container.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 20))
            
            # Define se é Global ou Local
            if tipo == "stats":
                self.view_atual = ("stats", "all")
                self.lbl_context.configure(text="Viewing: Global Statistics")
                self.gerar_graficos_estatisticas(maquina_idx=None) # None = Global
            else:
                m_idx = int(tag)
                self.view_atual = ("stats_mach", tag)
                self.lbl_context.configure(text=f"Viewing: Machine {m_idx} Statistics")
                self.gerar_graficos_estatisticas(maquina_idx=m_idx) # Passa o ID da máquina
            
        else:
            # Esconde Graficos, Mostra Tabela
            self.frm_stats_container.grid_forget()
            self.frm_table_container.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 20))

            if tipo == "proc":
                self.exibir_processing_times()
            elif tipo == "setup" and tag != "none":
                self.exibir_setup_times(int(tag))

    def exibir_processing_times(self):
        if not Sheet or not self.dados_instancia["loaded"]: return
        self.view_atual = ("proc", "all")
        
        dados = self.dados_instancia["processing"]
        n_jobs = self.dados_instancia["N"]
        n_maquinas = self.dados_instancia["M"]
        
        col_headers = [f"J{i}" for i in range(n_jobs)]
        row_indices = [f"M{i}" for i in range(n_maquinas)]

        self.lbl_context.configure(text="Editing: Processing Times")
        
        self.sheet.headers(col_headers)
        self.sheet.row_index(row_indices)
        self.sheet.set_sheet_data(dados)

    def exibir_setup_times(self, maquina_idx):
        if not Sheet or not self.dados_instancia["loaded"]: return
        self.view_atual = ("setup", str(maquina_idx))
        
        dados = self.dados_instancia["setup"].get(maquina_idx, [])
        if not dados:
            n_jobs = self.dados_instancia["N"]
            dados = [[0]*n_jobs for _ in range(n_jobs)]
            self.dados_instancia["setup"][maquina_idx] = dados

        n_jobs = self.dados_instancia["N"]
        headers = [f"J{i}" for i in range(n_jobs)]
        row_indices = [f"J{i}" for i in range(n_jobs)]

        self.lbl_context.configure(text=f"Editing: Setup Times (Machine {maquina_idx})")
        
        self.sheet.headers(headers)
        self.sheet.row_index(row_indices) 
        self.sheet.set_sheet_data(dados)

    def acao_save_instance(self):
        if not self.dados_instancia["loaded"]:
            return

        self.salvar_alteracoes_da_view_atual()

        nome_sugerido = f"MODIFIED_{self.dados_instancia.get('nome', 'instance.txt')}"

        caminho = filedialog.asksaveasfilename(
            parent=self,
            initialfile=nome_sugerido, 
            defaultextension=".txt", 
            filetypes=[("Text Files", "*.txt")]
        )
        if not caminho: return

        try:
            N = self.dados_instancia["N"]
            M = self.dados_instancia["M"]
            p_matrix = self.dados_instancia["processing"] 
            s_dict = self.dados_instancia["setup"]

            with open(caminho, "w") as f:
                f.write(f"{N}\t{M}\t1\n")
                f.write(f"{M}\n") 

                for j in range(N): 
                    linha_txt = []
                    for m in range(M): 
                        tempo = p_matrix[m][j]
                        linha_txt.append(f"{m}\t{tempo}")
                    f.write("\t".join(linha_txt) + "\n")

                f.write("SSD\n")
                for m in range(M):
                    f.write(f"M{m}\n")
                    matriz = s_dict.get(m, [])
                    if not matriz: matriz = [[0]*N for _ in range(N)]
                    
                    for idx_linha, row in enumerate(matriz):
                        linha_valores = [str(idx_linha)] + [str(v) for v in row]
                        linha_str = "\t".join(linha_valores)
                        f.write(linha_str + "\n")
            
            messagebox.showinfo("Saved", "Instance saved successfully!", parent=self)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save file:\n{e}")

    def acao_load_instance(self):
        caminho = filedialog.askopenfilename(
            parent=self, 
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if not caminho: return

        try:
            with open(caminho, 'r') as f:
                linhas = [l.strip() for l in f.readlines() if l.strip()]

            if not linhas: return

            cabecalho = list(map(int, linhas[0].split()))
            n_jobs = cabecalho[0]
            n_maquinas = cabecalho[1]

            segunda_linha = list(map(int, linhas[1].split()))
            if len(segunda_linha) == 1: inicio_proc = 2
            else: inicio_proc = 1

            matriz_proc = [[0]*n_jobs for _ in range(n_maquinas)]
            
            for j in range(n_jobs):
                if (inicio_proc + j) >= len(linhas): break
                linha_raw = list(map(int, linhas[inicio_proc + j].split()))
                for k in range(0, len(linha_raw), 2):
                    if k+1 >= len(linha_raw): break
                    maq_idx = linha_raw[k] 
                    tempo = linha_raw[k+1]
                    if maq_idx < n_maquinas:
                        matriz_proc[maq_idx][j] = tempo

            setups = {} 
            idx_busca_ssd = inicio_proc + n_jobs
            idx_ssd = -1
            for i in range(idx_busca_ssd, len(linhas)):
                if linhas[i] == "SSD":
                    idx_ssd = i
                    break
            
            if idx_ssd != -1:
                idx_atual = idx_ssd + 1
                maquina_atual = -1
                
                while idx_atual < len(linhas):
                    conteudo = linhas[idx_atual]
                    if conteudo.startswith("M"):
                        try: maquina_atual = int(conteudo[1:])
                        except: maquina_atual = -1
                        idx_atual += 1
                        if 0 <= maquina_atual < n_maquinas:
                            matriz_m = []
                            for _ in range(n_jobs):
                                if idx_atual >= len(linhas): break
                                vals = list(map(int, linhas[idx_atual].split()))
                                matriz_m.append(vals)
                                idx_atual += 1
                            setups[maquina_atual] = matriz_m
                        else: pass
                    else: idx_atual += 1

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
            print(f"Erro ao ler instância: {e}")
            messagebox.showerror("Error", f"Failed to parse instance:\n{e}")

    def atualizar_interface_pos_load(self):
        dados = self.dados_instancia
        
        # Atualiza os labels do topo
        self.lbl_val_nome.configure(text=dados['nome'])
        self.lbl_val_mach.configure(text=str(dados['M']))
        self.lbl_val_jobs.configure(text=str(dados['N']))

        # --- ATUALIZA A ÁRVORE DE SETUP ---
        filhos_setup = self.tree_side.get_children(self.node_setup)
        for f in filhos_setup: self.tree_side.delete(f)

        # --- ATUALIZA A ÁRVORE DE ESTATÍSTICAS (NOVO) ---
        filhos_stats = self.tree_side.get_children(self.node_stats)
        for f in filhos_stats: self.tree_side.delete(f)

        # Cria os nós filhos para cada máquina
        for m in range(dados['M']):
            # Nó de Setup (Tabela)
            self.tree_side.insert(self.node_setup, "end", text=f"    📁 M{m}", values=("setup", f"{m}"))
            
            # Nó de Estatística (Gráfico Local)
            self.tree_side.insert(self.node_stats, "end", text=f"    📊 M{m} Stats", values=("stats_mach", f"{m}"))

        self.exibir_processing_times()
        
        # Abre os nós pais para facilitar a visualização
        self.tree_side.item(self.node_stats, open=True)
        self.tree_side.item(self.node_setup, open=False) 
        self.tree_side.selection_set(self.node_proc)

def abrir_editor_janela(root_parent=None):
    if root_parent:
        app = InstanceEditor(root_parent)
    else:
        app = InstanceEditor(None)
        app.mainloop()

if __name__ == "__main__":
    ctk.set_appearance_mode("Dark")
    abrir_editor_janela()