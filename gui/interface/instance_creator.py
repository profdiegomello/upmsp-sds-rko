import customtkinter as ctk
from tkinter import ttk, filedialog
import tkinter as tk
import os
import sys
import random

# Tenta importar o tksheet
try:
    from tksheet import Sheet
except ImportError:
    Sheet = None 

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
        self.geometry("1200x700") 
        
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
        
        # Rastreia o que está selecionado na árvore: ("tipo", "tag")
        self.selecao_atual = ("general", "root")

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
        
        # Mostra General por padrao
        self.mostrar_general()

    def ao_fechar(self):
        self.destroy()

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

        # Nos Fixos
        self.node_general = self.tree.insert("", "end", text=" ⚙️ General Settings", values=("general", "root"))
        self.node_proc = self.tree.insert("", "end", text=" 📂 Processing Times", values=("proc", "root"))
        self.node_setup = self.tree.insert("", "end", text=" 📂 Setup Times", values=("setup", "root"))

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

        # Randomize Selected
        self.btn_rand_sel = ctk.CTkButton(self.frm_header, text="RANDOMIZE SELECTED", width=120,
                                          fg_color=CORES_CREATOR["btn_primary"], hover_color=CORES_CREATOR["btn_hover"],
                                          state="disabled", command=self.acao_randomizar_selecionado)
        self.btn_rand_sel.pack(side="left", padx=(0, 10))

        # Randomize Processing
        self.btn_rand_proc = ctk.CTkButton(self.frm_header, text="RANDOMIZE PROCESSING", width=130,
                                          fg_color=CORES_CREATOR["btn_primary"], hover_color=CORES_CREATOR["btn_hover"],
                                          state="disabled", command=self.acao_randomizar_apenas_processing)
        self.btn_rand_proc.pack(side="left", padx=(0, 10))

        # Randomize All Setups
        self.btn_rand_setups = ctk.CTkButton(self.frm_header, text="RANDOMIZE ALL SETUPS", width=130,
                                          fg_color=CORES_CREATOR["btn_primary"], hover_color=CORES_CREATOR["btn_hover"],
                                          state="disabled", command=self.acao_randomizar_apenas_setups)
        self.btn_rand_setups.pack(side="left", padx=(0, 20))

        # Save 
        self.btn_save = ctk.CTkButton(self.frm_header, text="💾 SAVE", width=100,
                                      fg_color="green", hover_color="darkgreen",
                                      state="disabled", command=self.acao_salvar_arquivo)
        self.btn_save.pack(side="right", padx=15)
        
        # Label de Status (Feedback sutil)
        self.lbl_status = ctk.CTkLabel(self.frm_header, text="", font=("Roboto", 12, "italic"))
        self.lbl_status.pack(side="right", padx=10)

    def criar_general_view(self):
        self.frm_general = ctk.CTkFrame(self.frm_content, fg_color="transparent")
        
        ctk.CTkLabel(self.frm_general, text="GENERAL SETTINGS", font=("Roboto", 24, "bold"), text_color="white").pack(pady=(60, 30))

        # Box Dimensions
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

        # Big Action Button
        self.btn_gen_empty = ctk.CTkButton(self.frm_general, text="GENERATE STRUCTURE", height=45, width=300,
                                           font=("Roboto", 13, "bold"),
                                           fg_color=CORES_CREATOR["btn_action"], hover_color=CORES_CREATOR["btn_action_hover"],
                                           command=self.acao_gerar_vazia)
        self.btn_gen_empty.pack(pady=30)
        
        ctk.CTkLabel(self.frm_general, text="Note: Generating a new structure will reset all current data.", text_color="gray").pack()

    def criar_sheet_view(self):
        self.frm_sheet = ctk.CTkFrame(self.frm_content, fg_color=CORES_CREATOR["grid_bg"])
        
        # Headerzinho da sheet
        frm_header = ctk.CTkFrame(self.frm_sheet, height=30, fg_color="transparent")
        frm_header.pack(fill="x", padx=10, pady=5)
        self.lbl_sheet_title = ctk.CTkLabel(frm_header, text="VIEWING MODE", font=("Roboto", 12, "bold"), text_color=CORES_CREATOR["text_highlight"])
        self.lbl_sheet_title.pack(side="left")

        # Tabela
        self.sheet_container = ctk.CTkFrame(self.frm_sheet, fg_color=CORES_CREATOR["grid_bg"])
        self.sheet_container.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        if Sheet:
            self.sheet = Sheet(self.sheet_container, headers=[], data=[], theme="dark", empty_horizontal=0, empty_vertical=0)
            self.sheet.enable_bindings(("single_select", "row_select", "column_select", "drag_select", "arrowkeys"))
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

    def mostrar_general(self):
        self.frm_sheet.pack_forget()
        self.frm_general.pack(fill="both", expand=True)
    
    def mostrar_sheet(self):
        self.frm_general.pack_forget()
        self.frm_sheet.pack(fill="both", expand=True)

    def ao_selecionar_tree(self, event):
        sel = self.tree.selection()
        if not sel: return
        
        item = self.tree.item(sel[0])
        tipo = item['values'][0]
        tag = item['values'][1]
        
        self.selecao_atual = (tipo, tag)

        if tipo == "general":
            self.mostrar_general()
            self.btn_rand_sel.configure(state="disabled") 
        else:
            if not self.dados["created"]:
                self.tree.selection_set(self.node_general)
                tk.messagebox.showinfo("Info", "Please generate the structure first.", parent=self)
                return
            
            self.btn_rand_sel.configure(state="normal")
            
            self.mostrar_sheet()
            if tipo == "proc":
                self.carregar_proc_sheet()
            elif tipo == "setup" and tag != "root":
                self.carregar_setup_sheet(int(tag))

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

        filhos = self.tree.get_children(self.node_setup)
        for f in filhos: self.tree.delete(f)
        for m in range(M):
            self.tree.insert(self.node_setup, "end", text=f"    📁 M{m}", values=("setup", f"{m}"))

        # Habilita todos os botoes de acao global
        self.btn_rand_proc.configure(state="normal")
        self.btn_rand_setups.configure(state="normal")
        self.btn_save.configure(state="normal")
        
        self.lbl_status.configure(text=f"Structure ({M}x{N}) generated", text_color=CORES_CREATOR["success_text"])

    def acao_randomizar_selecionado(self):
        if not self.dados["created"]: return
        v_min, v_max = self._get_range()
        if v_min is None: return

        tipo, tag = self.selecao_atual
        N, M = self.dados["N"], self.dados["M"]
        msg = ""

        if tipo == "proc":
            # Randomiza Processing Times
            for r in range(M):
                for c in range(N):
                    self.dados["processing"][r][c] = random.randint(v_min, v_max)
            msg = "Selected: Processing Times Randomized"
            self.carregar_proc_sheet()

        elif tipo == "setup" and tag != "root":
            # Randomiza Setup da Maquina Especifica
            m_id = int(tag)
            for r in range(N):
                for c in range(N):
                    if r == c: self.dados["setup"][m_id][r][c] = 0
                    else: self.dados["setup"][m_id][r][c] = random.randint(v_min, v_max)
            msg = f"Selected: Setup Times for M{m_id} Randomized"
            self.carregar_setup_sheet(m_id)

        else:
            self.lbl_status.configure(text="Select a valid table on the left.", text_color="orange")
            return

        self.lbl_status.configure(text=msg, text_color=CORES_CREATOR["success_text"])

    def acao_randomizar_apenas_processing(self):
        if not self.dados["created"]: return
        v_min, v_max = self._get_range()
        if v_min is None: return

        M, N = self.dados["M"], self.dados["N"]

        # Randomiza APENAS Processing
        for r in range(M):
            for c in range(N):
                self.dados["processing"][r][c] = random.randint(v_min, v_max)
        
        # Refresh se estiver vendo processing
        tipo, _ = self.selecao_atual
        if tipo == "proc": self.carregar_proc_sheet()

        self.lbl_status.configure(text="Processing Times randomized successfully", text_color=CORES_CREATOR["success_text"])

    def acao_randomizar_apenas_setups(self):
        if not self.dados["created"]: return
        v_min, v_max = self._get_range()
        if v_min is None: return

        M, N = self.dados["M"], self.dados["N"]

        # Randomiza APENAS Setups (todas as maquinas)
        for m in range(M):
            for r in range(N):
                for c in range(N):
                    if r == c: self.dados["setup"][m][r][c] = 0
                    else: self.dados["setup"][m][r][c] = random.randint(v_min, v_max)

        # Refresh se estiver vendo algum setup
        tipo, tag = self.selecao_atual
        if tipo == "setup" and tag != "root": self.carregar_setup_sheet(int(tag))

        self.lbl_status.configure(text="All Setup Times randomized successfully", text_color=CORES_CREATOR["success_text"])

    def acao_salvar_arquivo(self):
        if not self.dados["created"]: return

        nome_sugerido = f"I_{self.dados['N']}_{self.dados['M']}_Generated.txt"
        caminho = filedialog.asksaveasfilename(
            parent=self,
            initialfile=nome_sugerido,
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt")]
        )
        if not caminho: return

        try:
            N, M = self.dados["N"], self.dados["M"]
            p_matrix = self.dados["processing"]
            s_dict = self.dados["setup"]

            with open(caminho, "w") as f:
                f.write(f"{N}\t{M}\t1\n")
                f.write(f"{M}\n")
                
                for j in range(N):
                    linha_txt = []
                    for m in range(M):
                        linha_txt.append(f"{m}\t{p_matrix[m][j]}")
                    f.write("\t".join(linha_txt) + "\n")
                
                f.write("SSD\n")
                for m in range(M):
                    f.write(f"M{m}\n")
                    matriz = s_dict[m]
                    for idx_linha, row in enumerate(matriz):
                        linha_vals = [str(idx_linha)] + [str(v) for v in row]
                        f.write("\t".join(linha_vals) + "\n")
            
            self.lbl_status.configure(text=f"Saved to: {os.path.basename(caminho)}", text_color=CORES_CREATOR["success_text"])

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

    def carregar_setup_sheet(self, m_id):
        if not Sheet: return
        self.lbl_sheet_title.configure(text=f"PREVIEW: SETUP TIMES (M{m_id})")
        dados = self.dados["setup"][m_id]
        N = self.dados["N"]
        self.sheet.headers([f"J{i}" for i in range(N)])
        self.sheet.row_index([f"J{i}" for i in range(N)])
        self.sheet.set_sheet_data(dados)

def abrir_creator_janela(root_parent=None):
    if root_parent:
        app = InstanceCreator(root_parent)
    else:
        app = InstanceCreator(None)
        app.mainloop()

if __name__ == "__main__":
    ctk.set_appearance_mode("Dark")
    abrir_creator_janela()