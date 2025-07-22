
import os
import random
import threading
import time
from pulp import value

estado=0
saida=0

TEMPO_LIMITE=-1
GERACAO_FINAL=1

def encode(dados, n_individuos):
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
    
def decode_individuo(individuo, indice, n_populacao, dados):
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
    
def decode(dados, populacao):
    threads=[]
    n_populacao=[None] * len(populacao)
    for i, individuo in enumerate(populacao):
        thread=threading.Thread(target=decode_individuo, args=(individuo, i, n_populacao, dados))
        threads.append(thread)
        thread.start()
    for thread in threads:
        thread.join()
    return n_populacao

def fitness_individuo(dados, individuo, indice, results):
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

def fitness(dados, n_populacao, populacao):
    threads=[]
    results=[None] * len(n_populacao)
    for i, individuo in enumerate(n_populacao):
        thread=threading.Thread(target=fitness_individuo, args=(dados, individuo, i, results))
        threads.append(thread)
        thread.start()
    for thread in threads:
        thread.join()
    combinados = sorted(zip(results, populacao, n_populacao), key=lambda par: par[0])
    resultados_ordenados, populacao_ordenada, n_populacao_ordenada = zip(*combinados)
    return list(populacao_ordenada), list(resultados_ordenados), list(n_populacao_ordenada)

def crossover_individuo(dados, individuo, indice, populacao, i_elite, chance_cross):
    tamanho_gene=int(len(dados["N"]))
    indv=list(individuo)
    for i in range(0, tamanho_gene, 1):
        if random.random() < chance_cross:
            indv[i]=i_elite[i]
    populacao[indice]=indv
    return

def mutation_individuo(dados, indice, populacao):
    individuo=[]
    for i in range(0, len(dados["N"]),1):
        individuo.append(random.random())
    populacao[indice]=individuo

def gera_nova_populacao(dados, populacao_f, percentual_elite, percentual_mutados, chance_cross):
    p_elite=int(len(populacao_f)*percentual_elite)
    p_mutados=int(len(populacao_f))-int(len(populacao_f)*percentual_mutados)
    threads=[]
    populacao=[None] * (len(populacao_f))
    for i in range(0, len(populacao_f), 1):
        if(i>p_mutados):
            thread=threading.Thread(target=mutation_individuo, args=(dados, i, populacao))
            threads.append(thread)
            thread.start()
        elif(i>p_elite):
            sorteio=random.randint(0, p_elite)
            thread=threading.Thread(target=crossover_individuo, args=(dados, populacao_f[i], i, populacao, populacao_f[sorteio], chance_cross))
            threads.append(thread)
            thread.start()
        else:
            populacao[i]=populacao_f[i]
    for thread in threads:
        thread.join()
    return populacao

def escrita_inicial(t_inicio, nome_instancia, tempo_limite, n_geracoes, n_individuos, parcial):
    with open("saidabrkga.txt", 'w') as f:
        # Cabeçalho com informações da execução
        f.write(f"# Execução BRKGA para UPMS-ST\n")
        f.write(f"# Data/Hora Início: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(t_inicio))}\n")
        f.write(f"# Instância: {nome_instancia}\n")
        f.write(f"# Tempo Limite: {tempo_limite} segundos\n")
        f.write(f"# Gerações Máximas: {n_geracoes}\n")
        f.write(f"# Tamanho da População: {n_individuos}\n")
        f.write(f"# Resultados Parciais: {'Sim' if parcial == 1 else 'Não'}\n\n")

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


#
# Executa o laco principal que faz o BRKGA evoluir uma populacao até cumprir as condicoes de saida
#
def solve(dados, nome_instancia, tempo_limite, n_individuos, n_geracoes, percentual_elite, percentual_mutados, chance_cross, parcial):

    global estado
    global saida
    
    # Marca o tempo de inicio
    t_inicio=time.time() 

    # Cria a populacao inicial
    populacao = encode(dados, n_individuos) #Codifica dados lidos
    
    if parcial==1:
        escrita_inicial(t_inicio, nome_instancia, tempo_limite, n_geracoes, n_individuos, parcial)

    geracao=1
    while(verifica_tempo_expirado(t_inicio, tempo_limite)):
    
        if estado==1:
            n_populacao=decode(dados, populacao)
        
        elif estado==2:
            populacao_f, results, populacao_m_f=fitness(dados, n_populacao, populacao)
        
        elif estado==3:
            if(parcial==1):
                escreve_parcial(results, geracao, t_inicio, "saidabrkga.txt")        
        
        elif estado==4:
            populacao=gera_nova_populacao(dados, populacao_f, percentual_elite, percentual_mutados, chance_cross)
        
        elif estado==5:
            if(geracao==n_geracoes):
                saida=GERACAO_FINAL
                break
            else:
                geracao+=1
                estado=0
           
    # Calcula o runtime     
    tempo_f = time.time() - t_inicio
    
    if(saida==TEMPO_LIMITE):
        status_str="TEMPO_LIMITE"
    else:
        status_str="ALL_GEN"
      
    # Converte a solucao do BRKGA em 'variaveis' C e X  
    C, X=calcular_C_e_X(populacao_m_f[0], dados)
                
    # retorna a solucao
    return results, tempo_f, status_str, C, X              

