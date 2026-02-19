import customtkinter as ctk
from PIL import Image
import os
import sys

def resource_path(relative_path):
    """ Obtem o caminho absoluto para recursos"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# --- MUDANÇA: Adicionado analysis_tab no final ---
def create_buttons(master, show_tab, knight_tab, sliders_tab, play_tab, chart_tab, gantt_tab, history_tab, analysis_tab):
    """
    Cria os botoes laterais (Knight, Sliders, Play, Chart, Gantt, History, Analysis).
    """
    # Frame lateral
    buttons_frame = ctk.CTkFrame(master, width=40, height=400, fg_color="transparent") # Aumentei um pouco a altura para caber mais um
    buttons_frame.grid(row=2, column=0, columnspan=2, sticky="ns")
    buttons_frame.grid_propagate(False)

    #  CARREGANDO IMAGENS 
    knight_image = ctk.CTkImage(Image.open(resource_path("assets/knight.png")), size=(20, 20))
    sliders_image = ctk.CTkImage(Image.open(resource_path("assets/sliders.png")), size=(20, 20))
    play_image = ctk.CTkImage(Image.open(resource_path("assets/play.png")), size=(20, 20))
    chart_image = ctk.CTkImage(Image.open(resource_path("assets/chart.png")), size=(20, 20))
    gantt_image = ctk.CTkImage(Image.open(resource_path("assets/gantt.png")), size=(20, 20)) 
    history_image = ctk.CTkImage(Image.open(resource_path("assets/history.png")), size=(20, 20))
    
    # --- NOVO ---
    magnifier_image = ctk.CTkImage(Image.open(resource_path("assets/magnifier.png")), size=(20, 20))

    # BOTOES 
    
    # Knight (Parâmetros + IO)
    knight_button = ctk.CTkButton(
        buttons_frame, text="", image=knight_image,
        width=25, height=25, fg_color="transparent", hover_color="#444444",
        command=lambda: show_tab(knight_tab)
    )
    knight_button.grid(row=0, column=0, pady=10, padx=5)

    # Sliders (Agentes)
    sliders_button = ctk.CTkButton(
        buttons_frame, text="", image=sliders_image,
        width=25, height=25, fg_color="transparent", hover_color="#444444",
        command=lambda: show_tab(sliders_tab)
    )
    sliders_button.grid(row=1, column=0, pady=10, padx=5)
    
    # Play (Execucao)
    play_button = ctk.CTkButton(
        buttons_frame, text="", image=play_image,
        width=25, height=25, fg_color="transparent", hover_color="#444444",
        command=lambda: show_tab(play_tab)
    )
    play_button.grid(row=2, column=0, pady=10, padx=5)

    # Chart (Grafico de Linha)
    chart_button = ctk.CTkButton(
        buttons_frame, text="", image=chart_image,
        width=25, height=25, fg_color="transparent", hover_color="#444444",
        command=lambda: show_tab(chart_tab)
    )
    chart_button.grid(row=3, column=0, pady=10, padx=5) 

    # Gantt
    gantt_button = ctk.CTkButton(
        buttons_frame, text="", image=gantt_image,
        width=25, height=25, fg_color="transparent", hover_color="#444444",
        command=lambda: show_tab(gantt_tab) 
    )
    gantt_button.grid(row=4, column=0, pady=10, padx=5)

    # History
    history_button = ctk.CTkButton(
        buttons_frame, text="", image=history_image,
        width=25, height=25, fg_color="transparent", hover_color="#444444",
        command=lambda: show_tab(history_tab) 
    )
    history_button.grid(row=5, column=0, pady=10, padx=5)

    # Analysis 
    analysis_button = ctk.CTkButton(
        buttons_frame, text="", image=magnifier_image,
        width=25, height=25, fg_color="transparent", hover_color="#444444",
        command=lambda: show_tab(analysis_tab) 
    )
    analysis_button.grid(row=6, column=0, pady=10, padx=5)

    return buttons_frame