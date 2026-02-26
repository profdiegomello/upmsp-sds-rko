import customtkinter as ctk
import sys
import os
from tkinter import messagebox
from PIL import Image # Necessário para carregar imagens

# Ajuste de path para importacoes funcionarem
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from interface.ui import abrir_benchmark 
from interface.instance_editor import abrir_editor_janela
from interface.instance_creator import abrir_creator_janela

class Launcher(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("RKO Solver Launcher")
        
        # --- LOGICA DE CENTRALIZACAO ---
        largura_janela = 500
        altura_janela = 450

        largura_tela = self.winfo_screenwidth()
        altura_tela = self.winfo_screenheight()

        pos_x = int((largura_tela / 2) - (largura_janela / 2))
        pos_y = int((altura_tela / 2) - (altura_janela / 2))

        self.geometry(f"{largura_janela}x{altura_janela}+{pos_x}+{pos_y}")
        self.resizable(False, False)
        
        # Define o protocolo: Quando clicar no X, chama self.encerrar_aplicacao
        self.protocol("WM_DELETE_WINDOW", self.encerrar_aplicacao)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(5, weight=1)

        # --- CARREGAMENTO DE ÍCONES ---
        self.icons = {}
        try:
            # Carrega Imagem do Foguete
            image_path_rocket = self.resource_path("assets/rocket-launcher.png")
            img_rocket = Image.open(image_path_rocket)
            self.icons["rocket"] = ctk.CTkImage(light_image=img_rocket, dark_image=img_rocket, size=(30, 30))

            # Carrega Imagem do Lápis
            image_path_pencil = self.resource_path("assets/pencil.png")
            img_pencil = Image.open(image_path_pencil)
            self.icons["pencil"] = ctk.CTkImage(light_image=img_pencil, dark_image=img_pencil, size=(30, 30))

            # Carrega Imagem do Plus
            image_path_plus = self.resource_path("assets/plus.png")
            img_plus = Image.open(image_path_plus)
            self.icons["plus"] = ctk.CTkImage(light_image=img_plus, dark_image=img_plus, size=(28, 28))
            
        except Exception as e:
            print(f"Aviso: Não foi possível carregar ícones da pasta assets. Erro: {e}")
            self.icons["rocket"] = None
            self.icons["pencil"] = None
            self.icons["plus"] = None

        # Titulo
        self.lbl_titulo = ctk.CTkLabel(self, text="RKO OPTIMIZER", font=("Roboto", 28, "bold"), text_color="#6D28D9")
        self.lbl_titulo.grid(row=0, column=0, pady=(40, 10))
        
        self.lbl_subtitulo = ctk.CTkLabel(self, text="Select a module to start:", font=("Roboto", 14), text_color="gray")
        self.lbl_subtitulo.grid(row=1, column=0, pady=(0, 30))

        
        # Create Instance 
        self.btn_create = ctk.CTkButton(
            self, 
            text="Create Instance", # Sem emoji
            image=self.icons["plus"],
            compound="left",        # Imagem à esquerda
            font=("Roboto", 14, "bold"), 
            height=50, 
            width=280, 
            fg_color="#333333",       
            hover_color="#6D28D9",    
            command=self.abrir_create
        )
        self.btn_create.grid(row=2, column=0, pady=10)

        # Edit Instance (Lápis)
        self.btn_edit = ctk.CTkButton(
            self, 
            text="Edit Instance",   # Sem emoji
            image=self.icons["pencil"],
            compound="left",        # Imagem à esquerda
            font=("Roboto", 14, "bold"), 
            height=50, 
            width=280, 
            fg_color="#333333",       
            hover_color="#6D28D9",    
            command=self.abrir_edit
        )
        self.btn_edit.grid(row=3, column=0, pady=10)

        # Benchmark (Foguete)
        self.btn_bench = ctk.CTkButton(
            self, 
            text="Benchmark & Run", # Sem emoji
            image=self.icons["rocket"],
            compound="left",        # Imagem à esquerda
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

    def resource_path(self, relative_path):
        """Obtém o caminho absoluto para o recurso, funciona para dev e PyInstaller"""
        try:
            # PyInstaller cria uma pasta temporária em _MEIPASS
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")

        return os.path.join(base_path, relative_path)

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
        try:
            abrir_creator_janela(root_parent=self)
        except Exception as e:
            print(f"Erro ao abrir Creator: {e}")

    def encerrar_aplicacao(self):
        """Pergunta antes de fechar tudo"""
        resposta = messagebox.askyesno(
            "Confirm Exit", 
            "Are you sure you want to close the launcher?\nAll opened windows will be closed.",
            parent=self
        )
        
        if resposta: # Se o usuário clicou em Sim
            self.quit()
            self.destroy()
            sys.exit(0)

if __name__ == "__main__":
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("dark-blue")
    app = Launcher()
    app.mainloop()