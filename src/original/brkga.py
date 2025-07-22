import argparse
import time
import os
import random
import threading
import matplotlib.pyplot as plt
import numpy as np
from pulp import value

dados={
    #Definição dos conjuntos
    "M":[], #Máquinas
    "N":[], #Jobs
    "N0":[], #Jobs + dummy 0
    #Constantes
    "V":0, #Constante grande
    #Parâmetros
    "p":{}, #p[ij]: Tempo de processamento do job j na máquina i
    "S":{} #S[i,j,k]: Tempo de setup do job j=>k na máquina i
}

estado=0
saida=0

TEMPO_LIMITE=-1
GERACAO_FINAL=1

#Lê de acordo com string variável

def le_formato_variavel(diretorio, formato):
    global dados

    ordem = formato.split(";")

    with open(diretorio, "r") as f:
        linhas = f.read().splitlines()

    linha_atual = 0

    for campo in ordem:
        if campo == "MNNO":
            # Aqui invertemos M e N, pois o formato do arquivo é: N M N0
            N, M, N0 = map(int, linhas[linha_atual].split())
            dados["M"] = list(range(1, M + 1))  # máquinas: 1..M
            dados["N"] = list(range(1, N + 1))  # jobs: 1..N
            dados["N0"] = [0] + dados["N"]      # inclui dummy job 0
            linha_atual += 1

        elif campo == "V":
            V = int(linhas[linha_atual])
            dados["V"] = V
            linha_atual += 1

        elif campo == "p":
            # Leitura dos tempos de processamento da tarefa j na máquina i
            N_ids = dados["N"]
            M_ids = dados["M"]
            p = {}
            for j in N_ids:
                partes = list(map(int, linhas[linha_atual].split()))
                for i in range(0, len(partes), 2):
                    maquina = partes[i] + 1  # índice 1-based
                    tempo = partes[i + 1]
                    p[(maquina, j)] = tempo
                linha_atual += 1
            dados["p"] = p

        elif campo == "S":
            if linhas[linha_atual].strip() != "SSD":
                raise ValueError("Esperado marcador 'SSD' não encontrado")
            linha_atual += 1

            S = {}
            M_ids = dados["M"]
            N_ids = dados["N"]

            for m_index in range(len(M_ids)):
                maquina = M_ids[m_index]

                marcador_maquina = linhas[linha_atual].strip()
                if not marcador_maquina.startswith("M"):
                    raise ValueError(f"Esperado marcador de máquina, obtido '{marcador_maquina}'")
                linha_atual += 1

                for i_index, j in enumerate(N_ids):  # para cada linha da matriz (job j)
                    valores = list(map(int, linhas[linha_atual].split()))
                    for k_index, k in enumerate(N_ids):  # para cada coluna da matriz (job k)
                        S[(maquina, j, k)] = valores[k_index]
                    linha_atual += 1
            dados["S"] = S

def le_arquivo(args):
    if not(os.path.exists(args.nome_instancia)):
        print(f"O arquivo <{args.nome_instancia}> não existe!")
        exit()
    else:
        le_formato_variavel(args.nome_instancia, "MNNO;V;p;S")
        return
    
def encode(n_individuos):
    populacao=[]
    for i in range(n_individuos):
        individuo=[]
        for j in dados["N"]:
            individuo.append(random.random())
        populacao.append(individuo)
    return populacao

def verifica_tempo_expirado(inicio, limite):
    global saida
    global estado
    duracao=time.time()-inicio
    if(limite==-1):
        estado+=1
        return True
    elif(duracao>=limite):
        saida=TEMPO_LIMITE
        return False
    else:
        estado+=1
        return True
    
def decode_individuo(individuo, indice, n_populacao):
    qtd_maquinas = len(dados["M"])
    copia = list(individuo)
    range_step = 1 / qtd_maquinas

    # Inicializa as máquinas com listas vazias
    maquinas_jobs = {m: [] for m in range(1, qtd_maquinas + 1)}

    # Atribui cada job (indexado de 1) a uma máquina com base no valor
    for i, valor in enumerate(copia):
        maquina = int(valor / range_step) + 1
        if maquina > qtd_maquinas:
            maquina = qtd_maquinas  # Proteção contra estouro
        job_id = i + 1  # Corrigido para índice começando de 1
        maquinas_jobs[maquina].append((valor, job_id))

    # Ordena os jobs em cada máquina por prioridade (valor)
    for m in maquinas_jobs:
        maquinas_jobs[m].sort()  # Ordena por valor
        maquinas_jobs[m] = [job for _, job in maquinas_jobs[m]]  # Retém apenas o ID do job

    n_populacao[indice] = maquinas_jobs
    
def decode(populacao):
    threads=[]
    n_populacao=[None] * len(populacao)
    for i, individuo in enumerate(populacao):
        thread=threading.Thread(target=decode_individuo, args=(individuo, i, n_populacao))
        threads.append(thread)
        thread.start()
    for thread in threads:
        thread.join()
    return n_populacao

def fitness_individuo(individuo, indice, results):
    tempo_maquinas = {m: 0 for m in dados["M"]}

    # Para cada máquina e sua lista de jobs ordenados
    for m in dados["M"]:
        job_list = individuo.get(m, [])
        tempo_total = 0
        if not job_list:
            continue

        anterior = 0  # dummy job
        for atual in job_list:
            tempo_total += dados["S"].get((m, anterior, atual), 0)
            tempo_total += dados["p"][(m, atual)]
            anterior = atual

        tempo_maquinas[m] = tempo_total

    # O makespan é o tempo da máquina mais carregada
    makespan = max(tempo_maquinas.values())
    results[indice] = makespan

def fitness(n_populacao, populacao):
    threads=[]
    results=[None] * len(n_populacao)
    for i, individuo in enumerate(n_populacao):
        thread=threading.Thread(target=fitness_individuo, args=(individuo, i, results))
        threads.append(thread)
        thread.start()
    for thread in threads:
        thread.join()
    combinados = sorted(zip(results, populacao, n_populacao), key=lambda par: par[0])
    resultados_ordenados, populacao_ordenada, n_populacao_ordenada = zip(*combinados)
    return list(populacao_ordenada), list(resultados_ordenados), list(n_populacao_ordenada)

def crossover_individuo(individuo, indice, populacao, i_elite):
    tamanho_gene=int(len(dados["N"]))
    indv=list(individuo)
    for i in range(0, tamanho_gene, 1):
        if random.random()<args.chance_cross:
            indv[i]=i_elite[i]
    populacao[indice]=indv
    return

def mutation_individuo(indice, populacao):
    individuo=[]
    for i in range(0, len(dados["N"]),1):
        individuo.append(random.random())
    populacao[indice]=individuo

def gera_nova_populacao(populacao_f):
    p_elite=int(len(populacao_f)*args.percentual_elite)
    p_mutados=int(len(populacao_f))-int(len(populacao_f)*args.percentual_mutados)
    threads=[]
    populacao=[None] * (len(populacao_f))
    for i in range(0, len(populacao_f), 1):
        if(i>p_mutados):
            thread=threading.Thread(target=mutation_individuo, args=(i, populacao))
            threads.append(thread)
            thread.start()
        elif(i>p_elite):
            sorteio=random.randint(0, p_elite)
            thread=threading.Thread(target=crossover_individuo, args=(populacao_f[i], i, populacao, populacao_f[sorteio]))
            threads.append(thread)
            thread.start()
        else:
            populacao[i]=populacao_f[i]
    for thread in threads:
        thread.join()
    return populacao

def escrita_inicial(t_inicio, args):
    with open("saidabrkga.txt", 'w') as f:
        # Cabeçalho com informações da execução
        f.write(f"# Execução BRKGA para UPMS-ST\n")
        f.write(f"# Data/Hora Início: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(t_inicio))}\n")
        f.write(f"# Instância: {args.nome_instancia}\n")
        f.write(f"# Tempo Limite: {args.tempo_limite} segundos\n")
        f.write(f"# Gerações Máximas: {args.n_geracoes}\n")
        f.write(f"# Tamanho da População: {args.n_individuos}\n")
        f.write(f"# Resultados Parciais: {'Sim' if args.parcial == 1 else 'Não'}\n\n")

def escreve_parcial(results, geracao, t_inicio, arq_saida):
    tempo_decorrido = time.time() - t_inicio
    melhor_makespan = results[0]  # O primeiro é o melhor (população está ordenada)
    
    with open(arq_saida, 'a') as f:  # 'a' para append (adicionar ao final do arquivo)
        # Escreve a linha com os dados da geração atual
        f.write(f"{geracao};{tempo_decorrido:.2f};{melhor_makespan}\n")
        
        # Opcional: para depuração, pode-se incluir mais detalhes
        # f.write(f"# Melhor solução da geração {geracao}: {populacao_f[0]}\n")

def escreve_final(populacao_f, populacao_m_f, results, t_inicio, arq_saida, saida, geracao):
    tempo_total = time.time() - t_inicio
    melhor_makespan = results[0]
    melhor_individuo = populacao_f[0]
    melhor_fenotipo = populacao_m_f[0]  # Novo formato: máquina → lista de jobs ordenados

    with open("saidabrkga.txt", 'a') as f:
        f.write("\n# RESULTADOS FINAIS\n")
        f.write(f"# Tempo total de execução: {tempo_total:.2f} segundos\n")
        f.write(f"# Melhor makespan encontrado: {melhor_makespan}\n")
        f.write(f"# Condição de saída: {'TIME_OUT' if saida == TEMPO_LIMITE else 'ALL_GEN'}\n")
        f.write(f"# Última geração gerada: {geracao}\n")

        f.write("# Alocação meta heurística de jobs por máquina:\n")
        f.write("Máquina\tJobs\n")
        for maquina in sorted(melhor_fenotipo.keys()):
            f.write(f"{maquina}\t{melhor_fenotipo[maquina]}\n")

        f.write("\n# Sequência de execução por máquina:\n")
        for maquina in sorted(melhor_fenotipo.keys()):
            jobs = melhor_fenotipo[maquina]
            f.write(f"Máquina {maquina}: {jobs}\n")
            tempo_maquina = 0
            anterior = 0  # dummy job inicial
            for job in jobs:
                tempo_maquina += dados["S"].get((maquina, anterior, job), 0)
                tempo_maquina += dados["p"][(maquina, job)]
                anterior = job
            f.write(f"# Tempo total máquina {maquina}: {tempo_maquina}\n")

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
    status: int
):

   # Registra os resultados no arquivo passado, usando tabulação como separador.
   # Caso lowerbound ou gap sejam None, registra como '---'.

    # Verifica se o arquivo já existe para saber se deve escrever o cabeçalho
    novo_arquivo = not os.path.exists(arquivo_saida)

    # Se lowerbound ou gap forem None, vamos definir uma string padrão '---'
    #if(lowerbound!=None):
    if lowerbound is not None:
        gap_str=((lowerbound-objetivo)/objetivo)*100
        lowerbound_str=lowerbound
    else:
        gap_str="---"
        lowerbound_str = "---"

    if(status==TEMPO_LIMITE):
        status="TEMPO_LIMITE"
    else:
        status="ALL_GEN"

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
                 f"{constraints}\t"
                 f"{variables}\t"
                 f"{parameters}\n")
        f.write(linha)

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

def calcular_C_e_X(individuo, dados):
    C = {}
    X = {}

    for i in dados["M"]:  # Para cada máquina
        tempo = 0
        anterior = 0  # Dummy job

        for j in individuo.get(i, []):
            setup = dados["S"].get((i, anterior, j), 0)
            proc = dados["p"][(i, j)]

            tempo += setup + proc
            C[(i, j)] = tempo

            # Marcar precedência
            X[(i, anterior, j)] = 1

            anterior = j

    return C, X


if __name__ == "__main__":
     #Recebe argumentos do terminal e os armazena em args
    parser=argparse.ArgumentParser(description="BRKGA para UPMS-ST")
    parser.add_argument("--nome_instancia", type=str, default=None, help="Nome da instância")
    parser.add_argument("--arq_saida", type=str, default=None, help="Arquivo de saída dos resultados")
    parser.add_argument("--gantt", type=str, default=None, help="Saída grafico de Gantt")
    parser.add_argument("--tempo_limite", type=int, default=-1, help="Limite de tempo em segundos")
    parser.add_argument("--n_geracoes", type=int, default=0, help="Número de gerações a ser computada")
    parser.add_argument("--n_individuos", type=int, default=0, help="Número de individuos a ser gerado")
    parser.add_argument("--percentual_elite", type=float, default=0, help="Número percentual de 1 a 0 de indivíduos da elite")
    parser.add_argument("--percentual_mutados", type=float, default=0, help="Número percentual de 1 a 0 de indivíduos mutados")
    parser.add_argument("--chance_cross", type=float, default=0, help="Número percentual de 1 a 0 de genes fazerem crossover")
    parser.add_argument("--lowerbound", type=float, default=None, help="Número de lowerbound do Gurobi para calcular o gap")
    parser.add_argument("--mostra_gantt", type=int, default=0, help="Deseja ver o grafico de gantt (0-Não 1-Sim)")
    parser.add_argument("--parcial", action="store_const", const=1, default=0, help="Deseja resultado parcial (0-Não 1-Sim)")
    args = parser.parse_args()
    le_arquivo(args) #Chama função de leitura
    populacao=encode(args.n_individuos) #Codifica dados lidos
    t_inicio=time.time() #Define tempo de início a execução
    escrita_inicial(t_inicio, args)
    geracao=1
    while(verifica_tempo_expirado(t_inicio, args.tempo_limite)):
        if estado==1:
            n_populacao=decode(populacao)
        elif estado==2:
            populacao_f, results, populacao_m_f=fitness(n_populacao, populacao)
        elif estado==3:
            if(args.parcial==1):
                escreve_parcial(results, geracao, t_inicio, "saidabrkga.txt")
        elif estado==4:
            populacao=gera_nova_populacao(populacao_f)
        elif estado==5:
            if(geracao==args.n_geracoes):
                saida=GERACAO_FINAL
                break
            else:
                geracao+=1
                estado=0
    tempo_f=time.time() - t_inicio
    parametros=f"i-{args.n_individuos}|g-{args.n_geracoes}|pe-{args.percentual_elite}|pm-{args.percentual_mutados}|c-{args.chance_cross}"
    salvar_resultado(args.arq_saida, args.nome_instancia, "BRKGA", results[0], args.lowerbound, None, tempo_f, args.n_geracoes, args.n_individuos, parametros, len(dados["N"]), len(dados["M"]), saida)
    escreve_final(populacao_f, populacao_m_f, results, t_inicio, "saidabrkga.txt", saida, geracao)
    if(args.gantt!=None):
        C, X=calcular_C_e_X(populacao_m_f[0], dados)
        gantt_chart(dados["M"], dados["N"], dados["N0"], X, C, dados["p"], args.mostra_gantt, args.gantt, args.nome_instancia)

    #TODO:
    #-Corrigir entrada do argparse formato ->Ex01: -input 100 FEITO!
    #-Renomear crossover para geranovapopulacao() FEITO!
    #-Mudar separador do PARAMETERS FEITO!
    #Implementar Gantt
    #Corrigir LowerBound
        
