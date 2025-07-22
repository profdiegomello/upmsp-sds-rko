from pulp import LpMinimize, LpProblem, LpVariable, lpSum, value, PULP_CBC_CMD, GUROBI
import gurobipy
from itertools import product
import matplotlib.pyplot as plt
import numpy as np
import argparse
import os
import random
import time
import math
import pickle

'''
Dicionario principal com os dados das instancias.
Sera passado de parâmetro em minhas funções como dados_instancia
'''
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
def rodar_simulated_annealing(dados_instancia: dict, temp_inicial, temp_final, alpha, iter_por_temp, block, block_size, p_shift, time_limit):
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

    runtime = time.time() - start_time

    return {
        "objetivo": melhor_custo, "runtime": runtime,
        "status_code": 2 if runtime < time_limit else 9, "solucao": melhor_solucao
    }

def modelSolving(M, N, N0, p, S, log, time_limit=None):

    # Constante grande:
    V = 1000

    model = LpProblem(name="UPMSPST", sense=LpMinimize)

    # Variáveis de decisão:
    X = LpVariable.dicts("X", product(M, N0, N), cat='Binary')
    C = LpVariable.dicts("C", product(M, N0), lowBound=0, cat='Continuous')
    Cmax = LpVariable("Cmax", lowBound=0, cat='Continuous')

    # Função objetivo (1):
    model += Cmax

    # Restrições (2):
    for k in N:
        model += lpSum(X[i, j, k] for i in M for j in N0 if j != k) == 1

    # Restrições (3):
    for j in N:
        model += lpSum(X[i, j, k] for i in M for k in N if j != k) <= 1

    # Restrições (4):
    for i in M:
        model += lpSum(X[i, 0, k] for k in N) <= 1

    # Restrições (5):
    for j in N:
        for k in N:
            if j != k:
                for i in M:
                    model += lpSum(X[i, h, j] for h in N0 if h != k and h != j) >= X[i, j, k]

    # Restrições (6):
    for j in N0:
        for k in N:
            if j != k:
                for i in M:
                    model += C[i, k] + V * (1 - X[i, j, k]) >= C[i, j] + S.get((i, j, k), 0) + p.get((i, k), 0)

    # Restrições (7):
    for i in M:
        model += C[i, 0] == 0

    # Restrições (8):
    for i in M:
        for j in N:
            model += C[i, j] >= 0

    # Restrições (9):
    for j in N:
        for i in M:
            model += Cmax >= C[i, j]

    # Resolver o modelo
    if time_limit is not None:
        modelo = model.solve(GUROBI(msg=True, logPath=str(log).replace(".txt", ""), timeLimit=time_limit))
    else:
        modelo = model.solve(GUROBI(msg=True, logPath=str(log).replace(".txt", "")))

    # Extrair valores das variáveis, separando por tipo:
    bin_vars = {}
    int_vars = {}
    cont_vars = {}

    for var in model.variables():
        # 'var' é um objeto LpVariable
        if var.cat == 'Binary':
            bin_vars[var.name] = var.varValue
        elif var.cat == 'Integer':
            int_vars[var.name] = var.varValue
        elif var.cat == 'Continuous':
            cont_vars[var.name] = var.varValue

    solucao_gurobi = {"X": X, "C": C}

    # Também extrair o valor do Cmax (que é contínuo, mas já está no dicionário cont_vars)
    Cmax_val = Cmax.varValue

    return {
        "objetivo": value(model.objective), "runtime": model.solutionTime,
        "lowerbound": model.solverModel.ObjBound, "gap": model.solverModel.MIPGap,
        "status_code": model.solverModel.Status, "solucao": solucao_gurobi,
        "constraints": len(model.constraints), "variables": len(model.variables()),
        "binarias": len(bin_vars), "inteiras": len(int_vars), "continuas": len(cont_vars)
    }

def geraInstancia(seed, M, N, lowerP, upperP, lowerS, upperS):
    global dados
    random.seed(seed)

    #Criando uma lista com os valores passados pra M, N e N0:
    maquinas = list(range(1, M+1))
    jobs = list(range(1, N+1))
    N0 = [0] + jobs #adicona o dummy na lista

    #Gerando tempo de processamento aleatório:
    p = {}
    for i in maquinas:
        for j in jobs:
            if j == 0:
                p[(i, j)] = 0
            else:
                p[(i, j)] = random.randint(lowerP, upperP)

    #Gerando tempo de setup aleatório:
    S = {}
    for i in maquinas:
        for j in N0:
            for k in jobs:
                if j != k:
                    S[(i, j, k)] = random.randint(lowerS, upperS)

    dados["M"]=maquinas
    dados["N"]=jobs
    dados["N0"]=N0
    dados["V"]=0
    dados["p"]=p
    dados["S"]=S
    return
    
#Gerencia a leitura de arquivos
def le_arquivo(args):
    if not(os.path.exists(args.nome_instancia)):
        print(f"O arquivo <{args.nome_instancia}> não existe!")
        exit()
    else:
        le_formato_variavel(args.nome_instancia, "MNNO;V;p;S")
        return

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

def gerar_gantt(solucao, dados, nome_arquivo, tipo_solucao='SA'):

    try:
        # Obtém o nome da pasta a partir do caminho completo do arquivo
        pasta_destino = os.path.dirname(nome_arquivo)
        # Se o nome da pasta não for vazio, cria a pasta (e subpastas)
        if pasta_destino:
            os.makedirs(pasta_destino, exist_ok=True)
    except Exception as e:
        print(f"\nAVISO: Não foi possível criar a pasta para o gráfico de Gantt. Erro: {e}")

    M, N, p, S = dados.get("M", []), dados.get("N", []), dados.get("p", {}), dados.get("S", {})
    if not M or not N: return
    
    fig, ax = plt.subplots(figsize=(15, max(5, len(M) * 0.8)))
    cmap = plt.colormaps.get_cmap("tab20").resampled(len(N))
    job_colors = {j: cmap(j - 1) for j in N}
    max_tempo_final = 0

    if tipo_solucao == 'SA':
        for maquina, sequencia in solucao.items():
            tempo_atual, job_anterior = 0, 0
            for job_atual in sequencia:
                setup = S.get((maquina, job_anterior, job_atual), 0)
                proc_time = p.get((maquina, job_atual), 0)
                start_time = tempo_atual + setup
                ax.barh(y=f'Máquina {maquina}', width=proc_time, left=start_time, height=0.6,
                        color=job_colors.get(job_atual, 'gray'), edgecolor='black')
                ax.text(start_time + proc_time / 2, f'Máquina {maquina}', f'J{job_atual}',
                        ha='center', va='center', color='white', fontsize=9, fontweight='bold')
                tempo_atual = start_time + proc_time
                job_anterior = job_atual
            if tempo_atual > max_tempo_final: max_tempo_final = tempo_atual
    
    elif tipo_solucao == 'GUROBI':
        X, C = solucao.get("X", {}), solucao.get("C", {})
        if not X or not C:
            print("\nAVISO: A solução do Gurobi está vazia ou mal formatada. Não é possível gerar o gráfico.")
            return
        
        C_values = {k: v.varValue for k, v in C.items() if v.varValue is not None}
        
        for (i, k, j), var_x in X.items():
            # Verifica se a variável de decisão X tem um valor e se está ativa
            if var_x.varValue is not None and var_x.varValue > 0.5:
                proc_time = p.get((i, j), 0)
                completion_time = C_values.get((i, j)) # Pega o valor já extraído
                
                if completion_time is not None:
                    start_time = completion_time - proc_time
                    ax.barh(y=f'Máquina {i}', width=proc_time, left=start_time, height=0.6,
                            color=job_colors.get(j, 'gray'), edgecolor='black')
                    ax.text(start_time + proc_time / 2, f'Máquina {i}', f'J{j}',
                            ha='center', va='center', color='white', fontsize=9, fontweight='bold')
        
        # Calcula o makespan de forma segura
        if C_values:
            max_tempo_final = max(C_values.values()) if C_values else 0

    ax.set_xlabel("Tempo")
    ax.set_title(f"Gráfico de Gantt - Solução {tipo_solucao}")
    ax.set_yticks([f'Máquina {m}' for m in M])
    ax.grid(axis='x', linestyle='--', alpha=0.6)
    if max_tempo_final > 0: ax.set_xlim(0, max_tempo_final * 1.05)
    plt.tight_layout()
    plt.savefig(nome_arquivo, dpi=300)
    print(f"Gráfico de Gantt salvo em: {nome_arquivo}")

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
    status: int, 
    resultado,
    args 
):

   # Registra os resultados no arquivo passado, usando tabulação como separador.
   # Caso lowerbound ou gap sejam None, registra como '---'.

    # Verifica se o arquivo já existe para saber se deve escrever o cabeçalho
    novo_arquivo = not os.path.exists(arquivo_saida)

    if args.modelo.upper() == "SA":
        # Se lowerbound ou gap forem None, vamos definir uma string padrão '---'
        if(lowerbound!=None ):
            gap_str = calcula_gap(lowerbound, objetivo)
            lowerbound_str = lowerbound
        else:
            gap_str="---"
            lowerbound_str = "---"
    else: 
        lowerbound_str = resultado['lowerbound']
        gap_str = calcula_gap(lowerbound_str, resultado['objetivo'])
    

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

def main():
    parser = argparse.ArgumentParser(description="Simulated Annealing para UPMS-ST")
    parser.add_argument("nome_instancia", help="Caminho para o arquivo da instância.")
    parser.add_argument("--modelo", default="SA", choices=["GUROBI", "SA"], help="Modelo a ser usado.")
    parser.add_argument("--arq_saida", default="resultados.txt", help="Arquivo de saída dos resultados.")
    parser.add_argument("--arq_gantt", default="gantt.png", help="Arquivo de saída do gráfico Gantt.")
    parser.add_argument("--time_limit", type=int, default=30, help="Limite de tempo em segundos.")
    parser.add_argument("--temp_inicial", type=float, default=1000.0)
    parser.add_argument("--temp_final", type=float, default=1.0)
    parser.add_argument("--alpha", type=float, default=0.95)
    parser.add_argument("--iter_por_temp", type=int, default=100)
    parser.add_argument("--block",type=float, default=0)
    parser.add_argument("--block_size", type=int, default=0)
    parser.add_argument("--p_shift", type=float, default=0)
    parser.add_argument("--lowerbound", type=float, default=None, help="Número de lowerbound do Gurobi para calcular o gap")
    args = parser.parse_args()

    le_arquivo(args) 
    
    # Se a instancia não passar as máquinas elegíveis:     
    # Coloco que todas as máquinas são elegíveis para todos os jobs
    if 'maquinasElegiveis' not in dados: dados['maquinasElegiveis'] = {j: dados['M'] for j in dados['N']}

    if args.modelo.upper() == "GUROBI":
        log_path = args.nome_instancia + ".log"
        resultado = modelSolving(dados["M"], dados["N"], dados["N0"], dados["p"], dados["S"], log_path, args.time_limit)
        if resultado.get("lowerbound") is not None:
            print(f"Lowerbound: {resultado['lowerbound']}")
        parametros = f"M-{len(dados['M'])}|N-{len(dados['N'])}|N0-{len(dados['N0'])}|p-{len(dados['p'])}|S-{len(dados['S'])}|tl-{args.time_limit}"
    else: 
        resultado = rodar_simulated_annealing(dados, args.temp_inicial, args.temp_final, args.alpha, args.iter_por_temp, args.block, args.block_size, args.p_shift, args.time_limit)
        parametros = f"ti-{args.temp_inicial}|tf-{args.temp_final}|a-{args.alpha}|it-{args.iter_por_temp}|b-{args.block}|bs-{args.block_size}|ps-{args.p_shift}|tl-{args.time_limit}"
        

    salvar_resultado(args.arq_saida, args.nome_instancia, args.modelo, 
                    resultado['objetivo'], args.lowerbound, None, resultado['runtime'],
                    resultado.get('constraints', 0), resultado.get('variables', 0), 
                    parametros, len(dados["N"]), len(dados["M"]), resultado["status_code"], resultado, args)
    
    if "solucao" in resultado and resultado["solucao"]:
        gerar_gantt(resultado["solucao"], dados, args.arq_gantt, tipo_solucao=args.modelo.upper())

if __name__ == "__main__":
    main()

