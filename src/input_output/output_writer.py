import os
import matplotlib.pyplot as plt
import numpy as np


#################################################################################################
#
# 
#
#################################################################################################

def calcula_gap(lowerbound, objetivo):
    gap=((objetivo-lowerbound)/lowerbound)*100
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

   # Registra os resultados no arquivo passado, usando tabulação como separador.
   # Caso lowerbound ou gap sejam None, registra como '---'.

    # Verifica se o arquivo já existe para saber se deve escrever o cabeçalho
    novo_arquivo = not os.path.exists(arquivo_saida)

    # Se lowerbound ou gap forem None, vamos definir uma string padrão '---'
    if lowerbound is not None:
    
        if gap is not None:
           gap_str = gap
        else:
            gap_str = calcula_gap(lowerbound, objetivo)
            
        lowerbound_str = lowerbound
    
    else:
        gap_str="---"
        lowerbound_str = "---"

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
                 f"{objetivo:.4f}\t"
                 f"{lowerbound_str}\t"
                 f"{gap_str}\t"
                 f"{runtime:.4f}\t"
                 f"{constraints_str}\t"
                 f"{variables_str}\t"
                 f"{parameters}\n")
        f.write(linha)


#
# Gera grafico de Gantt com o resultado informado
#
def gantt_chart(M,N,N0,X,C,p,mostra,nome,instancia):

    # Criar a figura
    fig, ax = plt.subplots(figsize=(10, 5))

    # Cores para os jobs
    colors = plt.cm.get_cmap("tab10", len(N))

    # Resultados da resolução (substituir pelos valores obtidos do solver)
    C_values = { (i, j): value(C[i, j]) if hasattr(C[i, j], 'varValue') else C[i, j] for (i, j) in C }  # Pegamos o valor numérico

    # Plotar os retângulos no gráfico
    for i in M:
        for j in N:
            for k in N0:
                if j != k:
                    if (i,k,j) in X.keys():
                        if X[i,k,j] > 0.5:
                            #print(f'Job {k} precede {j} na máquina {i}')
                            # Tempo de início do job
                            start_time = C_values[i, j] - p[i, j]
                            ax.barh(y=i, width=p[i, j], left=start_time, height=0.4, color=colors(j-1), edgecolor='black', label=f'Job {j}' if i == 1 else "")

                            # Adicionar labels
                            ax.text(start_time + p[i, j]/2, i, f'J{j}', ha='center', va='center', color='white', fontsize=10, fontweight='bold')

    # Configurações do gráfico
    ax.set_yticks(M)
    ax.set_yticklabels([f'Máquina {i}' for i in M])
    ax.set_xlabel("Tempo")
    ax.set_title(instancia)

    ax.set_xticks(np.arange(0, max(C_values.values()) + 2, 1))  # Marcas de 1 em 1 no eixo x
    ax.grid(axis='x', linestyle="--", alpha=0.7)  # Ativar grid no eixo x
    plt.setp(ax.get_xticklabels(), rotation=90, fontsize=6)

    # Evitar repetição de labels
    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))

    # Mostrar o gráfico
    plt.savefig(nome, dpi=300, bbox_inches='tight')
    if(mostra==1):
        plt.show()

