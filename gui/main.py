import customtkinter as ctk
import sys
import os

# Ajuste de path para importações funcionarem
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from interface.ui import abrir_benchmark 
from interface.instance_editor import abrir_editor_janela

class Launcher(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("RKO Solver Launcher")
        
        #centralizacao
        largura_janela = 500
        altura_janela = 450

        largura_tela = self.winfo_screenwidth()
        altura_tela = self.winfo_screenheight()

        # Calcula a posição x e y para centralizar
        pos_x = int((largura_tela / 2) - (largura_janela / 2))
        pos_y = int((altura_tela / 2) - (altura_janela / 2))

        # Define a geometria: LarguraxAltura + PosX + PosY
        self.geometry(f"{largura_janela}x{altura_janela}+{pos_x}+{pos_y}")
        self.resizable(False, False)

        # Protocolo de Fechamento
        self.protocol("WM_DELETE_WINDOW", self.encerrar_aplicacao)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(5, weight=1)

        # Titulo
        self.lbl_titulo = ctk.CTkLabel(self, text="RKO OPTIMIZER", font=("Roboto", 28, "bold"), text_color="#6D28D9")
        self.lbl_titulo.grid(row=0, column=0, pady=(40, 10))
        
        self.lbl_subtitulo = ctk.CTkLabel(self, text="Select a module to start:", font=("Roboto", 14), text_color="gray")
        self.lbl_subtitulo.grid(row=1, column=0, pady=(0, 30))

        
        #  Create Instance
        self.btn_create = ctk.CTkButton(
            self, 
            text="➕  Create Instance", 
            font=("Roboto", 14, "bold"), 
            height=50, 
            width=280, 
            fg_color="#333333",       
            hover_color="#6D28D9",    
            command=self.abrir_create
        )
        self.btn_create.grid(row=2, column=0, pady=10)

        # Edit Instance
        self.btn_edit = ctk.CTkButton(
            self, 
            text="✏️  Edit Instance", 
            font=("Roboto", 14, "bold"), 
            height=50, 
            width=280, 
            fg_color="#333333",       
            hover_color="#6D28D9",    
            command=self.abrir_edit
        )
        self.btn_edit.grid(row=3, column=0, pady=10)

        #  Benchmark
        self.btn_bench = ctk.CTkButton(
            self, 
            text="🚀  Benchmark & Run", 
            font=("Roboto", 14, "bold"), 
            height=50, 
            width=280, 
            fg_color="#333333",       
            hover_color="#6D28D9",    
            command=self.abrir_benchmark_app
        )
        self.btn_bench.grid(row=4, column=0, pady=10)

        # Footer
        ctk.CTkLabel(self, text="v1.0.0 - Scientific Initiation Project", font=("Arial", 10), text_color="#444444").grid(row=5, column=0, pady=20)

    def abrir_benchmark_app(self):
        try:
            abrir_benchmark(root_parent=self) 
        except Exception as e:
            print(f"Erro ao abrir Benchmark: {e}")

    def abrir_edit(self):
        try:
            abrir_editor_janela(root_parent=self)
        except Exception as e:
            print(f"Erro ao abrir Editor: {e}")

    def abrir_create(self):
        # Janela 'filha' tambem centralizada em relacao ao pai ou tela
        top = ctk.CTkToplevel(self)
        top.title("Creator")
        w, h = 300, 200
        x = int((self.winfo_screenwidth()/2) - (w/2))
        y = int((self.winfo_screenheight()/2) - (h/2))
        top.geometry(f"{w}x{h}+{x}+{y}")
        
        ctk.CTkLabel(top, text="Creator Module\nComing Soon...").pack(expand=True)

    def encerrar_aplicacao(self):
        self.destroy()
        sys.exit(0)

if __name__ == "__main__":
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("dark-blue")
    app = Launcher()
    app.mainloop()