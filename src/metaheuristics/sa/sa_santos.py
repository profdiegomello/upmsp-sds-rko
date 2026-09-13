import random
import time
import math
import copy

def custo_maquina(maquina: int, sequencia: list, dados_instancia: dict):
    S = dados_instancia.get("S", {})
    p = dados_instancia.get("p", {})
    tempo = 0
    job_anterior = 0
    for job_atual in sequencia:
        tempo += S.get((maquina, job_anterior, job_atual), 0) + p.get((maquina, job_atual), float('inf'))
        job_anterior = job_atual
    return tempo

def sa_calcular_custo(escalonamento: dict, dados_instancia: dict):
    tempo_maquina = {maq: custo_maquina(maq, seq, dados_instancia) for maq, seq in escalonamento.items()}
    return max(tempo_maquina.values()) if tempo_maquina else 0

def sa_construir_solucao(dados_instancia: dict):
    N = dados_instancia.get("N", [])
    M = dados_instancia.get("M", [])
    maq_elegiveis = dados_instancia.get("maquinasElegiveis", {})
    escalonamento = {maquina: [] for maquina in M}
    
    for job in N:
        maquina = random.choice(maq_elegiveis.get(job, M))
        escalonamento[maquina].append(job)
        
    for maquina in M:
        random.shuffle(escalonamento[maquina])
        
    return escalonamento

def encontrar_maquina_critica(escalonamento: dict, dados_instancia: dict):
    tempo_maquina = {maq: custo_maquina(maq, seq, dados_instancia) for maq, seq in escalonamento.items()}
    return max(tempo_maquina, key=tempo_maquina.get) if tempo_maquina else None

def sa_gerar_vizinho(escalonamento: dict, dados_instancia: dict):
    novo_escalonamento = {k: list(v) for k, v in escalonamento.items()}
    M = dados_instancia.get("M", [])
    maq_elegiveis = dados_instancia.get("maquinasElegiveis", {})
    
    if random.random() < 0.5:
        m_x = encontrar_maquina_critica(novo_escalonamento, dados_instancia)
    else:
        m_x = random.choice(M)
        
    if m_x is None or not novo_escalonamento[m_x]:
        nao_vazias = [m for m in M if novo_escalonamento[m]]
        if not nao_vazias:
            return novo_escalonamento
        m_x = random.choice(nao_vazias)

    intensification = (random.random() < 0.5)
    nh = random.randint(1, 6)
    seq_x = novo_escalonamento[m_x]
    
    def aplicar_shift(maquina, sequencia):
        if len(sequencia) <= 1:
            return
        idx_origem = random.randrange(len(sequencia))
        job = sequencia.pop(idx_origem)
        if intensification:
            melhor_pos = 0
            menor_custo = float('inf')
            for pos in range(len(sequencia) + 1):
                sequencia.insert(pos, job)
                c = custo_maquina(maquina, sequencia, dados_instancia)
                if c < menor_custo:
                    menor_custo = c
                    melhor_pos = pos
                sequencia.pop(pos)
            sequencia.insert(melhor_pos, job)
        else:
            sequencia.insert(random.randint(0, len(sequencia)), job)

    if nh == 1:
        aplicar_shift(m_x, seq_x)
        
    elif nh == 2:
        if len(seq_x) >= 2:
            idx1 = random.randrange(len(seq_x))
            if intensification:
                melhor_idx2 = idx1
                menor_custo = float('inf')
                for idx2 in range(len(seq_x)):
                    if idx1 == idx2: 
                        continue
                    seq_x[idx1], seq_x[idx2] = seq_x[idx2], seq_x[idx1]
                    c = custo_maquina(m_x, seq_x, dados_instancia)
                    if c < menor_custo:
                        menor_custo = c
                        melhor_idx2 = idx2
                    seq_x[idx1], seq_x[idx2] = seq_x[idx2], seq_x[idx1]
                seq_x[idx1], seq_x[melhor_idx2] = seq_x[melhor_idx2], seq_x[idx1]
            else:
                idx2 = random.randrange(len(seq_x))
                seq_x[idx1], seq_x[idx2] = seq_x[idx2], seq_x[idx1]

    elif nh == 3:
        if len(seq_x) >= 1:
            idx = random.randrange(len(seq_x))
            job = seq_x[idx]
            destinos = [m for m in M if m != m_x and m in maq_elegiveis.get(job, M)]
            if destinos:
                m_y = random.choice(destinos)
                seq_x.pop(idx)
                seq_y = novo_escalonamento[m_y]
                if intensification:
                    melhor_pos = 0
                    menor_custo = float('inf')
                    for pos in range(len(seq_y) + 1):
                        seq_y.insert(pos, job)
                        c = custo_maquina(m_y, seq_y, dados_instancia)
                        if c < menor_custo:
                            menor_custo = c
                            melhor_pos = pos
                        seq_y.pop(pos)
                    seq_y.insert(melhor_pos, job)
                else:
                    seq_y.insert(random.randint(0, len(seq_y)), job)
                    
    elif nh == 4:
        if len(seq_x) >= 1:
            idx_x = random.randrange(len(seq_x))
            job_x = seq_x[idx_x]
            parceiras = [m for m in M if m != m_x and len(novo_escalonamento[m]) > 0 and m in maq_elegiveis.get(job_x, M)]
            parceiras_validas = [m for m in parceiras if any(m_x in maq_elegiveis.get(j, M) for j in novo_escalonamento[m])]
            
            if parceiras_validas:
                m_y = random.choice(parceiras_validas)
                seq_y = novo_escalonamento[m_y]
                candidatos_y = [i for i, j in enumerate(seq_y) if m_x in maq_elegiveis.get(j, M)]
                idx_y = random.choice(candidatos_y)
                job_y = seq_y[idx_y]
                
                seq_x.pop(idx_x)
                seq_y.pop(idx_y)
                
                if intensification:
                    melhor_pos_x = 0
                    menor_custo_x = float('inf')
                    for pos in range(len(seq_x) + 1):
                        seq_x.insert(pos, job_y)
                        c = custo_maquina(m_x, seq_x, dados_instancia)
                        if c < menor_custo_x:
                            menor_custo_x = c
                            melhor_pos_x = pos
                        seq_x.pop(pos)
                    seq_x.insert(melhor_pos_x, job_y)
                    
                    melhor_pos_y = 0
                    menor_custo_y = float('inf')
                    for pos in range(len(seq_y) + 1):
                        seq_y.insert(pos, job_x)
                        c = custo_maquina(m_y, seq_y, dados_instancia)
                        if c < menor_custo_y:
                            menor_custo_y = c
                            melhor_pos_y = pos
                        seq_y.pop(pos)
                    seq_y.insert(melhor_pos_y, job_x)
                else:
                    seq_x.insert(random.randint(0, len(seq_x)), job_y)
                    seq_y.insert(random.randint(0, len(seq_y)), job_x)
                    
    elif nh == 5:
        aplicar_shift(m_x, seq_x)
        aplicar_shift(m_x, seq_x)
        
    elif nh == 6:
        if len(seq_x) >= 1:
            idx_x = random.randrange(len(seq_x))
            job_x = seq_x[idx_x]
            parceiras_validas = []
            for m in M:
                if m == m_x or len(novo_escalonamento[m]) == 0 or m not in maq_elegiveis.get(job_x, M):
                    continue
                if any(m_x in maq_elegiveis.get(j, M) for j in novo_escalonamento[m]):
                    parceiras_validas.append(m)
                    
            if parceiras_validas:
                m_y = random.choice(parceiras_validas)
                seq_y = novo_escalonamento[m_y]
                candidatos_y = [i for i, j in enumerate(seq_y) if m_x in maq_elegiveis.get(j, M)]
                
                if intensification:
                    melhor_idx_y = candidatos_y[0]
                    menor_custo_x = float('inf')
                    for iy in candidatos_y:
                        jy = seq_y[iy]
                        seq_x[idx_x] = jy
                        c = custo_maquina(m_x, seq_x, dados_instancia)
                        if c < menor_custo_x:
                            menor_custo_x = c
                            melhor_idx_y = iy
                        seq_x[idx_x] = job_x
                    idx_y = melhor_idx_y
                else:
                    idx_y = random.choice(candidatos_y)
                    
                seq_x[idx_x], seq_y[idx_y] = seq_y[idx_y], seq_x[idx_x]

    return novo_escalonamento

def calcular_C_e_X(solucao, dados_instancia):
    C_dict = {}
    X_dict = {}
    p = dados_instancia.get("p", {})
    S = dados_instancia.get("S", {})

    for maquina, job_list in solucao.items():
        tempo_maquina = 0
        job_anterior = 0
        for job_atual in job_list:
            setup = S.get((maquina, job_anterior, job_atual), 0)
            processamento = p.get((maquina, job_atual), 0)
            tempo_maquina += setup + processamento
            C_dict[(maquina, job_atual)] = tempo_maquina
            X_dict[(maquina, job_anterior, job_atual)] = 1
            job_anterior = job_atual
    return X_dict, C_dict

def rodar_simulated_annealing(dados_instancia: dict, temp_inicial, temp_final, alpha, iter_por_temp, block, block_size, p_shift, time_limit, seed):
    """
    Função estritamente fiel ao Algoritmo 1 de Santos et al. (2016).
    Recebe os argumentos extras da CLI (block, block_size, p_shift) e os ignora para não quebrar o seu argparse.
    """
    if seed is not None:
        random.seed(seed)
        
    start_time = time.time()
    
    S = sa_construir_solucao(dados_instancia)
    custo_S = sa_calcular_custo(S, dados_instancia)
    
    S_star = copy.deepcopy(S)
    custo_S_star = custo_S
    
    t = temp_inicial
    
    print(f"[{0.00:^7.2f}s] SA Inicializado. Makespan inicial: {custo_S_star:.4f} | t0={temp_inicial}, alpha={alpha}, sa_max={iter_por_temp}", flush=True)

    while True:
        elapsed = time.time() - start_time
        if elapsed >= time_limit:
            break
            
        for _ in range(int(iter_por_temp)):
            if (time.time() - start_time) >= time_limit:
                break
                
            S_prime = sa_gerar_vizinho(S, dados_instancia)
            custo_S_prime = sa_calcular_custo(S_prime, dados_instancia)
            
            delta = custo_S_prime - custo_S
            
            if delta <= 0:
                S = S_prime
                custo_S = custo_S_prime
                
                if custo_S_prime < custo_S_star:
                    S_star = copy.deepcopy(S_prime)
                    custo_S_star = custo_S_prime
                    
                    tempo_decorrido = time.time() - start_time
                    print(f"[{tempo_decorrido:^7.2f}s] Nova melhor solucao: {custo_S_star:.4f} (Temperatura atual: {t:.4f})", flush=True)
            else:
                x = random.random()
                if x < math.exp(-delta / t):
                    S = S_prime
                    custo_S = custo_S_prime
                    
        t = alpha * t
        
        if t < temp_final:
            t = temp_inicial

    runtime = time.time() - start_time
    X_dict, C_dict = calcular_C_e_X(S_star, dados_instancia)

    return {
        "objetivo": custo_S_star, 
        "runtime": runtime,
        "status_code": 2 if runtime < time_limit else 9, 
        "solucao": S_star,
        "X_dict": X_dict,
        "C_dict": C_dict
    }
