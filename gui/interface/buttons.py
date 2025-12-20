import customtkinter as ctk
from PIL import Image
import os
import sys



def resource_path(relative_path):
    """ Obtém o caminho absoluto para recursos, funcione em dev ou PyInstaller """
    try:
        # PyInstaller cria uma pasta temporária e armazena o caminho em _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)



def create_buttons(master, show_tab, knight_tab, sliders_tab, scroll_tab, play_tab):
    """
    Cria os botões laterais (Knight, Sliders, IO) dentro de um frame.
    
    master: frame onde os botões serão colocados
    show_tab: função que alterna entre as abas
    knight_tab, sliders_tab, scroll_tab: frames das abas
    """

    # Frame lateral para os botões
    buttons_frame = ctk.CTkFrame(master, width=40, height=300, fg_color="transparent")
    buttons_frame.grid(row=2, column=0, columnspan=2, sticky="ns")
    buttons_frame.grid_propagate(False)

    # Imagens
    knight_image = ctk.CTkImage(Image.open(resource_path("assets/knight.png")), size=(16, 16))
    sliders_image = ctk.CTkImage(Image.open(resource_path("assets/sliders.png")), size=(16, 16))
    scroll_image = ctk.CTkImage(Image.open(resource_path("assets/scroll.png")), size=(16, 16))
    play_image = ctk.CTkImage(Image.open(resource_path("assets/play.png")), size=(16, 16))

    # Botões
    knight_button = ctk.CTkButton(
        buttons_frame, text="", image=knight_image,
        width=18, fg_color="transparent",
        command=lambda: show_tab(knight_tab)
    )
    knight_button.grid(row=0, column=0, pady=10, padx=5)

    sliders_button = ctk.CTkButton(
        buttons_frame, text="", image=sliders_image,
        width=18, fg_color="transparent",
        command=lambda: show_tab(sliders_tab)
    )
    sliders_button.grid(row=1, column=0, pady=10, padx=5)

    scroll_button = ctk.CTkButton(
        buttons_frame, text="", image=scroll_image,
        width=18, fg_color="transparent",
        command=lambda: show_tab(scroll_tab)
    )
    scroll_button.grid(row=2, column=0, pady=10, padx=5)
    
    play_button = ctk.CTkButton(
        buttons_frame, text="", image=play_image,
        width=18, fg_color="transparent",
        command=lambda: show_tab(play_tab)
    )
    play_button.grid(row=3, column=0, pady=10, padx=5)


    return buttons_frame
