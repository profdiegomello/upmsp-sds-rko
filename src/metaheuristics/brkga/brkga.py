import random
import time

# O import de 'threading' foi removido, pois não é mais necessário.

estado=0
saida=0

TEMPO_LIMITE=-1
GERACAO_FINAL=1

def encode(dados, n_individuos, decoder):
    populacao=[]
    if decoder == "n":
        for i in range(n_individuos):
            individuo=[]
            for j in dados["N"]:
                individuo.append(random.random())
            populacao.append(individuo)
    elif decoder == "2n" or decoder == "2n*":
        for i in range(n_individuos):
            individuo=[]
            for j in range(0, 2*len(dados["N"]), 1):
                individuo.append(random.random())
            populacao.append(individuo)
    elif decoder == "ect":
        for i in range(n_individuos):
            individuo=[]
            for j in range(0, len(dados["N"]), 1):
                individuo.append(random.random())
            populacao.append(individuo)
    elif decoder == "incremental":
        for i in range(n_individuos):
            individuo=[]
            for j in range(0, len(dados["N"]), 1):
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
    
def decode_individuo(individuo, indice, n_populacao, dados, decoder):
    qtd_maquinas = len(dados["M"])
    copia = list(individuo)
    range_step = 1 / qtd_maquinas
    n_jobs = len(dados["N"])

    if decoder == "n":
        # Ordena os jobs por valor da chave (menor valor = maior prioridade)
        jobs_ordenados = sorted(range(1, n_jobs + 1), key=lambda j: copia[j - 1])

        maquinas_jobs = {m: [] for m in dados["M"]}
        tempo_termino_maquinas = {m: 0 for m in dados["M"]}
        ultimo_job_maquina = {m: 0 for m in dados["M"]}  # Começa com dummy job 0

        for job in jobs_ordenados:
            melhor_maquina = None
            menor_tempo_termino = float('inf')

            for maquina in dados["M"]:
                setup_time = dados["S"].get((maquina, ultimo_job_maquina[maquina], job), 0)
                processing_time = dados["p"].get((maquina, job), float('inf'))

                completion_time = tempo_termino_maquinas[maquina] + setup_time + processing_time

                if completion_time < menor_tempo_termino:
                    menor_tempo_termino = completion_time
                    melhor_maquina = maquina

            # Aloca job na melhor máquina encontrada
            if melhor_maquina is not None:
                maquinas_jobs[melhor_maquina].append(job)
                tempo_termino_maquinas[melhor_maquina] = menor_tempo_termino
                ultimo_job_maquina[melhor_maquina] = job

    elif decoder == "2n":
        # Inicializa as máquinas com listas vazias
        maquinas_jobs = {m: [] for m in range(1, qtd_maquinas + 1)}

        # Parte 1: alocação de jobs para máquinas
        alocacao = copia[:n_jobs]
        ordem = copia[n_jobs:]  # Parte 2: ordem dos jobs

        for i in range(n_jobs):
            job_id = i + 1
            valor_aloc = alocacao[i]
            maquina = int(valor_aloc / range_step) + 1
            if maquina > qtd_maquinas:
                maquina = qtd_maquinas
            maquinas_jobs[maquina].append((ordem[i], job_id))  # ordem define prioridade

        # Parte 2: ordenar jobs dentro de cada máquina com base nos valores da segunda metade
        for m in maquinas_jobs:
            maquinas_jobs[m].sort()  # Ordena por valor da prioridade
            maquinas_jobs[m] = [job for _, job in maquinas_jobs[m]]

    elif decoder == "2n*":
        maquinas_jobs = {m: [] for m in range(1, qtd_maquinas + 1)}
        idx_ordem = len(dados["N"])

        # Parte 1: alocação dos jobs para máquinas
        for i in range(len(dados["N"])):
            valor = copia[i]
            maquina = int(valor / range_step) + 1
            if maquina > qtd_maquinas:
                maquina = qtd_maquinas
            job_id = i + 1
            maquinas_jobs[maquina].append(job_id)

        # Parte 2: ordena os jobs dentro de cada máquina com base na prioridade
        prioridade = copia[idx_ordem:]
        prioridades_jobs = {i + 1: prioridade[i] for i in range(len(prioridade))}

        for m in maquinas_jobs:
            maquinas_jobs[m] = sorted(maquinas_jobs[m], key=lambda j: prioridades_jobs[j])

    elif decoder == "ect":
        
        # Decoder 4: Ordenação por chave + Alocação por Earliest Completion Time
        jobs_ordenados = sorted(range(1, n_jobs + 1), key=lambda j: copia[j - 1])

        maquinas_jobs = {m: [] for m in dados["M"]}
        tempo_termino_maquinas = {m: 0 for m in dados["M"]}
        ultimo_job_maquina = {m: 0 for m in dados["M"]} # Dummy job 0

        for job in jobs_ordenados:
            melhor_maquina = None
            menor_tempo_termino = float('inf')
            
            for maquina in dados["M"]:
                setup_time = dados["S"].get((maquina, ultimo_job_maquina[maquina], job), 0)
                
                processing_time = dados["p"].get((maquina, job), float('inf')) 
                
                completion_time = tempo_termino_maquinas[maquina] + setup_time + processing_time

                if completion_time < menor_tempo_termino:
                    menor_tempo_termino = completion_time
                    melhor_maquina = maquina
            
            # Garante que uma máquina foi encontrada (caso não haja jobs válidos)
            if melhor_maquina is not None:
                maquinas_jobs[melhor_maquina].append(job)
                tempo_termino_maquinas[melhor_maquina] = menor_tempo_termino
                ultimo_job_maquina[melhor_maquina] = job
            
    elif decoder == "incremental":
        # Decoder 5: Ordenação por chave + Alocação por Custo Incremental no makespan

        # 1. Ordena os jobs com base nas chaves aleatórias
        jobs_ordenados = sorted(range(1, n_jobs + 1), key=lambda j: copia[j - 1])
        
        # 2. Inicializa o estado das máquinas
        maquinas_jobs = {m: [] for m in dados["M"]}
        
        # 3. Aloca cada job ordenado para a máquina que causa o menor aumento no makespan
        for job in jobs_ordenados:
            melhor_maquina = None
            menor_aumento_makespan = float('inf')
            
            # Avalia cada máquina para encontrar a melhor
            for maquina in dados["M"]:
                # Crie uma cópia temporária da máquina para o cálculo
                temp_maquinas = {m: list(maquinas_jobs[m]) for m in dados["M"]}
                temp_maquinas[maquina].append(job)
                
                # Calcule o makespan para essa configuração temporária
                makespan_temp = 0
                for m_temp in dados["M"]:
                    tempo_maquina = 0
                    anterior = 0
                    for j_temp in temp_maquinas[m_temp]:
                        tempo_maquina += dados["S"].get((m_temp, anterior, j_temp), 0)
                        tempo_maquina += dados["p"][(m_temp, j_temp)]
                        anterior = j_temp
                    if tempo_maquina > makespan_temp:
                        makespan_temp = tempo_maquina
                
                # Calcule o makespan da configuração atual (antes de alocar o job)
                makespan_atual = 0
                for m_atual in dados["M"]:
                    tempo_maquina_atual = 0
                    anterior = 0
                    for j_atual in maquinas_jobs[m_atual]:
                        tempo_maquina_atual += dados["S"].get((m_atual, anterior, j_atual), 0)
                        tempo_maquina_atual += dados["p"][(m_atual, j_atual)]
                        anterior = j_atual
                    if tempo_maquina_atual > makespan_atual:
                        makespan_atual = tempo_maquina_atual

                # Custo incremental = novo makespan - makespan atual
                aumento_makespan = makespan_temp - makespan_atual
                
                if aumento_makespan < menor_aumento_makespan:
                    menor_aumento_makespan = aumento_makespan
                    melhor_maquina = maquina

            # Aloca o job na melhor máquina
            maquinas_jobs[melhor_maquina].append(job)
            
    # Armazena o resultado decodificado
    n_populacao[indice] = maquinas_jobs

# --- ALTERAÇÃO 1: Função 'decode' agora é sequencial ---
def decode(dados, populacao, decoder):
    n_populacao = [None] * len(populacao)
    # O laço agora chama a função diretamente, uma por uma.
    for i, individuo in enumerate(populacao):
        decode_individuo(individuo, i, n_populacao, dados, decoder)
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
    makespan = max(tempo_maquinas.values()) if tempo_maquinas else 0
    results[indice] = makespan

# --- ALTERAÇÃO 2: Função 'fitness' agora é sequencial ---
def fitness(dados, n_populacao, populacao):
    results = [None] * len(n_populacao)
    # O laço agora chama a função diretamente, uma por uma.
    for i, individuo in enumerate(n_populacao):
        fitness_individuo(dados, individuo, i, results)
    
    # A lógica de ordenação permanece a mesma
    combinados = sorted(zip(results, populacao, n_populacao), key=lambda par: par[0])
    resultados_ordenados, populacao_ordenada, n_populacao_ordenada = zip(*combinados)
    return list(populacao_ordenada), list(resultados_ordenados), list(n_populacao_ordenada)

def crossover_individuo(dados, individuo, indice, populacao, i_elite, chance_cross):
    tamanho_gene = int(len(individuo))
    indv = list(individuo)
    for i in range(tamanho_gene):
        if random.random() < chance_cross:
            indv[i] = i_elite[i]
    populacao[indice] = indv
    return

def mutation_individuo(dados, indice, populacao, indiv):
    individuo = []
    for i in range(len(indiv)):
        individuo.append(random.random())
    populacao[indice] = individuo

# --- ALTERAÇÃO 3: Função 'gera_nova_populacao' agora é sequencial ---
def gera_nova_populacao(dados, populacao_f, percentual_elite, percentual_mutados, chance_cross):
    p_elite = int(len(populacao_f) * percentual_elite)
    # Índice a partir do qual a mutação começa
    p_inicio_mutacao = int(len(populacao_f) * (1 - percentual_mutados))
    
    populacao = [None] * len(populacao_f)

    for i in range(len(populacao_f)):
        # Elitismo: os melhores indivíduos são copiados diretamente
        if i < p_elite:
            populacao[i] = populacao_f[i]
        # Mutação: os piores indivíduos são substituídos por novos aleatórios
        elif i >= p_inicio_mutacao:
            mutation_individuo(dados, i, populacao, populacao_f[i])
        # Crossover: o restante da população cruza com a elite
        else:
            sorteio = random.randint(0, p_elite - 1 if p_elite > 0 else 0)
            crossover_individuo(dados, populacao_f[i], i, populacao, populacao_f[sorteio], chance_cross)
            
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

def escreve_final(populacao_f, populacao_m_f, results, t_inicio, arq_saida, saida, geracao, dados):
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
def solve(dados, nome_instancia, tempo_limite, n_individuos, n_geracoes, percentual_elite, percentual_mutados, chance_cross, parcial, decoder):

    global estado
    global saida
    
    # Marca o tempo de inicio
    t_inicio=time.time() 

    # Cria a populacao inicial
    populacao = encode(dados, n_individuos, decoder) #Codifica dados lidos
    
    if parcial==1:
        escrita_inicial(t_inicio, nome_instancia, tempo_limite, n_geracoes, n_individuos, parcial)
    
    # Inicializa variáveis para guardar a melhor solução encontrada
    populacao_f, results, populacao_m_f = [], [], []

    geracao=1
    while(verifica_tempo_expirado(t_inicio, tempo_limite)):
    
        if estado==1:
            n_populacao=decode(dados, populacao, decoder)
        
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
    
    # Se a última ação foi gerar uma nova população, precisamos avaliar
    # e ordenar uma última vez para garantir que temos a melhor solução.
    if populacao_f is None or not populacao_f:
        n_populacao = decode(dados, populacao, decoder)
        populacao_f, results, populacao_m_f = fitness(dados, n_populacao, populacao)

    if(saida==TEMPO_LIMITE):
        status_str="TEMPO_LIMITE"
    else:
        status_str="ALL_GEN"

    # Converte a solucao do BRKGA em 'variaveis' C e X  
    C, X = calcular_C_e_X(populacao_m_f[0], dados) # populacao_m_f[0] é a melhor solução
                
    # Escreve o resultado final
    escreve_final(populacao_f, populacao_m_f, results, t_inicio, "saidabrkga.txt", saida, geracao, dados)
    
    # retorna a solucao
    return results, tempo_f, status_str, C, X