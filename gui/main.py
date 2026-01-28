import sys
import os
import multiprocessing

#GARANTE QUE O DIRETORIO `gui/` ESTEJA NO sys.path 
GUI_ROOT = os.path.dirname(os.path.abspath(__file__))
if GUI_ROOT not in sys.path:
    sys.path.insert(0, GUI_ROOT)

from interface.buttons import create_buttons
from interface.ui import construir_aplicacao

def main():
    # cria a janela e tabs
    janela, show_tab, knight_tab, sliders_tab, io_tab, play_tab, chart_tab, gantt_tab = construir_aplicacao()

    # cria os botoes
    buttons_frame = create_buttons(janela,
                                    show_tab,
                                    knight_tab,
                                    sliders_tab,
                                    io_tab,
                                    play_tab,
                                    chart_tab,
                                    gantt_tab
                                    )
    
    # inicia a interface
    janela.mainloop()

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
