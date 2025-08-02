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
# Constroi grafico de Gantt
#
def gantt_chart(M, N, N0, p, s, X, C, arq_gantt, instancia, makespan, str_metodo):
    """
    Gera um gráfico de Gantt a partir de dicionários genéricos de solução (X e C).

    Args:
        M (list): Lista de máquinas.
        N (list): Lista de jobs.
        N0 (list): Lista de jobs incluindo o job dummy 0.
        p (dict): Dicionário com os tempos de processamento.
        s (dict): Dicionário com os tempos de setup (não usado diretamente na plotagem,
                  pois está embutido em C, mas mantido por consistência).
        X (dict): Dicionário de sequenciamento no formato {(i, k, j): 1}.
        C (dict): Dicionário de tempo de término no formato {(i, j): tempo}.
        mostra (int): 1 para exibir o gráfico, 0 para apenas salvar.
        arq_gantt (str): Nome do arquivo para salvar o gráfico.
        instancia (str): Nome da instância para o título do gráfico.
    """
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Cores para os jobs
    # Usando um mapa de cores com base no número total de jobs
    colors = plt.cm.get_cmap("tab20", len(N)) 

    max_completion_time = 0

    # Iterar sobre as máquinas e jobs para desenhar as barras
    for i in M:
        for j in N:
            # Verifica se o job j está alocado em alguma sequência na máquina i
            # Isso é verdade se existir alguma chave em X da forma (i, k, j)
            is_job_on_machine = any(X.get((i, k, j), 0) > 0.5 for k in N0)
            
            if is_job_on_machine:
                completion_time = C.get((i, j), 0)
                processing_time = p.get((i, j), 0)
                start_time = completion_time - processing_time

                # Atualiza o tempo máximo de conclusão para ajustar o eixo x
                if completion_time > max_completion_time:
                    max_completion_time = completion_time

                # Desenha a barra do job
                ax.barh(y=f'Máquina {i}', width=processing_time, left=start_time, height=0.5, 
                        color=colors(j - 1), edgecolor='black')
                
                # Adiciona o nome do job no centro da barra
                ax.text(start_time + processing_time / 2, f'Máquina {i}', f'J{j}', 
                        ha='center', va='center', color='white', fontsize=9, fontweight='bold')

    # Configurações do gráfico
    ax.set_xlabel("Tempo")
    ax.set_ylabel("Máquinas")
    ax.set_title(f"Makespan: {round(makespan,4)} ({str_metodo}) at {instancia}")
    
    # Ajustar o eixo Y para inverter a ordem (Máquina 1 no topo)
    ax.invert_yaxis()
    
    ax.set_xticks(np.arange(0, max_completion_time + 2, max(1, int((max_completion_time+2)/30))))
    plt.setp(ax.get_xticklabels(), rotation=90, fontsize=8)

    ax.grid(axis='x', linestyle='--', alpha=0.7)
    plt.tight_layout()

    # Salvar o gráfico
    plt.savefig(f'{arq_gantt}-{str_metodo}', dpi=300, bbox_inches='tight')

    plt.close(fig)


#
# Gera grafico de Gantt com o resultado informado
#
def gantt_chart_2(M,N,N0,X,C,p,mostra,nome,instancia):

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

