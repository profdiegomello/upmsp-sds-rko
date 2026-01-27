import os
import matplotlib
matplotlib.use('Agg') # Backend não-interativo para gerar imagens sem travar a GUI
import matplotlib.pyplot as plt
import numpy as np


def calcula_gap(lowerbound, objetivo):
    if lowerbound == 0:
        return 0.0
    gap = ((objetivo - lowerbound) / lowerbound) * 100
    return gap

def salvar_resultado(
    arquivo_saida: str,
    instancia: str,
    modelo: str,
    objetivo: float,
    lowerbound,  # Pode ser float ou None
    gap,         # Pode ser float ou None
    runtime: float,
    constraints: int,
    variables: int,
    parameters: str,
    jobs: int,
    machines: int,
    status: str
):

    print(f"Melhor makespan encontrado: {objetivo}")

    # Registra os resultados no arquivo passado, usando tabulação como separador.
    # Caso lowerbound ou gap sejam None, registra como '---'.

    # Verifica se o arquivo já existe para saber se deve escrever o cabeçalho
    novo_arquivo = not os.path.exists(arquivo_saida)

    # Se lowerbound ou gap forem None, vamos definir uma string padrão '---'
    if lowerbound is not None and lowerbound != 0:
    
        if gap is not None:
           gap_str = gap
        else:
            gap_str = calcula_gap(lowerbound, objetivo)
            
        lowerbound_str = lowerbound
    
    else:
        gap_str="---"
        lowerbound_str = "---"

    if objetivo is not None:
        objetivo_str = f"{objetivo:.4f}"
    else:
        objetivo_str = "---"


    # Apenas solvers MIP contém restricoes e variaveis        
    if constraints == 0:
        constraints_str = '---'
        variables_str = '---'
    else:
        constraints_str = str(constraints)
        variables_str = str(variables)
        

    with open(arquivo_saida, "a") as f:
        # Escreve o cabeçalho se o arquivo for novo
        if novo_arquivo:
            f.write("INSTANCE\tJOBS\tMACHINE\tMODEL\tSTATUS\tOBJECTIVE\tLOWERBOUND\tGAP\tRUNTIME\tCONSTRAINTS\tVARIABLES\tPARAMETERS\n")

        # Formata a linha com os valores, separando por tabulação
        linha = (f"{instancia}\t"
                 f"{jobs}\t"
                 f"{machines}\t"
                 f"{modelo}\t"
                 f"{status}\t"
                 f"{objetivo_str}\t"
                 f"{lowerbound_str}\t"
                 f"{gap_str}\t"
                 f"{runtime:.4f}\t"
                 f"{constraints_str}\t"
                 f"{variables_str}\t"
                 f"{parameters}\n")
        f.write(linha)

#
# Constroi grafico de Gantt (MODO ESCURO)
#
def gantt_chart(M, N, N0, p, s, X, C, arq_gantt, instancia, makespan, str_metodo):
    """
    Gera um gráfico de Gantt com tema escuro.
    """
    
    # Cria a figura
    fig, ax = plt.subplots(figsize=(12, 6))


    COR_FUNDO = "#DDDDDD"  # Cinza escuro (quase preto)
    
    fig.patch.set_facecolor(COR_FUNDO) # Fundo da imagem
    ax.set_facecolor(COR_FUNDO)        # Fundo da área do gráfico

    # Bordas (Spines) em branco
    ax.spines['bottom'].set_color('black')
    ax.spines['top'].set_color('black') 
    ax.spines['left'].set_color('black')
    ax.spines['right'].set_color('black')
    
    # Cor dos textos dos eixos (Ticks e Labels)
    ax.tick_params(axis='x', colors='black')
    ax.tick_params(axis='y', colors='black')
    ax.xaxis.label.set_color('black')
    ax.yaxis.label.set_color('black')
    
    # Cor do Título
    ax.title.set_color('black')
    # =================================================================
    
    # Cores para os jobs (Tab20 é bom para distinguir muitos jobs)
    colors = plt.cm.get_cmap("tab20", len(N)) 

    max_completion_time = 0

    # Iterar sobre as máquinas e jobs para desenhar as barras
    for i in M:
        for j in N:
            # Verifica se o job j está alocado em alguma sequência na máquina i
            is_job_on_machine = any(X.get((i, k, j), 0) > 0.5 for k in N0)
            
            if is_job_on_machine:
                completion_time = C.get((i, j), 0)
                processing_time = p.get((i, j), 0)
                start_time = completion_time - processing_time

                # Atualiza o tempo máximo de conclusão
                if completion_time > max_completion_time:
                    max_completion_time = completion_time

                # Desenha a barra do job
                ax.barh(
                    y=f'M{i}', 
                    width=processing_time, 
                    left=start_time, 
                    height=0.6, 
                    color=colors(j - 1), 
                    edgecolor='black', # Borda preta na barra ajuda no contraste com as cores do job
                    alpha=0.9
                )
                
                # Adiciona o nome do job no centro da barra (TEXTO BRANCO)
                ax.text(
                    start_time + processing_time / 2,
                    f'M{i}', 
                    f'{j}',
                    ha='center',
                    va='center',
                    color='white',      
                    fontsize=8,
                    fontweight='bold'   # Negrito para leitura melhor
                )

    # Configurações do gráfico
    ax.set_xlabel("Tempo")
    ax.set_ylabel("Máquinas")
    ax.set_title(f"Makespan: {round(makespan,4)} ({str_metodo}) - {instancia}")
    
    # Ajustar o eixo Y para inverter a ordem (Máquina 1 no topo)
    ax.invert_yaxis()
    
    # Ajuste dos ticks do eixo X
    step = max(1, int((max_completion_time + 2) / 30))
    ax.set_xticks(np.arange(0, max_completion_time + 2, step))
    plt.setp(ax.get_xticklabels(), rotation=90, fontsize=8)

    # Grade (Grid) branca e suave
    ax.grid(axis='x', linestyle='--', alpha=0.3, color='#808080')
    
    plt.tight_layout()

    # Salvar o gráfico
    # Adicionamos facecolor na hora de salvar para garantir que o fundo vá junto
    plt.savefig(
        f'{arq_gantt}-{str_metodo}.png', 
        dpi=300, 
        bbox_inches='tight', 
        facecolor=fig.get_facecolor()
    )

    plt.close(fig)