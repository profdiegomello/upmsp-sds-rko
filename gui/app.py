from buttons import create_buttons         
from ui import build_app                   

def main():
    # build_app cria a janela, tabs e a função show_tab
    janela, show_tab, knight_tab, sliders_tab, io_tab, play_tab = build_app()

    # cria os botões (assume a assinatura: create_buttons(janela, show_tab, knight_tab, sliders_tab, io_tab))
    buttons_frame = create_buttons(janela, show_tab, knight_tab, sliders_tab, io_tab, play_tab)
    
    print()

    # inicia a interface
    janela.mainloop()

if __name__ == "__main__":
    main()
