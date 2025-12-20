import os
import random
import time
import math
import pickle

'''
Função que calcula o custo total de uma solução de escalonamento.
Esse é o custo que queremos minimizar!

Args:
    escalonamento (dict): Dicionário representando a solução.
    dados_instancia (dict): Dicionário com os dados da instância.

Returns:
    float: Valor do makespan para a solução fornecida.
'''
def sa_calcular_custo(escalonamento: dict, dados_instancia: dict):

    M, p, S, = (
        dados_instancia.get("M", {}), dados_instancia.get("p", {}), dados_instancia.get("S", {})
    )

    # dicionario pro tempo de ocupação de cada maquina:
    tempo_maquina = {maquina: 0 for maquina in M}

    # loop q itera sobre cada par maquina-jobs:
    for maquina, sequencia in escalonamento.items():
        job_anterior = 0

        # para cada job da maquina:
        for job_atual in sequencia:
            # calcula o tempo de setup entre o job anterior e o atual:
            setup = S.get((maquina, job_anterior, job_atual), 0)
            proc = p.get((maquina, job_atual), float('inf'))

            tempo_maquina[maquina] += setup + proc
            job_anterior = job_atual

    # calcula o makespan:   
    makespan = max(tempo_maquina.values()) if tempo_maquina else 0

    return makespan


'''
Função que constrói uma solução inicial gulosa.
Os jobs sao ordenados de forma aleatória.
Cada job é alocado na máquina elegível que resulta em seu menor 
tempo de conclusão, considerando o estado atual das máquinas.

Args:
    dados_instancia (dict): Dicionário com os dados da instância.

Returns:
    dict: Um dicionário representando a solução de escalonamento inicial.
'''
def sa_construir_solucao(dados_instancia: dict):

    N, M, p, S, maq_elegiveis = (
        dados_instancia.get("N", []), dados_instancia.get("M", []), dados_instancia.get("p", {}), dados_instancia.get("S", {}),
        dados_instancia.get("maquinasElegiveis", {})
    )

    escalonamento = {maquina: [] for maquina in M}
    tempo_maquina = {maquina: 0 for maquina in M}
    ultimo_job = {maquina: 0 for maquina in M}

    # ordena jobs de forma aleatória:
    jobs = list(N)
    random.shuffle(jobs)

    # pra cada job da lista de jobs:
    for job in jobs:
        melhor_maquina = -1
        menor_custo_adicional = float('inf')

        # para cada máquina elegível para aquele job:
        for maquina in maq_elegiveis.get(job, M):
            job_anterior = ultimo_job[maquina]

            # calcula o custo adicional de processar o job na máquina atual:
            setup = S.get((maquina, job_anterior, job), 0)
            proc = p.get((maquina, job), float('inf'))
            custo_adicional = setup + proc

            # verifica se essa alocação da um tempo de conclusão melhor:
            if tempo_maquina[maquina] + custo_adicional < menor_custo_adicional:
                menor_custo_adicional = tempo_maquina[maquina] + custo_adicional
                melhor_maquina = maquina

        # se uma melhor maquina for encontrada:
        if melhor_maquina != -1:
            # aloca o job nela:
            escalonamento[melhor_maquina].append(job)
            tempo_maquina[melhor_maquina] = menor_custo_adicional
            ultimo_job[melhor_maquina] = job

    return escalonamento


'''
Função para encontrar a maquina crítica, ou seja, a que tem o maior tempo total de trabalho.

Args:
    escalonamento (dict): A solução de escalonamento atual.
    dados_instancia (dict): Dicionário com os dados da instância.

Returns: 
    Any | None: O ID da máquina crítica, ou None se o escalonamento for vazio.
'''
def encontrar_maquina_critica(escalonamento: dict, dados_instancia: dict):

    p, S = dados_instancia.get("p", {}), dados_instancia.get("S", {})

    # dicionario pro tempo de ocupação de cada máquina:
    tempo_maquina = {}

    # loop q itera sobre cada par de máquina-jobs:
    for maquina, sequencia in escalonamento.items():
        tempo_atual = 0
        job_anterior = 0

        # pra cada job da máquina:
        for job_atual in sequencia:

            # calcula o tempo de setup entre o job anterior e o atual:
            setup = S.get((maquina, job_anterior, job_atual), 0)
            proc = p.get((maquina, job_atual), float('inf'))

            tempo_atual += setup + proc
            job_anterior = job_atual

        tempo_maquina[maquina] = tempo_atual

    # retorna o id da maquina critica ou None:
    return max(tempo_maquina, key=tempo_maquina.get) if tempo_maquina else None


'''
Função que gera uma solução vizinha a partir da atual usando operadores de movimento.

Args: 
    escalonamento (dict): A solução de escalonamento atual.
    dados_instancia (dict): Dicionário com os dados da instância.
    p_bloco (float): Probabilidade de aplicar um movimento em bloco.
    max_tamanho_bloco (int): Tamanho máximo de um bloco de jobs.
    p_shift (float): Probabilidade de escolher um movimento do tipo 'Shift'.

Returns: 
    dict: Um novo dicionário de escalonamento representando a solução vizinha.
'''

def sa_gerar_vizinho(escalonamento: dict, dados_instancia: dict, p_bloco: float, max_tamanho_bloco: int, p_shift: float):

    # cria uma copia da solução atual:
    novo_escalonamento = pickle.loads(pickle.dumps(escalonamento, protocol=pickle.HIGHEST_PROTOCOL))

    M = dados_instancia["M"]
    maq_elegiveis = dados_instancia.get("maquinasElegiveis", {})

    # primeiro escolhemos a máquina mais sobrecarregada:
    maquina_critica = encontrar_maquina_critica(novo_escalonamento, dados_instancia)
    # se n houver maquina crítica, ou se ela nao tiver jobs, entao retorna a cópia sem modificações:
    if maquina_critica is None or not novo_escalonamento[maquina_critica]:
        return novo_escalonamento
    
    # aqui decide se vai fazer um movimento em bloco ou usar shift ou swap
    if random.random() < p_bloco:

        # agora decide entre block shift e block swap: 
        if random.random() < p_shift: # shift:

            seq_critica = novo_escalonamento[maquina_critica]

            if len(seq_critica) < 1: return novo_escalonamento    

            # pega um tamanho random de bloco que n seja maior que o tamanho definido:
            tamanho_bloco = random.randint(1, min(max_tamanho_bloco, len(seq_critica)))
            # pega uma posicao inicial random:
            idx_inicio = random.randint(0, len(seq_critica) - tamanho_bloco)
            # extrai os jobs do bloco:
            bloco = seq_critica[idx_inicio : idx_inicio + tamanho_bloco]
            # remove o bloco da posição original:
            del novo_escalonamento[maquina_critica][idx_inicio : idx_inicio + tamanho_bloco]
            # cria uma lista de todas as maquinas que o bloco pode ir: 
            destinos_possiveis = [m for m in M if m != maquina_critica and all(m in maq_elegiveis.get(j, M) for j in bloco)]

            if destinos_possiveis:
                # escolhe maquina random e escolhe uma posição random nessa maquina pra inserir o bloco: 
                m_destino = random.choice(destinos_possiveis)
                idx_insercao = random.randint(0, len(novo_escalonamento[m_destino]))
                novo_escalonamento[m_destino][idx_insercao:idx_insercao] = bloco
            else:
                novo_escalonamento[maquina_critica][idx_inicio:idx_inicio] = bloco

        else: # swap
            
            # acha todas as maquinas que nao estao vazias pra ser parceira de troca:
            maquinas_parceiras = [m for m in M if m != maquina_critica and len(novo_escalonamento[m])>0]
            if not maquinas_parceiras: return novo_escalonamento # n tem com quem trocar

            # escolhe uma maquina random pra ser parceira:   
            maq_parceira = random.choice(maquinas_parceiras)
            seq_critica = novo_escalonamento[maquina_critica]
            seq_parceira = novo_escalonamento[maq_parceira]

            # pega um tamanho random de bloco 1 que n seja maior que o tamanho definido:
            tamanho_bloco1 = random.randint(1, min(max_tamanho_bloco, len(seq_critica)))
            # pega uma posicao inicial random:
            idx1 = random.randint(0, len(seq_critica) - tamanho_bloco1)
            # extrai os jobs do bloco 1:
            bloco1 = seq_critica[idx1 : idx1 + tamanho_bloco1]

            # pega um tamanho random de bloco 2 que n seja maior que o tamanho definido:
            tamanho_bloco2 = random.randint(1, min(max_tamanho_bloco, len(seq_parceira)))
            # pega uma posicao inicial random:
            idx2 = random.randint(0, len(seq_parceira) - tamanho_bloco2)
            # extrai os jobs do bloco 2:
            bloco2 = seq_parceira[idx2 : idx2 + tamanho_bloco2]

            # verifica se os jobs dos blocos podem ser trocados:
            bloco1_elegivel = all(maq_parceira in maq_elegiveis.get(j, M) for j in bloco1)
            bloco2_elegivel = all(maq_parceira in maq_elegiveis.get(j, M) for j in bloco2)

            # se for elegivel: 
            if bloco1_elegivel and bloco2_elegivel:
                # reconstroi as listas de jobs trocando eles de lugar:
                nova_seq_critica = seq_critica[:idx1] + bloco2 + seq_critica[idx1 + tamanho_bloco1:]
                nova_seq_parceira = seq_parceira[:idx2] + bloco1 + seq_parceira[idx2 + tamanho_bloco2:]

                # atualiza o dicionario:
                novo_escalonamento[maquina_critica] = nova_seq_critica
                novo_escalonamento[maq_parceira] = nova_seq_parceira

    else:
        # escolhe um job random da máquina crítica:
        job_alvo = random.choice(novo_escalonamento[maquina_critica])

        # decide entre Shift ou Swap
        if random.random() < p_shift: # shift

            # remove o job da posição atual: 
            idx_origem = novo_escalonamento[maquina_critica].index(job_alvo)
            job_movido = novo_escalonamento[maquina_critica].pop(idx_origem)

            # cria uma lista de todas as maquinas que o job pode ir: 
            destinos_possiveis = [m for m in M if m != maquina_critica and m in maq_elegiveis.get(job_movido, M)]
            # se tiver maquinas:
            if destinos_possiveis:
                # escolhe um destino random e coloca o job nessa posição:
                m_destino = random.choice(destinos_possiveis)
                idx_destino = random.randint(0, len(novo_escalonamento[m_destino]))
                novo_escalonamento[m_destino].insert(idx_destino, job_movido)
            else:
                novo_escalonamento[maquina_critica].insert(idx_origem, job_movido)       

        else: # swap

            # cria uma lista de maquinas parceiras: 
            parceiras = [m for m in M if m != maquina_critica and novo_escalonamento[m]]
            # se tiver parceiras:
            if parceiras:
                # seleciona uma maquina parceira random:
                m_parceira = random.choice(parceiras)
                # seleciona um job random da maquina parceira pra trocar de lugar:
                job_parceiro = random.choice(novo_escalonamento[m_parceira])

                # se as maquinas parceiras forem elegíveis para os jobs a serem trocados: 
                if m_parceira in maq_elegiveis.get(job_alvo, M) and maquina_critica in maq_elegiveis.get(job_parceiro, M):
                    
                    # troca os jobs de maquina:
                    idx_alvo = novo_escalonamento[maquina_critica].index(job_alvo)
                    idx_parceiro = novo_escalonamento[m_parceira].index(job_parceiro)
                    novo_escalonamento[maquina_critica][idx_alvo], novo_escalonamento[m_parceira][idx_parceiro] = job_parceiro, job_alvo

    return novo_escalonamento


def calcular_C_e_X(solucao, dados_instancia):
    """
    Calcula os dicionários C (término) e X (sequência) a partir da
    solução do Simulated Annealing.
    """
    C_dict = {}
    X_dict = {}
    p = dados_instancia["p"]
    S = dados_instancia["S"]

    for maquina, job_list in solucao.items():
        tempo_maquina = 0
        job_anterior = 0  # Job dummy inicial

        for job_atual in job_list:
            setup = S.get((maquina, job_anterior, job_atual), 0)
            processamento = p.get((maquina, job_atual), 0)
            
            # Atualiza o tempo de conclusão do job atual
            tempo_maquina += setup + processamento
            C_dict[(maquina, job_atual)] = tempo_maquina
            
            # Define a precedência no dicionário X
            X_dict[(maquina, job_anterior, job_atual)] = 1
            
            # Atualiza o job anterior para a próxima iteração
            job_anterior = job_atual
            
    return X_dict, C_dict

'''
Função principal do Simulated Annealing.

Args: 
    dados_instancia (dict): Dicionário com os dados da instância.
    args (object): Objeto ou namespace contendo os hiperparâmetros do algoritmo (ex: temp_inicial, alpha, time_limit, etc.).

Returns:
    dict: Dicionário com os resultados da execução, contendo:
        - "objetivo": O custo (makespan) da melhor solução encontrada.
        - "runtime": O tempo total de execução em segundos.
        - "status_code": Código indicando o motivo da parada.
        - "solucao": O dicionário da melhor solução de escalonamento.
'''
def rodar_simulated_annealing(dados_instancia: dict, temp_inicial, temp_final, alpha, iter_por_temp, block, block_size, p_shift, time_limit, seed):
    # marca o tempo q a função começou:
    start_time = time.time()

    solucao_atual = sa_construir_solucao(dados_instancia)
    custo_atual = sa_calcular_custo(solucao_atual, dados_instancia)
    # a melhor solucao ate entao é a atual, entao cria uma copia dela: 
    melhor_solucao = pickle.loads(pickle.dumps(solucao_atual, protocol=pickle.HIGHEST_PROTOCOL))
    melhor_custo = custo_atual
    temperatura = temp_inicial

    # enquanto a temperatura nao esfriar ate seu limite minimo e o tempo de execução estiver dentro do tempo limite: 
    while temperatura > temp_final and (time.time() - start_time) < time_limit:

        # pra cada nivel de temperatura: 
        for _ in range(iter_por_temp):

            # gera uma solução vizinha e calcula o custo dela: 
            vizinho = sa_gerar_vizinho(solucao_atual, dados_instancia, block, block_size, p_shift)
            custo_vizinho = sa_calcular_custo(vizinho, dados_instancia)
            delta = custo_vizinho - custo_atual

            # se delta for menor que 0 ou a nova solução é pior, mas é aceita por Metropolis: 
            if delta < 0 or random.random() < math.exp(-delta / temperatura):
                solucao_atual = vizinho
                custo_atual = custo_vizinho

                # ve se a nova solução é melhor que a melhor solução encontrada ate agora:
                if custo_atual < melhor_custo:
                    melhor_solucao = pickle.loads(pickle.dumps(vizinho, protocol=pickle.HIGHEST_PROTOCOL))
                    melhor_custo = custo_atual

        # reduz a temperatura:
        temperatura *= alpha

    # Calcula o tempo decorrido na execucao do SA
    runtime = time.time() - start_time
    
    # Gerar dicionários X e C a partir da melhor solução encontrada
    X_dict, C_dict = calcular_C_e_X(melhor_solucao, dados_instancia)

    return {
        "objetivo": melhor_custo, 
        "runtime": runtime,
        "status_code": 2 if runtime < time_limit else 9, 
        "solucao": melhor_solucao,
        "X_dict": X_dict, # Adiciona o dicionário X
        "C_dict": C_dict   # Adiciona o dicionário C
    }

