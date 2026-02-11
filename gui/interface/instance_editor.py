import customtkinter as ctk
from tkinter import ttk, filedialog
import tkinter as tk
import os
import sys

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

        self.parent_app = parent # Guarda a referencia do Launcher
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
        self.criar_tabela_sheet()
        
    def ao_fechar(self):
        """Fecha apenas o editor, mantendo o Launcher vivo"""
        self.destroy()
   
    def salvar_alteracoes_da_view_atual(self):
        """Pega os dados visuais do tksheet e salva na estrutura de dados em memória"""
        if not self.dados_instancia["loaded"] or not self.view_atual:
            return

        tipo, tag = self.view_atual
        
        # Pega todos os dados da planilha como lista de listas
        dados_visuais = self.sheet.get_sheet_data()
        
        # Converte tudo para int (o tksheet pode retornar strings)
        try:
            dados_int = [[int(c) for c in linha] for linha in dados_visuais]
        except ValueError:
            tk.messagebox.showerror("Format Error", "All cells must contain integer numbers.")
            return

        if tipo == "proc":
            self.dados_instancia["processing"] = dados_int
            #print("Processing times updated in memory.")
            
        elif tipo == "setup":
            maquina_id = int(tag)
            self.dados_instancia["setup"][maquina_id] = dados_int
            #print(f"Setup times for Machine {maquina_id} updated in memory.")

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

        self.node_proc = self.tree_side.insert("", "end", text=" 📂 Processing Times", open=True, values=("proc", "all"))
        self.node_setup = self.tree_side.insert("", "end", text=" 📂 Setup Times", open=True, values=("setup_root", "none"))
        
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
        
        # --- BLOCO DE INFORMAÇÕES FIXAS (Esquerda) ---
        # Usamos .pack(side="left") para empilhar: LabelBranco -> ValorAzul -> Espaço -> LabelBranco...
        
        # 1. Instance Name
        ctk.CTkLabel(frm_info, text="INSTANCE:", text_color="white", font=("Roboto", 12, "bold")).pack(side="left", padx=(0, 5))
        self.lbl_val_nome = ctk.CTkLabel(frm_info, text="---", text_color=CORES_EDITOR["text_highlight"], font=("Roboto", 12, "bold"))
        self.lbl_val_nome.pack(side="left", padx=(0, 25))

        # 2. Machines
        ctk.CTkLabel(frm_info, text="MACHINES:", text_color="white", font=("Roboto", 12, "bold")).pack(side="left", padx=(0, 5))
        self.lbl_val_mach = ctk.CTkLabel(frm_info, text="-", text_color=CORES_EDITOR["text_highlight"], font=("Roboto", 12, "bold"))
        self.lbl_val_mach.pack(side="left", padx=(0, 25))

        # 3. Jobs
        ctk.CTkLabel(frm_info, text="JOBS:", text_color="white", font=("Roboto", 12, "bold")).pack(side="left", padx=(0, 5))
        self.lbl_val_jobs = ctk.CTkLabel(frm_info, text="-", text_color=CORES_EDITOR["text_highlight"], font=("Roboto", 12, "bold"))
        self.lbl_val_jobs.pack(side="left", padx=(0, 20))

        # --- BLOCO DE CONTEXTO (Direita) ---
        # Mostra o que está sendo editado no momento (Ex: "Processing Times") de forma discreta
        self.lbl_context = ctk.CTkLabel(frm_info, text="", text_color="gray60", font=("Roboto", 11, "italic"))
        self.lbl_context.pack(side="right", padx=10)

    def criar_tabela_sheet(self):
        self.frm_table_container = ctk.CTkFrame(self.frm_main, fg_color=CORES_EDITOR["grid_bg"], border_width=1, border_color="#333333", corner_radius=4)
        self.frm_table_container.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.frm_table_container.grid_rowconfigure(0, weight=1)
        self.frm_table_container.grid_columnconfigure(0, weight=1)

        if Sheet:
            # Sheet comeca vazia
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

    def acao_save_instance(self):
        if not self.dados_instancia["loaded"]:
            return

        # Garante que a edicao atual foi salva na memoria
        self.salvar_alteracoes_da_view_atual()

        # Pede onde salvar
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
            p_matrix = self.dados_instancia["processing"] # Linha=Maq, Col=Job
            s_dict = self.dados_instancia["setup"]

            with open(caminho, "w") as f:

                f.write(f"{N}\t{M}\t1\n")
                f.write(f"{M}\n") 

                # --- PROCESSING TIMES ---
                # Formato original: MaqID \t Tempo \t MaqID \t Tempo ...
                for j in range(N): # Para cada Job (linha do arquivo)
                    linha_txt = []
                    for m in range(M): # Para cada Máquina
                        tempo = p_matrix[m][j]
                        # Adiciona par: ID_Maquina [TAB] Tempo
                        linha_txt.append(f"{m}\t{tempo}")
                    
                    # Une tudo com TAB e escreve
                    f.write("\t".join(linha_txt) + "\n")

                # --- SSD (SETUP TIMES) ---
                f.write("SSD\n")
                
                for m in range(M):
                    f.write(f"M{m}\n")
                    matriz = s_dict.get(m, [])
                    
                    if not matriz: 
                        matriz = [[0]*N for _ in range(N)]
                    
                    for idx_linha, row in enumerate(matriz):
                        linha_valores = [str(idx_linha)] + [str(v) for v in row]
                        
                        # Une com TAB
                        linha_str = "\t".join(linha_valores)
                        f.write(linha_str + "\n")
            
            #print(f"Sucesso: Arquivo salvo em {caminho}")

        except Exception as e:
            tk.messagebox.showerror("Error", f"Failed to save file:\n{e}")
            print(f"Erro detalhado save: {e}")

    # PARSER
    def acao_load_instance(self):
        caminho = filedialog.askopenfilename(
            parent=self, 
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if not caminho: return

        try:
            with open(caminho, 'r') as f:
                # Lê todas as linhas removendo espaços em branco extras
                linhas = [l.strip() for l in f.readlines() if l.strip()]

            if not linhas: return

            # Ler Cabeçalho (N Jobs, M Máquinas)
            cabecalho = list(map(int, linhas[0].split()))
            n_jobs = cabecalho[0]
            n_maquinas = cabecalho[1]

            segunda_linha = list(map(int, linhas[1].split()))
            if len(segunda_linha) == 1:
                inicio_proc = 2
            else:
                inicio_proc = 1

            # Inicializa matriz MxN com zeros
            matriz_proc = [[0]*n_jobs for _ in range(n_maquinas)]
            
            # Ler Processing Times
            for j in range(n_jobs):
                if (inicio_proc + j) >= len(linhas): break
                
                linha_raw = list(map(int, linhas[inicio_proc + j].split()))
                
                # A linha tem pares: (maq_id, tempo) -> Ex: 0 67 1 12 ...
                # maq_id no arquivo é 0-based
                for k in range(0, len(linha_raw), 2):
                    if k+1 >= len(linha_raw): break
                    maq_idx = linha_raw[k] 
                    tempo = linha_raw[k+1]
                    
                    if maq_idx < n_maquinas:
                        matriz_proc[maq_idx][j] = tempo

            # Ler Setups
            setups = {} 
            # O bloco SSD começa logo apOs os jobs
            idx_busca_ssd = inicio_proc + n_jobs
            
            idx_ssd = -1
            for i in range(idx_busca_ssd, len(linhas)):
                if linhas[i] == "SSD":
                    idx_ssd = i
                    break
            
            if idx_ssd != -1:
                idx_atual = idx_ssd + 1
                
                # Ler blocos de máquinas
                # O formato é: "M0", depois N linhas de matriz, depois "M1", etc.
                maquina_atual = -1
                
                while idx_atual < len(linhas):
                    conteudo = linhas[idx_atual]
                    
                    if conteudo.startswith("M"):
                        # Nova máquina encontrada (ex: "M0")
                        try:
                            # Extrai o número depois do M (M0 -> 0)
                            maquina_atual = int(conteudo[1:])
                        except:
                            maquina_atual = -1
                        
                        idx_atual += 1
                        
                        # Se identificou uma máquina válida, lê as próximas N linhas
                        if 0 <= maquina_atual < n_maquinas:
                            matriz_m = []
                            for _ in range(n_jobs):
                                if idx_atual >= len(linhas): break
                                vals = list(map(int, linhas[idx_atual].split()))
                                matriz_m.append(vals)
                                idx_atual += 1
                            setups[maquina_atual] = matriz_m
                        else:
                            # Se não for marcador de máquina válido ou acabou, continua
                            pass
                    else:
                        idx_atual += 1

            # Salvar em memOria
            self.dados_instancia = {
                "loaded": True,
                "nome": os.path.basename(caminho),
                "N": n_jobs,
                "M": n_maquinas,
                "processing": matriz_proc,
                "setup": setups
            }

            #Atualizar Interface
            self.atualizar_interface_pos_load()

        except Exception as e:
            print(f"Erro ao ler instância: {e}")
            tk.messagebox.showerror("Error", f"Failed to parse instance:\n{e}")

    def atualizar_interface_pos_load(self):
        dados = self.dados_instancia
        
        # Atualiza os valores nos campos específicos
        self.lbl_val_nome.configure(text=dados['nome'])
        self.lbl_val_mach.configure(text=str(dados['M']))
        self.lbl_val_jobs.configure(text=str(dados['N']))

        filhos = self.tree_side.get_children(self.node_setup)
        for f in filhos: self.tree_side.delete(f)

        for m in range(dados['M']):
            self.tree_side.insert(self.node_setup, "end", text=f"    📁 M{m}", values=("setup", f"{m}"))

        self.exibir_processing_times()
        self.tree_side.item(self.node_setup, open=True)

    def ao_selecionar_sidebar(self, event):
        sel = self.tree_side.selection()
        if not sel: return
        
        self.salvar_alteracoes_da_view_atual()

        # Descobre o novo item selecionado
        item = self.tree_side.item(sel[0])
        tipo = item['values'][0] 
        tag = item['values'][1]  

        if not self.dados_instancia["loaded"]: return

        # Carrega o novo item
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

        # Atualiza apenas o label de contexto na direita
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

        # Atualiza apenas o label de contexto na direita
        self.lbl_context.configure(text=f"Editing: Setup Times (Machine {maquina_idx})")
        
        self.sheet.headers(headers)
        self.sheet.row_index(row_indices) 
        self.sheet.set_sheet_data(dados)

def abrir_editor_janela(root_parent=None):
    if root_parent:
        app = InstanceEditor(root_parent)
    else:
        app = InstanceEditor(None)
        app.mainloop()
if __name__ == "__main__":
    ctk.set_appearance_mode("Dark")
    abrir_editor_janela()