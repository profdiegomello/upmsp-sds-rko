# solver-rko-upmsp-sds.py
import numpy as np
import os
import sys
import argparse
import time # Adicionado para medir o tempo total
from types import SimpleNamespace

# Adicionando a pasta raiz do codigo fonte para que todos os demais imports sejam relativos
# Para executar, usar 'python3 -m solvers.solver_brkga.py' (ou executar diretamente)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from metaheuristics.rkolib.RKO import RKO
from metaheuristics.rkolib.Environment import RKOEnvAbstract, check_env
import input_output.input_reader as input_reader
import input_output.output_writer as output_writer

class UPMSPSDSProblem(RKOEnvAbstract):
    """
    Ambiente do UPMSP-SDS para o framework RKO.
    Cada decoder tem seu próprio método: _decode_ect, _decode_ksts, ...
    O método público `decoder(keys)` apenas faz o despacho para o decoder
    selecionado em self.decoder_name. Não altere a assinatura de `decoder`.
    """
    def __init__(self, instance_path: str, decoder: str = "ect"):
        super().__init__()
        print(f"Carregando instância do UPMSP-SDS de: {instance_path}")

        # Carrega dados
        self.dados = self._load_data(instance_path)

        # Nome do decoder escolhido (atributo obrigatório conforme pedido)
        self.decoder_name = (decoder or "ect").lower()

        # atributos obrigatórios
        self.instance_name = os.path.basename(instance_path)

        # determina tam_solution conforme decoder (1N, 2N, ...)
        n_jobs = len(self.dados.get("N", []))
        if self.decoder_name == "ksts":
            self.tam_solution = 2 * n_jobs
        elif self.decoder_name in ("2n", "2n*"):
            self.tam_solution = 2 * n_jobs
        elif self.decoder_name == "m3law" or "M3LAW":
            self.tam_solution = n_jobs
        elif self.decoder_name == "incremental" or "INCREMENTAL":
            self.tam_solution = n_jobs
        elif self.decoder_name == "cheapest" or "CHEAPEST":
            self.tam_solution = 2 * n_jobs
        else:
            self.tam_solution = n_jobs

        # demais atributos (mantive o que já havia)
        self.LS_type: str = 'Best'
        self.dict_best: dict = {}
        self.save_q_learning_report = False

        # parâmetros de meta-heurísticas (mantidos)
        self.BRKGA_parameters = {'p': [100], 'pe': [0.20], 'pm': [0.10], 'rhoe': [0.70]}
        self.SA_parameters = {'SAmax': [50], 'alphaSA': [0.99], 'betaMin': [0.05], 'betaMax': [0.25], 'T0': [10000]}
        self.ILS_parameters = {'betaMin': [0.10, 0.2], 'betaMax': [0.20, 0.3]}
        self.VNS_parameters = {'kMax': [5, 3], 'betaMin': [0.05, 0.1]}
        self.PSO_parameters = {'PSize': [100], 'c1': [2.05], 'c2': [2.05], 'w': [0.73]}
        self.GA_parameters = {'sizePop': [100], 'probCros': [0.98], 'probMut': [0.005]}
        self.LNS_parameters = {'betaMin': [0.10], 'betaMax': [0.30], 'TO': [1000], 'alphaLNS': [0.95]}

    def _load_data(self, instance_path: str):
        """Carrega instância usando input_reader (interface antiga usada no projeto)."""
        mock_args = SimpleNamespace(nome_instancia=instance_path)
        return input_reader.le_arquivo(mock_args)

    # -------------------------
    # Métodos privados: decoders
    # -------------------------

    def _decode_ect(self, keys: np.ndarray) -> dict:
        """Decoder ECT (Earliest Completion Time) — 1 gene por job."""
        num_jobs = len(self.dados["N"])
        num_machines = len(self.dados["M"])

        # ordena por prioridade (menor key -> maior prioridade)
        job_sequence = np.argsort(keys)[:num_jobs]  # garante comprimento

        machine_schedules = [[] for _ in range(num_machines)]
        machine_completion_times = np.zeros(num_machines)

        for job_idx in job_sequence:
            job = int(job_idx) + 1  # 1-based nas instâncias
            best_machine = -1
            min_completion_time = float('inf')

            for machine_idx in range(num_machines):
                machine = machine_idx + 1
                last_job = machine_schedules[machine_idx][-1] if machine_schedules[machine_idx] else 0
                earliest_start = machine_completion_times[machine_idx]

                setup_time = self.dados["S"].get((machine, last_job, job), 0)
                proc_time = self.dados["p"].get((machine, job), 0)

                completion_time = earliest_start + setup_time + proc_time
                if completion_time < min_completion_time:
                    min_completion_time = completion_time
                    best_machine = machine_idx

            machine_schedules[best_machine].append(job)
            machine_completion_times[best_machine] = min_completion_time

        makespan = float(np.max(machine_completion_times)) if machine_completion_times.size > 0 else 0.0
        return {"schedule": machine_schedules, "makespan": makespan}

    def _decode_ksts(self, keys: np.ndarray) -> dict:
        """
        KSTS Guloso (2N genes): primeiras N = prioridades; últimas N = chaves da roleta.
        Critério principal: setups (filtra candidatas usando T_k média da linha de last_k).
        Critério secundário / fallback: roleta adaptativa inversa à carga (makespan local).
        """
        num_jobs = len(self.dados["N"])
        num_machines = len(self.dados["M"])

        # garante tamanho mínimo
        if len(keys) < 2 * num_jobs:
            keys = np.resize(keys, 2 * num_jobs)

        priority_keys = keys[:num_jobs]
        roulette_keys = keys[num_jobs:2 * num_jobs]

        # ordem global
        jobs_ordered = list(np.argsort(priority_keys))[:num_jobs]

        machine_schedules = [[] for _ in range(num_machines)]
        machine_completion_times = np.zeros(num_machines)
        cargas = np.zeros(num_machines)  # proxy de carga = soma dos tempos de processamento

        epsilon = 1e-9

        def calc_threshold(machine_idx: int, last_job: int) -> float:
            """Média dos setups S(machine, last_job, j) para todos j != last_job."""
            machine_id = machine_idx + 1
            vals = []
            for j in self.dados["N"]:
                if j == last_job:
                    continue
                vals.append(self.dados["S"].get((machine_id, last_job, j), 0))
            return float(sum(vals) / len(vals)) if vals else 0.0

        for idx in jobs_ordered:
            job = int(idx) + 1

            # --- roleta adaptativa por carga ---
            weights = [1.0 / (epsilon + c) for c in cargas]
            total_w = sum(weights)
            probs = [w / total_w for w in weights] if total_w > 0 else [1.0 / num_machines] * num_machines
            cumul = np.cumsum(probs)

            r = float(roulette_keys[int(idx)] % 1.0)
            mk_roleta_idx = int(np.searchsorted(cumul, r, side='right'))
            if mk_roleta_idx >= num_machines:
                mk_roleta_idx = num_machines - 1

            # --- cria conjunto de candidatas via critério de setup ---
            candidatas = []  # (machine_idx, s_val)
            for m_idx in range(num_machines):
                if not machine_schedules[m_idx]:
                    # máquina vazia => candidato automático com setup 0
                    candidatas.append((m_idx, 0.0))
                else:
                    last_job = machine_schedules[m_idx][-1]
                    s_val = float(self.dados["S"].get((m_idx + 1, last_job, job), 0))
                    T_k = calc_threshold(m_idx, last_job)
                    if s_val <= T_k:
                        candidatas.append((m_idx, s_val))

            # --- decisão final ---
            if candidatas:
                best_m_idx, best_s = min(candidatas, key=lambda x: x[1])
            else:
                best_m_idx = mk_roleta_idx
                last_job = machine_schedules[best_m_idx][-1] if machine_schedules[best_m_idx] else 0
                best_s = float(self.dados["S"].get((best_m_idx + 1, last_job, job), 0))

            # atualiza schedule e tempos
            proc_time = float(self.dados["p"].get((best_m_idx + 1, job), 0.0))
            machine_schedules[best_m_idx].append(job)
            # atualiza tempo de conclusão: somando o setup escolhido + proc_time
            machine_completion_times[best_m_idx] += best_s + proc_time
            cargas[best_m_idx] += proc_time

        makespan = float(np.max(machine_completion_times)) if machine_completion_times.size > 0 else 0.0
        return {"schedule": machine_schedules, "makespan": makespan}

    def _decoder_m3law(self, keys: np.ndarray) -> dict:
        
        """
        Novo Decoder: Mioptic Minimum Makespan + Look Ahead Window.
        Analisa uma janela de tarefas futuras para decidir a melhor alocação.
        """
        num_jobs = len(self.dados["N"])
        num_machines = len(self.dados["M"])
        
        # Parâmetro da janela (pode ser ajustado)
        WINDOW_SIZE = 3

        # 1. Ordena os jobs pela prioridade (chaves)
        # np.argsort retorna indices 0-based, somamos 1 para pegar o ID do Job
        jobs_ordenados = [idx + 1 for idx in np.argsort(keys)]
        
        # Lista de pendentes para podermos remover itens dinamicamente
        jobs_pendentes = list(jobs_ordenados)

        machine_schedules = [[] for _ in range(num_machines)]
        machine_completion_times = np.zeros(num_machines)
        # Mantemos rastreio do último job de forma rápida
        last_job_on_machine = [0] * num_machines 

        # Enquanto houver jobs para alocar
        while jobs_pendentes:
            # 2. Define a janela de visualização
            janela = jobs_pendentes[:WINDOW_SIZE]
            
            melhor_job = None
            melhor_maquina_idx = -1
            menor_tempo_termino_global = float('inf')

            # 3. Avalia todas as combinações (Job da Janela X Máquina)
            for job_candidato in janela:
                for machine_idx in range(num_machines):
                    machine = machine_idx + 1
                    
                    ultimo_job = last_job_on_machine[machine_idx]
                    
                    # Calcula custos
                    setup_time = self.dados["S"].get((machine, ultimo_job, job_candidato), 0)
                    processing_time = self.dados["p"].get((machine, job_candidato), float('inf'))
                    
                    # Earliest Completion Time dentro da janela
                    completion_time = machine_completion_times[machine_idx] + setup_time + processing_time

                    if completion_time < menor_tempo_termino_global:
                        menor_tempo_termino_global = completion_time
                        melhor_maquina_idx = machine_idx
                        melhor_job = job_candidato

            # 4. Realiza a alocação
            if melhor_job is not None:
                machine_schedules[melhor_maquina_idx].append(melhor_job)
                machine_completion_times[melhor_maquina_idx] = menor_tempo_termino_global
                last_job_on_machine[melhor_maquina_idx] = melhor_job
                
                # Remove da lista de pendentes
                jobs_pendentes.remove(melhor_job)
            else:
                # Fallback de segurança (caso processing_time seja infinito para todos)
                job_forcado = jobs_pendentes.pop(0)
                machine_schedules[0].append(job_forcado)

        makespan = np.max(machine_completion_times)
        return {"schedule": machine_schedules, "makespan": makespan}

    def _decoder_incremental(self, keys: np.ndarray) -> dict:
        """
        Decoder 5: Ordenação por chave + Alocação por Custo Incremental no makespan
        """
        n_jobs = len(self.dados["N"])
        copia = keys 

        # 1. Ordena os jobs com base nas chaves aleatórias
        jobs_ordenados = sorted(range(1, n_jobs + 1), key=lambda j: copia[j - 1])
        
        # 2. Inicializa o estado das máquinas
        maquinas_jobs = {m: [] for m in self.dados["M"]}
        
        # 3. Aloca cada job ordenado para a máquina que causa o menor aumento no makespan
        for job in jobs_ordenados:
            melhor_maquina = None
            menor_aumento_makespan = float('inf')
            
            # Avalia cada máquina para encontrar a melhor
            for maquina in self.dados["M"]:
                # Crie uma cópia temporária da máquina para o cálculo 
                temp_maquinas = {m: list(maquinas_jobs[m]) for m in self.dados["M"]}
                temp_maquinas[maquina].append(job)
                
                # Calcule o makespan para essa configuração temporária
                makespan_temp = 0
                for m_temp in self.dados["M"]:
                    tempo_maquina = 0
                    anterior = 0
                    for j_temp in temp_maquinas[m_temp]:
                        tempo_maquina += self.dados["S"].get((m_temp, anterior, j_temp), 0)
                        tempo_maquina += self.dados["p"][(m_temp, j_temp)]
                        anterior = j_temp
                    if tempo_maquina > makespan_temp:
                        makespan_temp = tempo_maquina
                
                # Calcule o makespan da configuração atual (antes de alocar o job)
                makespan_atual = 0
                for m_atual in self.dados["M"]:
                    tempo_maquina_atual = 0
                    anterior = 0
                    for j_atual in maquinas_jobs[m_atual]:
                        tempo_maquina_atual += self.dados["S"].get((m_atual, anterior, j_atual), 0)
                        tempo_maquina_atual += self.dados["p"][(m_atual, j_atual)]
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

        schedule_list = [maquinas_jobs[m] for m in sorted(self.dados["M"])]
        
        # Calcula o makespan final para retorno 
        final_makespan = 0
        for m in self.dados["M"]:
            tempo_maquina = 0
            anterior = 0
            for j in maquinas_jobs[m]:
                tempo_maquina += self.dados["S"].get((m, anterior, j), 0)
                tempo_maquina += self.dados["p"][(m, j)]
                anterior = j
            if tempo_maquina > final_makespan:
                final_makespan = tempo_maquina

        return {"schedule": schedule_list, "makespan": final_makespan}

    def _decode_cheapest_insertion(self, keys: np.ndarray) -> dict:
        """
        Decoder: CHEAPEST_INSERTION (inserção mais barata com ranking viciado + busca local).
        Representação esperada: 2N genes (primeira metade = ordenação/prioridade,
        segunda metade = escolha/bias).
        Retorna: {"schedule": machine_schedules_list, "makespan": makespan}
        """
        num_jobs = len(self.dados["N"])
        machines = list(self.dados["M"])  # lista de ids das máquinas (1-based)
        num_machines = len(machines)

        # garante que teremos 2N genes (se não, redimensiona - ideal é gerar corretamente)
        if len(keys) < 2 * num_jobs:
            keys = np.resize(keys, 2 * num_jobs)

        genes_ordem = keys[:num_jobs]
        genes_escolha = keys[num_jobs:2 * num_jobs]

        # 1. Ordenar jobs (Prioridade definida pelo GA)
        jobs_ordenados = sorted(range(1, num_jobs + 1), key=lambda j: genes_ordem[j - 1])

        # Representação temporária: dicionário m -> lista de jobs
        maquinas_jobs = {m: [] for m in machines}
        # carga_maquinas guarda o tempo acumulado da sequência atual (setup+proc)
        carga_maquinas = {m: 0.0 for m in machines}

        # Função auxiliar para calcular tempo total de uma sequência numa máquina
        def tempo_seq_na_maquina(m: int, seq: list) -> float:
            t = 0.0
            anterior = 0
            for j in seq:
                t += float(self.dados["S"].get((m, anterior, j), 0))
                t += float(self.dados["p"].get((m, j), 0))
                anterior = j
            return t

        # 2. Para cada job, avalia inserções em todas as máquinas (Cheapest Insertion global)
        for job in jobs_ordenados:
            ranking_opcoes = []  # (makespan_projetado, maquina, posicao, incremento)

            for m in machines:
                sequencia_atual = maquinas_jobs[m]
                melhor_pos_m = 0
                menor_incremento_m = float('inf')

                # testa todas as posições possíveis (0 .. len)
                for pos in range(len(sequencia_atual) + 1):
                    nova_seq = sequencia_atual[:pos] + [job] + sequencia_atual[pos:]
                    tempo_novo = tempo_seq_na_maquina(m, nova_seq)
                    incremento = tempo_novo - carga_maquinas[m]

                    if incremento < menor_incremento_m:
                        menor_incremento_m = incremento
                        melhor_pos_m = pos

                makespan_projetado = carga_maquinas[m] + menor_incremento_m
                ranking_opcoes.append((makespan_projetado, m, melhor_pos_m, menor_incremento_m))

            # 3. Ordena as máquinas do melhor para o pior (menor makespan projetado primeiro)
            ranking_opcoes.sort(key=lambda x: x[0])

            # 4. Seleção viciada (biased ranking) usando genes_escolha
            gene_val = float(genes_escolha[job - 1])
            bias = 10.0
            idx_escolhido = int(len(ranking_opcoes) * (gene_val ** bias))
            if idx_escolhido >= len(ranking_opcoes):
                idx_escolhido = len(ranking_opcoes) - 1

            _, maquina_selecionada, pos_escolhida, custo_escolhido = ranking_opcoes[idx_escolhido]

            # 5. Efetiva a inserção
            maquinas_jobs[maquina_selecionada].insert(pos_escolhida, job)
            # atualiza carga aproximada (usamos o incremento calculado)
            carga_maquinas[maquina_selecionada] += custo_escolhido

        # -------------------------
        # BUSCA LOCAL (tentativa simples de realocar último job da máquina crítica)
        # -------------------------
        # 1. identifica máquina crítica (maior carga)
        maquina_critica = max(carga_maquinas, key=carga_maquinas.get)
        makespan_atual = carga_maquinas[maquina_critica]

        if len(maquinas_jobs[maquina_critica]) > 0:
            # pega o último job da máquina crítica
            job_problematico = maquinas_jobs[maquina_critica][-1]

            # custo da critica sem esse job
            seq_critica_sem = maquinas_jobs[maquina_critica][:-1]
            custo_critica_sem_job = tempo_seq_na_maquina(maquina_critica, seq_critica_sem)

            melhor_movimento = None
            menor_makespan_encontrado = makespan_atual

            # tenta encaixar em qualquer outra máquina
            for m_dest in machines:
                if m_dest == maquina_critica:
                    continue

                seq_dest = maquinas_jobs[m_dest]
                for pos in range(len(seq_dest) + 1):
                    nova_seq = seq_dest[:pos] + [job_problematico] + seq_dest[pos:]
                    custo_dest = tempo_seq_na_maquina(m_dest, nova_seq)

                    # novo pico considerando apenas as duas máquinas envolvidas (simplificação)
                    novo_pico = max(custo_critica_sem_job, custo_dest)

                    if novo_pico < menor_makespan_encontrado:
                        menor_makespan_encontrado = novo_pico
                        melhor_movimento = (m_dest, pos, custo_dest, custo_critica_sem_job)

            # aplica movimento se encontrado
            if melhor_movimento:
                m_dest, pos_dest, novo_custo_dest, custo_critica_sem = melhor_movimento
                # remove último job da crítica
                maquinas_jobs[maquina_critica].pop()
                # insere no destino
                maquinas_jobs[m_dest].insert(pos_dest, job_problematico)
                # após movimento, recalcule as cargas de forma segura abaixo

        # -------------------------
        # pós-processamento: monta schedule_list e calcula makespan real
        # -------------------------
        schedule_list = [maquinas_jobs[m] for m in machines]

        # recalcula cargas/makespan com base nas sequências finais (garante consistência)
        cargas_finais = {}
        for m in machines:
            cargas_finais[m] = tempo_seq_na_maquina(m, maquinas_jobs[m])

        final_makespan = max(cargas_finais.values()) if cargas_finais else 0.0

        return {"schedule": schedule_list, "makespan": float(final_makespan)}

    # -------------------------
    # Método público: dispatcher
    # -------------------------
    def decoder(self, keys: np.ndarray) -> dict:
        """
        Método público exigido pela interface: NÃO alterar a assinatura.
        Faz o despacho ao decoder escolhido em self.decoder_name.
        """
        dec = self.decoder_name.lower()
        dispatch = {
            "ect": self._decode_ect,
            "ksts": self._decode_ksts,
            "m3law": self._decoder_m3law,
            "incremental": self._decoder_incremental,
            "cheapest": self._decode_cheapest_insertion,
            # mapeie outros nomes aqui quando implementar:
            # "2n": self._decode_2n,
            # "incremental": self._decode_incremental,
            # "m3law": self._decode_m3law,
        }
        # pega função, default para ECT se decoder desconhecido
        func = dispatch.get(dec, self._decode_ect)
        return func(keys)

    # -------------------------
    # restante da classe (cost, convert_schedule_to_gantt_format, etc.)
    # -------------------------
    def cost(self, solution: dict, final_solution: bool = False) -> float:
        return solution["makespan"]

    def convert_schedule_to_gantt_format(self, decoded_solution: dict) -> (dict, dict):
        schedule = decoded_solution["schedule"]
        X = {}
        C = {}
        for machine_idx, job_list in enumerate(schedule):
            machine = machine_idx + 1
            current_time = 0
            last_job = 0
            for job in job_list:
                setup = self.dados["S"].get((machine, last_job, job), 0)
                proc_time = self.dados["p"].get((machine, job), 0)
                current_time += setup + proc_time
                C[(machine, job)] = current_time
                X[(machine, last_job, job)] = 1
                last_job = job
        return X, C



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RKO Solver for UPMSP-SDS")
    parser.add_argument("--input", required=True, type=str, help="Caminho para o arquivo da instância.")
    parser.add_argument("--time", type=int, default=60, help="Tempo limite de execução em segundos.")
    parser.add_argument("--gantt", type=str, default=None, help="Nome base para o arquivo do gráfico de Gantt (sem extensão).")
    # NOVO: Argumento para o arquivo de resultados
    parser.add_argument("--output", type=str, default=None, help="Arquivo de saída para registrar os resultados.")
    # NOVO: argumento para escolher o decoder usado para decodificar chaves geradas pelo solver
    parser.add_argument("--decoder", type=str, default="ect", help="Decoder a ser usado: ect (default), ksts, 2n, 2n*, ...")
    args = parser.parse_args()

    # 1. Instancia o ambiente do problema, passando o decoder escolhido
    env = UPMSPSDSProblem(instance_path=args.input, decoder=args.decoder)

    # 2. Instancia o solver RKO
    solver = RKO(
        env=env, 
        print_best=True
    )
    
    # --- Inicia a contagem de tempo ---
    start_time = time.time()

    # 3. Executa o solver
    # Define aqui a configuração de meta-heurísticas paralelas
    final_cost, final_solution_keys, time_to_best = solver.solve(
        time_total=args.time, 
        runs=1,
        brkga=1, 
        lns=1, 
        vns=1, 
        ils=1, 
        sa=1, 
        pso=1, 
        ga=1
    )
    
    # --- Finaliza a contagem de tempo ---
    total_runtime = time.time() - start_time

    # 4. Decodifica a melhor solução encontrada para obter o cronograma
    final_schedule = env.decoder(final_solution_keys)

    # 5. NOVO: Salva os resultados em arquivo, se solicitado
    if args.output:
        print(f"\nSalvando resultado no arquivo: {args.output}")
        
        # Cria uma string descritiva dos parâmetros
        params_str = ''
        params_str += f"brkga:p={env.BRKGA_parameters['p']}|"
        params_str += f"brkga:pe={env.BRKGA_parameters['pe']}|"
        params_str += f"brkga:pm={env.BRKGA_parameters['pm']}|"
        params_str += f"brkga:rhoe={env.BRKGA_parameters['rhoe']}|"
        
        params_str += f"sa:SAmax={env.SA_parameters['SAmax']}|"
        params_str += f"sa:alphaSA={env.SA_parameters['alphaSA']}|"
        params_str += f"sa:betaMin={env.SA_parameters['betaMin']}|"
        params_str += f"sa:betaMax={env.SA_parameters['betaMax']}|"
        params_str += f"sa:T0={env.SA_parameters['T0']}|"

        params_str += f"ILS:betaMin={env.ILS_parameters['betaMin']}|"
        params_str += f"ILS:betaMax={env.ILS_parameters['betaMax']}|"

        params_str += f"VNS:kMax={env.VNS_parameters['kMax']}|"
        params_str += f"VNS:betaMin={env.VNS_parameters['betaMin']}|"

        params_str += f"PSO:PSize={env.PSO_parameters['PSize']}|"
        params_str += f"PSO:c1={env.PSO_PARAMETERS['c1'] if 'PSO_PARAMETERS' in dir(env) else env.PSO_parameters['c1']}|"
        params_str += f"PSO:c2={env.PSO_PARAMETERS['c2'] if 'PSO_PARAMETERS' in dir(env) else env.PSO_parameters['c2']}|"
        params_str += f"PSO:w={env.PSO_PARAMETERS['w'] if 'PSO_PARAMETERS' in dir(env) else env.PSO_parameters['w']}|"

        params_str += f"GA:sizePop={env.GA_parameters['sizePop']}|"
        params_str += f"GA:probCros={env.GA_parameters['probCros']}|"
        params_str += f"GA:probMut={env.GA_parameters['probMut']}|"

        params_str += f"LNS:betaMin={env.LNS_parameters['betaMin']}|"
        params_str += f"LNS:betaMax={env.LNS_parameters['betaMax']}|"
        params_str += f"LNS:TO={env.LNS_parameters['TO']}|"
        params_str += f"LNS:alphaLNS={env.LNS_parameters['alphaLNS']}|"

        params_str += f"decoder={env.decoder_name.upper()}"
        
        output_writer.salvar_resultado(
            arquivo_saida=args.output,
            instancia=env.instance_name,
            modelo="RKO",
            objetivo=final_cost,
            lowerbound=None, # RKO não calcula lowerbound
            gap=None,
            runtime=total_runtime,
            constraints=0, # Não aplicável para meta-heurísticas
            variables=0,   # Não aplicável para meta-heurísticas
            parameters=params_str,
            jobs=len(env.dados["N"]),
            machines=len(env.dados["M"]),
            status="TimeLimit" 
        )
        print("Resultado salvo.")

    # 6. Gera o gráfico de Gantt se solicitado
    if args.gantt:
        print(f"\nGerando Gráfico de Gantt como '{args.gantt}-RKO-{env.decoder_name.upper()}.png'...")
        X, C = env.convert_schedule_to_gantt_format(final_schedule)
        output_writer.gantt_chart(
            M=env.dados["M"], N=env.dados["N"], N0=env.dados["N0"],
            p=env.dados["p"], s=env.dados["S"], X=X, C=C,
            arq_gantt=args.gantt, instancia=env.instance_name,
            makespan=final_cost, str_metodo=f"RKO-{env.decoder_name.upper()}"
        )
        print("Gráfico de Gantt salvo.")

    # 7. Exibe os resultados finais
    print("\n" + "="*30)
    print("      RESULTADOS FINAIS      ")
    print("="*30)
    print(f"Decoder escolhido: {env.decoder_name}")
    print(f"Instância: {env.instance_name}")
    print(f"Melhor Makespan Encontrado: {final_cost:.4f}")
    print(f"Tempo para Melhor Solução: {time_to_best:.2f}s")
    print(f"Tempo Total de Execução: {total_runtime:.2f}s")
    print("Cronograma por Máquina:")
    for i, machine_schedule in enumerate(final_schedule["schedule"]):
        print(f"  Máquina {i+1}: {machine_schedule}")
