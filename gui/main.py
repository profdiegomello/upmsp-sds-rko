# main.py
from interface.buttons import create_buttons       
from interface.ui import construir_aplicacao                    

def main():
    # cria a janela e tabs
    janela, show_tab, knight_tab, sliders_tab, io_tab, play_tab = construir_aplicacao()

    # cria os botões 
    buttons_frame = create_buttons(janela, show_tab, knight_tab, sliders_tab, io_tab, play_tab)
    
    # inicia a interface
    janela.mainloop()

if __name__ == "__main__":
    main()
