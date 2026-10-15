# solver-rko-roberto.py
import numpy as np
import os
import sys
import argparse
import time
import random
from types import SimpleNamespace

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from metaheuristics.rkolib.RKO import RKO
from metaheuristics.rkolib.Environment import RKOEnvAbstract, check_env
import input_output.input_reader as input_reader
import input_output.output_writer as output_writer

class UPMSPSDSProblem(RKOEnvAbstract):
    def __init__(self, instance_path: str, decoder: str = "ect"):
        super().__init__()
        print(f"Carregando instância do UPMSP-SDS de: {instance_path}")

        self.dados = self._load_data(instance_path)
        self.decoder_name = (decoder or "ect").lower()
        self.instance_name = os.path.basename(instance_path)

        n_jobs = len(self.dados.get("N", []))
        m_machines = len(self.dados.get("M", []))
        
        if self.decoder_name in ("ksts", "2n", "2n*", "cheapest"):
            self.tam_solution = 2 * n_jobs
        elif self.decoder_name == "eroglu":
            self.tam_solution = n_jobs * m_machines
        elif self.decoder_name in ("roberto", "wgci"):
            self.tam_solution = n_jobs + 1
        else:
            self.tam_solution = n_jobs

        self.LS_type: str = 'Best'
        self.dict_best: dict = {}
        self.save_q_learning_report = False

        self.BRKGA_parameters = {'p': [100], 'pe': [0.20], 'pm': [0.10], 'rhoe': [0.70]}
        self.SA_parameters = {'SAmax': [50], 'alphaSA': [0.99], 'betaMin': [0.05], 'betaMax': [0.25], 'T0': [10000]}
        self.ILS_parameters = {'betaMin': [0.10, 0.2], 'betaMax': [0.20, 0.3]}
        self.VNS_parameters = {'kMax': [5, 3], 'betaMin': [0.05, 0.1]}
        self.PSO_parameters = {'PSize': [100], 'c1': [2.05], 'c2': [2.05], 'w': [0.73]}
        self.GA_parameters = {'sizePop': [100], 'probCros': [0.98], 'probMut': [0.005]}
        self.LNS_parameters = {'betaMin': [0.10], 'betaMax': [0.30], 'TO': [1000], 'alphaLNS': [0.95]}

    def _load_data(self, instance_path: str):
        mock_args = SimpleNamespace(nome_instancia=instance_path)
        return input_reader.le_arquivo(mock_args)

    def _decode_roberto(self, keys) -> dict:
        """
        Decodificador Windowed GCI baseado em Roberto et al. (2025) 
        adaptado para minimização de makespan no UPMSP-SDS.
        """
        is_list = isinstance(keys, list)
        keys_np = np.array(keys) if is_list else keys

        num_jobs = len(self.dados["N"])
        machines = list(self.dados["M"])

        expected_len = num_jobs + 1
        if len(keys_np) < expected_len:
            keys_np = np.resize(keys_np, expected_len)

        priority_keys = keys_np[:num_jobs]
        w_key = float(keys_np[num_jobs])

        # Mapeia a última chave para definir o tamanho da janela W em [1, num_jobs]
        W = max(1, min(num_jobs, int(np.floor(w_key * num_jobs)) + 1))

        # Ordena os jobs pelas chaves de prioridade
        jobs_pendentes = [int(idx) + 1 for idx in np.argsort(priority_keys)]

        maquinas_jobs = {m: [] for m in machines}
        carga_maquinas = {m: 0.0 for m in machines}

        S = self.dados["S"]
        p = self.dados["p"]

        while jobs_pendentes:
            janela = jobs_pendentes[:W]

            melhor_job = None
            melhor_m = None
            melhor_pos = -1
            menor_criterio = (float('inf'), float('inf'))
            melhor_delta = 0.0

            for job in janela:
                for m in machines:
                    seq = maquinas_jobs[m]
                    len_seq = len(seq)
                    proc_time = float(p.get((m, job), 0.0))

                    for pos in range(len_seq + 1):
                        prev_job = 0 if pos == 0 else seq[pos - 1]
                        next_job = None if pos == len_seq else seq[pos]

                        s_prev_job = float(S.get((m, prev_job, job), 0.0))

                        if next_job is not None:
                            s_job_next = float(S.get((m, job, next_job), 0.0))
                            s_prev_next = float(S.get((m, prev_job, next_job), 0.0))
                            delta = s_prev_job + proc_time + s_job_next - s_prev_next
                        else:
                            delta = s_prev_job + proc_time

                        novo_ct = carga_maquinas[m] + delta
                        
                        # Minimiza o tempo de conclusão resultante na máquina, desempatando pelo menor delta
                        criterio_atual = (novo_ct, delta)

                        if criterio_atual < menor_criterio:
                            menor_criterio = criterio_atual
                            melhor_job = job
                            melhor_m = m
                            melhor_pos = pos
                            melhor_delta = delta

            maquinas_jobs[melhor_m].insert(melhor_pos, melhor_job)
            carga_maquinas[melhor_m] += melhor_delta
            jobs_pendentes.remove(melhor_job)

        schedule_list = [maquinas_jobs[m] for m in machines]
        final_makespan = max(carga_maquinas.values()) if carga_maquinas else 0.0

        return {"schedule": schedule_list, "makespan": float(final_makespan)}

    def _decode_eroglu(self, keys) -> dict:
        """
        Decodificador fiel ao Appendix 1 de Eroglu et al. (2014) - GALA.
        """
        is_list = isinstance(keys, list)
        keys_np = np.array(keys) if is_list else keys

        num_jobs = len(self.dados["N"])
        num_machines = len(self.dados["M"])

        expected_len = num_jobs * num_machines
        if len(keys_np) < expected_len:
            keys_np = np.resize(keys_np, expected_len)
        
        # Mapeia vetor para Matriz N x M
        K = keys_np.reshape((num_jobs, num_machines)).copy()
        machine_schedules = [[] for _ in range(num_machines)]
        
        # Decodificação inicial: para cada job, escolhe a máquina com a menor chave
        for j_idx in range(num_jobs):
            best_m_idx = int(np.argmin(K[j_idx, :]))
            machine_schedules[best_m_idx].append(j_idx + 1)
            
        # O sequenciamento na máquina obedece a ordem crescente das chaves
        for m_idx in range(num_machines):
            machine_schedules[m_idx].sort(key=lambda job: K[job - 1, m_idx])
            
        # Criação da estrutura Gene detalhada no Appendix 1
        Gene = []
        for m_idx in range(num_machines):
            for job in machine_schedules[m_idx]:
                Gene.append({'Machine': m_idx + 1, 'Job': job})
                
        g = len(Gene)
        
        CT_Machine = {}
        for m_idx in range(num_machines):
            m_id = m_idx + 1
            c = 0.0
            last_job = 0
            for job in machine_schedules[m_idx]:
                c += self.dados["S"].get((m_id, last_job, job), 0.0) + self.dados["p"].get((m_id, job), 0.0)
                last_job = job
            CT_Machine[m_id] = c

        # =========================================================
        # BUSCA LOCAL IDÊNTICA AO APPENDIX 1 (Eroglu et al., 2014)
        # =========================================================
        for i in range(g):
            for j in range(i + 1, g):
                m_id_i = Gene[i]['Machine']
                m_id_j = Gene[j]['Machine']
                
                # (A)(a) Interchange of jobs (Same Machine)
                if m_id_i == m_id_j:
                    m_id = m_id_i
                    job_i = Gene[i]['Job']
                    job_j = Gene[j]['Job']
                    
                    # (i) Adjacent jobs interchange
                    if j == i + 1:
                        a = 0.0; b = 0.0; c = 0.0
                        if i > 0 and Gene[i-1]['Machine'] == m_id:
                            job_prev = Gene[i-1]['Job']
                            a = (self.dados["S"].get((m_id, job_prev, job_j), 0.0) - self.dados["S"].get((m_id, job_prev, job_i), 0.0)) + \
                                (self.dados["S"].get((m_id, job_j, job_i), 0.0) - self.dados["S"].get((m_id, job_i, job_j), 0.0))
                        if i == 0 or Gene[i-1]['Machine'] != m_id:
                            b = (self.dados["S"].get((m_id, 0, job_j), 0.0) - self.dados["S"].get((m_id, 0, job_i), 0.0)) + \
                                (self.dados["S"].get((m_id, job_j, job_i), 0.0) - self.dados["S"].get((m_id, job_i, job_j), 0.0))
                        if j < g - 1 and Gene[j+1]['Machine'] == m_id:
                            job_next = Gene[j+1]['Job']
                            c = self.dados["S"].get((m_id, job_i, job_next), 0.0) - self.dados["S"].get((m_id, job_j, job_next), 0.0)
                            
                        if a + b + c < 0:
                            Gene[i]['Job'], Gene[j]['Job'] = Gene[j]['Job'], Gene[i]['Job']
                            CT_Machine[m_id] += (a + b + c)
                            
                            # (B)(i) Calibrate random numbers (Interchange)
                            idx_i, idx_j = job_i - 1, job_j - 1
                            K[idx_i, m_id-1], K[idx_j, m_id-1] = K[idx_j, m_id-1], K[idx_i, m_id-1]
                            
                            active_key = K[idx_i, m_id-1]
                            for m_cal in range(num_machines):
                                if m_cal != m_id-1 and K[idx_i, m_cal] <= active_key:
                                    K[idx_i, m_cal] = random.uniform(active_key + 1e-5, 1.0)
                                    
                            active_key = K[idx_j, m_id-1]
                            for m_cal in range(num_machines):
                                if m_cal != m_id-1 and K[idx_j, m_cal] <= active_key:
                                    K[idx_j, m_cal] = random.uniform(active_key + 1e-5, 1.0)
                                    
                    # (ii) Non-adjacent jobs interchange
                    elif j > i + 1:
                        a = 0.0; b = 0.0; c = 0.0
                        job_i_next = Gene[i+1]['Job']
                        
                        if i > 0 and Gene[i-1]['Machine'] == m_id:
                            job_prev = Gene[i-1]['Job']
                            a = (self.dados["S"].get((m_id, job_prev, job_j), 0.0) - self.dados["S"].get((m_id, job_prev, job_i), 0.0)) + \
                                (self.dados["S"].get((m_id, job_j, job_i_next), 0.0) - self.dados["S"].get((m_id, job_i, job_i_next), 0.0))
                        if i == 0 or Gene[i-1]['Machine'] != m_id:
                            b = (self.dados["S"].get((m_id, 0, job_j), 0.0) - self.dados["S"].get((m_id, 0, job_i), 0.0)) + \
                                (self.dados["S"].get((m_id, job_j, job_i_next), 0.0) - self.dados["S"].get((m_id, job_i, job_i_next), 0.0))
                        
                        job_j_prev = Gene[j-1]['Job']
                        if j < g - 1 and Gene[j+1]['Machine'] == m_id:
                            job_next = Gene[j+1]['Job']
                            c = (self.dados["S"].get((m_id, job_j_prev, job_i), 0.0) - self.dados["S"].get((m_id, job_j_prev, job_j), 0.0)) + \
                                (self.dados["S"].get((m_id, job_i, job_next), 0.0) - self.dados["S"].get((m_id, job_j, job_next), 0.0))
                        else:
                            c = (self.dados["S"].get((m_id, job_j_prev, job_i), 0.0) - self.dados["S"].get((m_id, job_j_prev, job_j), 0.0))
                            
                        if a + b + c < 0:
                            Gene[i]['Job'], Gene[j]['Job'] = Gene[j]['Job'], Gene[i]['Job']
                            CT_Machine[m_id] += (a + b + c)
                            
                            # (B)(i) Calibrate random numbers (Interchange)
                            idx_i, idx_j = job_i - 1, job_j - 1
                            K[idx_i, m_id-1], K[idx_j, m_id-1] = K[idx_j, m_id-1], K[idx_i, m_id-1]
                            
                            active_key = K[idx_i, m_id-1]
                            for m_cal in range(num_machines):
                                if m_cal != m_id-1 and K[idx_i, m_cal] <= active_key:
                                    K[idx_i, m_cal] = random.uniform(active_key + 1e-5, 1.0)
                                    
                            active_key = K[idx_j, m_id-1]
                            for m_cal in range(num_machines):
                                if m_cal != m_id-1 and K[idx_j, m_cal] <= active_key:
                                    K[idx_j, m_cal] = random.uniform(active_key + 1e-5, 1.0)
                                    
                # (A)(b) Intra-machine exchanging (Different Machines)
                elif m_id_i != m_id_j:
                    m_i = m_id_i
                    m_j = m_id_j
                    job_i = Gene[i]['Job']
                    job_j = Gene[j]['Job']
                    
                    a = 0.0; a1 = 0.0; a2 = 0.0
                    b = 0.0; b1 = 0.0; b2 = 0.0
                    MakespanD1 = 0.0; MakespanD2 = 0.0
                    
                    a = CT_Machine[m_i] + self.dados["p"].get((m_i, job_j), 0.0) - self.dados["p"].get((m_i, job_i), 0.0)
                    if i > 0 and Gene[i-1]['Machine'] == m_i:
                        job_prev = Gene[i-1]['Job']
                        a1 = self.dados["S"].get((m_i, job_prev, job_j), 0.0) - self.dados["S"].get((m_i, job_prev, job_i), 0.0)
                    if i == 0 or Gene[i-1]['Machine'] != m_i:
                        a1 = self.dados["S"].get((m_i, 0, job_j), 0.0) - self.dados["S"].get((m_i, 0, job_i), 0.0)
                    if i < g - 1 and Gene[i+1]['Machine'] == m_i:
                        job_next = Gene[i+1]['Job']
                        a2 = self.dados["S"].get((m_i, job_j, job_next), 0.0) - self.dados["S"].get((m_i, job_i, job_next), 0.0)
                        
                    b = CT_Machine[m_j] + self.dados["p"].get((m_j, job_i), 0.0) - self.dados["p"].get((m_j, job_j), 0.0)
                    if j > 0 and Gene[j-1]['Machine'] == m_j:
                        job_prev = Gene[j-1]['Job']
                        b1 = self.dados["S"].get((m_j, job_prev, job_i), 0.0) - self.dados["S"].get((m_j, job_prev, job_j), 0.0)
                    if j == 0 or Gene[j-1]['Machine'] != m_j:
                        b1 = self.dados["S"].get((m_j, 0, job_i), 0.0) - self.dados["S"].get((m_j, 0, job_j), 0.0)
                    if j < g - 1 and Gene[j+1]['Machine'] == m_j:
                        job_next = Gene[j+1]['Job']
                        b2 = self.dados["S"].get((m_j, job_i, job_next), 0.0) - self.dados["S"].get((m_j, job_j, job_next), 0.0)
                        
                    a = a + a1 + a2
                    b = b + b1 + b2
                    MakespanD1 = max(CT_Machine[m_i], CT_Machine[m_j])
                    MakespanD2 = max(a, b)
                    
                    if MakespanD2 < MakespanD1:
                        Gene[i]['Job'], Gene[j]['Job'] = Gene[j]['Job'], Gene[i]['Job']
                        CT_Machine[m_i] = a
                        CT_Machine[m_j] = b
                        
                        # (B)(ii) Calibrate random numbers (Exchange)
                        idx_i, idx_j = job_i - 1, job_j - 1
                        
                        temp_i_mi = K[idx_i, m_i-1]
                        temp_i_mj = K[idx_i, m_j-1]
                        temp_j_mi = K[idx_j, m_i-1]
                        temp_j_mj = K[idx_j, m_j-1]
                        
                        K[idx_i, m_j-1] = temp_j_mj
                        K[idx_j, m_i-1] = temp_i_mi
                        K[idx_i, m_i-1] = temp_j_mi
                        K[idx_j, m_j-1] = temp_i_mj
                        
                        active_key = K[idx_i, m_j-1]
                        for m_cal in range(num_machines):
                            if m_cal != m_j-1 and K[idx_i, m_cal] <= active_key:
                                K[idx_i, m_cal] = random.uniform(active_key + 1e-5, 1.0)
                                
                        active_key = K[idx_j, m_i-1]
                        for m_cal in range(num_machines):
                            if m_cal != m_i-1 and K[idx_j, m_cal] <= active_key:
                                K[idx_j, m_cal] = random.uniform(active_key + 1e-5, 1.0)

        # Transfere as modificações do array K calibrado de volta para as chaves nativas do RKO
        flat_K = K.flatten()
        if is_list:
            keys[:] = flat_K[:len(keys)].tolist()
        else:
            keys[:] = flat_K[:len(keys)]
            
        # Reconstrução final do cronograma formatado a partir da estrutura Gene
        machine_schedules_final = [[] for _ in range(num_machines)]
        for gene in Gene:
            machine_schedules_final[gene['Machine'] - 1].append(gene['Job'])

        makespan = float(np.max(list(CT_Machine.values()))) if CT_Machine else 0.0
        return {"schedule": machine_schedules_final, "makespan": makespan}

    def _decode_ect(self, keys: np.ndarray) -> dict:
        num_jobs = len(self.dados["N"])
        num_machines = len(self.dados["M"])

        job_sequence = np.argsort(keys)[:num_jobs]  

        machine_schedules = [[] for _ in range(num_machines)]
        machine_completion_times = np.zeros(num_machines)

        for job_idx in job_sequence:
            job = int(job_idx) + 1  
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
        num_jobs = len(self.dados["N"])
        num_machines = len(self.dados["M"])

        if len(keys) < 2 * num_jobs:
            keys = np.resize(keys, 2 * num_jobs)

        priority_keys = keys[:num_jobs]
        roulette_keys = keys[num_jobs:2 * num_jobs]

        jobs_ordered = list(np.argsort(priority_keys))[:num_jobs]

        machine_schedules = [[] for _ in range(num_machines)]
        machine_completion_times = np.zeros(num_machines)
        cargas = np.zeros(num_machines)  

        epsilon = 1e-9

        def calc_threshold(machine_idx: int, last_job: int) -> float:
            machine_id = machine_idx + 1
            vals = []
            for j in self.dados["N"]:
                if j == last_job:
                    continue
                vals.append(self.dados["S"].get((machine_id, last_job, j), 0))
            return float(sum(vals) / len(vals)) if vals else 0.0

        for idx in jobs_ordered:
            job = int(idx) + 1

            weights = [1.0 / (epsilon + c) for c in cargas]
            total_w = sum(weights)
            probs = [w / total_w for w in weights] if total_w > 0 else [1.0 / num_machines] * num_machines
            cumul = np.cumsum(probs)

            r = float(roulette_keys[int(idx)] % 1.0)
            mk_roleta_idx = int(np.searchsorted(cumul, r, side='right'))
            if mk_roleta_idx >= num_machines:
                mk_roleta_idx = num_machines - 1

            candidatas = []  
            for m_idx in range(num_machines):
                if not machine_schedules[m_idx]:
                    candidatas.append((m_idx, 0.0))
                else:
                    last_job = machine_schedules[m_idx][-1]
                    s_val = float(self.dados["S"].get((m_idx + 1, last_job, job), 0))
                    T_k = calc_threshold(m_idx, last_job)
                    if s_val <= T_k:
                        candidatas.append((m_idx, s_val))

            if candidatas:
                best_m_idx, best_s = min(candidatas, key=lambda x: x[1])
            else:
                best_m_idx = mk_roleta_idx
                last_job = machine_schedules[best_m_idx][-1] if machine_schedules[best_m_idx] else 0
                best_s = float(self.dados["S"].get((best_m_idx + 1, last_job, job), 0))

            proc_time = float(self.dados["p"].get((best_m_idx + 1, job), 0.0))
            machine_schedules[best_m_idx].append(job)
            machine_completion_times[best_m_idx] += best_s + proc_time
            cargas[best_m_idx] += proc_time

        makespan = float(np.max(machine_completion_times)) if machine_completion_times.size > 0 else 0.0
        return {"schedule": machine_schedules, "makespan": makespan}

    def _decoder_m3law(self, keys: np.ndarray) -> dict:
        num_jobs = len(self.dados["N"])
        num_machines = len(self.dados["M"])
        
        WINDOW_SIZE = 3

        jobs_ordenados = [idx + 1 for idx in np.argsort(keys)]
        jobs_pendentes = list(jobs_ordenados)

        machine_schedules = [[] for _ in range(num_machines)]
        machine_completion_times = np.zeros(num_machines)
        last_job_on_machine = [0] * num_machines 

        while jobs_pendentes:
            janela = jobs_pendentes[:WINDOW_SIZE]
            
            melhor_job = None
            melhor_maquina_idx = -1
            menor_tempo_termino_global = float('inf')

            for job_candidato in janela:
                for machine_idx in range(num_machines):
                    machine = machine_idx + 1
                    ultimo_job = last_job_on_machine[machine_idx]
                    
                    setup_time = self.dados["S"].get((machine, ultimo_job, job_candidato), 0)
                    processing_time = self.dados["p"].get((machine, job_candidato), float('inf'))
                    
                    completion_time = machine_completion_times[machine_idx] + setup_time + processing_time

                    if completion_time < menor_tempo_termino_global:
                        menor_tempo_termino_global = completion_time
                        melhor_maquina_idx = machine_idx
                        melhor_job = job_candidato

            if melhor_job is not None:
                machine_schedules[melhor_maquina_idx].append(melhor_job)
                machine_completion_times[melhor_maquina_idx] = menor_tempo_termino_global
                last_job_on_machine[melhor_maquina_idx] = melhor_job
                jobs_pendentes.remove(melhor_job)
            else:
                job_forcado = jobs_pendentes.pop(0)
                machine_schedules[0].append(job_forcado)

        makespan = np.max(machine_completion_times)
        return {"schedule": machine_schedules, "makespan": makespan}

    def _decoder_incremental(self, keys: np.ndarray) -> dict:
        n_jobs = len(self.dados["N"])
        copia = keys 

        jobs_ordenados = sorted(range(1, n_jobs + 1), key=lambda j: copia[j - 1])
        maquinas_jobs = {m: [] for m in self.dados["M"]}
        
        for job in jobs_ordenados:
            melhor_maquina = None
            menor_aumento_makespan = float('inf')
            
            for maquina in self.dados["M"]:
                temp_maquinas = {m: list(maquinas_jobs[m]) for m in self.dados["M"]}
                temp_maquinas[maquina].append(job)
                
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

                aumento_makespan = makespan_temp - makespan_atual
                
                if aumento_makespan < menor_aumento_makespan:
                    menor_aumento_makespan = aumento_makespan
                    melhor_maquina = maquina

            maquinas_jobs[melhor_maquina].append(job)

        schedule_list = [maquinas_jobs[m] for m in sorted(self.dados["M"])]
        
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
        num_jobs = len(self.dados["N"])
        machines = list(self.dados["M"])  
        num_machines = len(machines)

        if len(keys) < 2 * num_jobs:
            keys = np.resize(keys, 2 * num_jobs)

        genes_ordem = keys[:num_jobs]
        genes_escolha = keys[num_jobs:2 * num_jobs]

        jobs_ordenados = sorted(range(1, num_jobs + 1), key=lambda j: genes_ordem[j - 1])

        maquinas_jobs = {m: [] for m in machines}
        carga_maquinas = {m: 0.0 for m in machines}

        def tempo_seq_na_maquina(m: int, seq: list) -> float:
            t = 0.0
            anterior = 0
            for j in seq:
                t += float(self.dados["S"].get((m, anterior, j), 0))
                t += float(self.dados["p"].get((m, j), 0))
                anterior = j
            return t

        for job in jobs_ordenados:
            ranking_opcoes = []  

            for m in machines:
                sequencia_atual = maquinas_jobs[m]
                melhor_pos_m = 0
                menor_incremento_m = float('inf')

                for pos in range(len(sequencia_atual) + 1):
                    nova_seq = sequencia_atual[:pos] + [job] + sequencia_atual[pos:]
                    tempo_novo = tempo_seq_na_maquina(m, nova_seq)
                    incremento = tempo_novo - carga_maquinas[m]

                    if incremento < menor_incremento_m:
                        menor_incremento_m = incremento
                        melhor_pos_m = pos

                makespan_projetado = carga_maquinas[m] + menor_incremento_m
                ranking_opcoes.append((makespan_projetado, m, melhor_pos_m, menor_incremento_m))

            ranking_opcoes.sort(key=lambda x: x[0])

            gene_val = float(genes_escolha[job - 1])
            bias = 10.0
            idx_escolhido = int(len(ranking_opcoes) * (gene_val ** bias))
            if idx_escolhido >= len(ranking_opcoes):
                idx_escolhido = len(ranking_opcoes) - 1

            _, maquina_selecionada, pos_escolhida, custo_escolhido = ranking_opcoes[idx_escolhido]

            maquinas_jobs[maquina_selecionada].insert(pos_escolhida, job)
            carga_maquinas[maquina_selecionada] += custo_escolhido

        maquina_critica = max(carga_maquinas, key=carga_maquinas.get)
        makespan_atual = carga_maquinas[maquina_critica]

        if len(maquinas_jobs[maquina_critica]) > 0:
            job_problematico = maquinas_jobs[maquina_critica][-1]
            seq_critica_sem = maquinas_jobs[maquina_critica][:-1]
            custo_critica_sem_job = tempo_seq_na_maquina(maquina_critica, seq_critica_sem)

            melhor_movimento = None
            menor_makespan_encontrado = makespan_atual

            for m_dest in machines:
                if m_dest == maquina_critica:
                    continue

                seq_dest = maquinas_jobs[m_dest]
                for pos in range(len(seq_dest) + 1):
                    nova_seq = seq_dest[:pos] + [job_problematico] + seq_dest[pos:]
                    custo_dest = tempo_seq_na_maquina(m_dest, nova_seq)

                    novo_pico = max(custo_critica_sem_job, custo_dest)

                    if novo_pico < menor_makespan_encontrado:
                        menor_makespan_encontrado = novo_pico
                        melhor_movimento = (m_dest, pos, custo_dest, custo_critica_sem_job)

            if melhor_movimento:
                m_dest, pos_dest, novo_custo_dest, custo_critica_sem = melhor_movimento
                maquinas_jobs[maquina_critica].pop()
                maquinas_jobs[m_dest].insert(pos_dest, job_problematico)

        schedule_list = [maquinas_jobs[m] for m in machines]

        cargas_finais = {}
        for m in machines:
            cargas_finais[m] = tempo_seq_na_maquina(m, maquinas_jobs[m])

        final_makespan = max(cargas_finais.values()) if cargas_finais else 0.0

        return {"schedule": schedule_list, "makespan": float(final_makespan)}

    def decoder(self, keys) -> dict:
        dec = self.decoder_name.lower()
        dispatch = {
            "ect": self._decode_ect,
            "ksts": self._decode_ksts,
            "m3law": self._decoder_m3law,
            "incremental": self._decoder_incremental,
            "cheapest": self._decode_cheapest_insertion,
            "eroglu": self._decode_eroglu,
            "roberto": self._decode_roberto,
            "wgci": self._decode_roberto,
        }
        func = dispatch.get(dec, self._decode_ect)
        return func(keys)

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
    parser.add_argument("--output", type=str, default=None, help="Arquivo de saída para registrar os resultados.")
    parser.add_argument("--decoder", type=str, default="ect", help="Decoder a ser usado: ect (default), m3law, cheapest, eroglu, roberto...")
    args = parser.parse_args()

    env = UPMSPSDSProblem(instance_path=args.input, decoder=args.decoder)

    solver = RKO(env=env, print_best=True)
    
    start_time = time.time()

    final_cost, final_solution_keys, time_to_best = solver.solve(
        time_total=args.time, runs=1, brkga=1, lns=1, vns=1, ils=1, sa=1, pso=1, ga=1
    )
    
    total_runtime = time.time() - start_time

    final_schedule = env.decoder(final_solution_keys)

    if args.output:
        print(f"\nSalvando resultado no arquivo: {args.output}")
        params_str = ''
        params_str += f"brkga:p={env.BRKGA_parameters['p']}|pe={env.BRKGA_parameters['pe']}|pm={env.BRKGA_parameters['pm']}|rhoe={env.BRKGA_parameters['rhoe']}|"
        params_str += f"sa:SAmax={env.SA_parameters['SAmax']}|alphaSA={env.SA_parameters['alphaSA']}|betaMin={env.SA_parameters['betaMin']}|betaMax={env.SA_parameters['betaMax']}|T0={env.SA_parameters['T0']}|"
        params_str += f"ILS:betaMin={env.ILS_parameters['betaMin']}|betaMax={env.ILS_parameters['betaMax']}|"
        params_str += f"VNS:kMax={env.VNS_parameters['kMax']}|betaMin={env.VNS_parameters['betaMin']}|"
        params_str += f"PSO:PSize={env.PSO_parameters['PSize']}|c1={env.PSO_parameters.get('c1', [2.05])}|c2={env.PSO_parameters.get('c2', [2.05])}|w={env.PSO_parameters.get('w', [0.73])}|"
        params_str += f"GA:sizePop={env.GA_parameters['sizePop']}|probCros={env.GA_parameters['probCros']}|probMut={env.GA_parameters['probMut']}|"
        params_str += f"LNS:betaMin={env.LNS_parameters['betaMin']}|betaMax={env.LNS_parameters['betaMax']}|TO={env.LNS_parameters['TO']}|alphaLNS={env.LNS_parameters['alphaLNS']}|"
        params_str += f"decoder={env.decoder_name.upper()}"
        
        output_writer.salvar_resultado(
            arquivo_saida=args.output,
            instancia=env.instance_name,
            objetivo=final_cost,
            modelo="RKO",
            lowerbound=None,
            gap=None,
            runtime=total_runtime,
            constraints=0,
            variables=0,
            parameters=params_str,
            jobs=len(env.dados["N"]),
            machines=len(env.dados["M"]),
            status="TimeLimit" 
        )
        print("Resultado salvo.")

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
