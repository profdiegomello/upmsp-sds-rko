from buttons import create_buttons         
from ui import build_app                   


#OBS: CODIGO SUJEITO A MUDANCAS E REFATORACOES
#VERSAO 1.0
#19/12/2025 , JOAO VITOR FONSECA

# Para executar basta instalar as dependencias em requirements.txt
# Em seguida, execute o arquivo app.py -> python3 app.py


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
