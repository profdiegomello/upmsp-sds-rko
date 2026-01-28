import numpy as np
import os
import sys
from types import SimpleNamespace

# Garante compatibilidade de imports como no arquivo original
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import backend.rko_dependencies.input_output.input_reader as input_reader

class UPMSPSDSProblem:
    """
    Ambiente do UPMSP-SDS para o framework RKO.
    Cada decoder tem seu próprio método: _decode_ect, _decode_ksts, ...
    O método público `decoder(keys)` apenas faz o despacho para o decoder
    selecionado em self.decoder_name.
    """
    def __init__(self, instance_path: str, decoder: str = "ect", time_limit: int = 120):
        # atributos basicos
        self.max_time = time_limit
        self.melhor_local = float('inf')
        self.dados = self._load_data(instance_path)
        self.decoder_name = (decoder or "ect").lower()
        self.instance_name = os.path.basename(instance_path)

        # determina tam_solution conforme decoder
        n_jobs = len(self.dados.get("N", []))
        if self.decoder_name == "ksts":
            self.tam_solution = 2 * n_jobs
        elif self.decoder_name in ("2n", "2n*"):
            self.tam_solution = 2 * n_jobs
        elif self.decoder_name == "m3law" or self.decoder_name == "M3LAW":
            self.tam_solution = n_jobs
        elif self.decoder_name == "incremental" or self.decoder_name == "INCREMENTAL":
            self.tam_solution = n_jobs
        elif self.decoder_name == "cheapest" or self.decoder_name == "CHEAPEST":
            self.tam_solution = 2 * n_jobs
        else:
            self.tam_solution = n_jobs

        # placeholders / parametros padrão
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

        self.ui_callback = None

    def _load_data(self, instance_path: str):
        """Carrega instância usando input_reader (interface antiga usada no projeto)."""
        mock_args = SimpleNamespace(nome_instancia=instance_path)
        return input_reader.le_arquivo(mock_args)

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
        """
        KSTS (2N genes): primeiras N = prioridades; últimas N = chaves da roleta
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
        machine_completion_times = np.zeros(num_machines)  # CT[m]: proc + setups
        cargas_proc = np.zeros(num_machines)               # apenas Σ p

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

            # Roleta adaptativa baseada no TEMPO TOTAL (CT)
            load_metric = machine_completion_times

            weights = [1.0 / (epsilon + load_metric[m_idx]) for m_idx in range(num_machines)]
            total_w = sum(weights)

            probs = (
                [w / total_w for w in weights]
                if total_w > 0
                else [1.0 / num_machines] * num_machines
            )

            cumul = np.cumsum(probs)
            r = float(roulette_keys[int(idx)] % 1.0)

            mk_roleta_idx = int(np.searchsorted(cumul, r, side="right"))
            if mk_roleta_idx >= num_machines:
                mk_roleta_idx = num_machines - 1

            # Conjunto de candidatas via criterio de setup
            candidatas = []  # (machine_idx, setup_val)

            for m_idx in range(num_machines):
                if not machine_schedules[m_idx]:
                    candidatas.append((m_idx, 0.0))
                else:
                    last_job = machine_schedules[m_idx][-1]
                    setup_val = float(self.dados["S"].get((m_idx + 1, last_job, job), 0))
                    T_k = calc_threshold(m_idx, last_job)

                    if setup_val <= T_k:
                        candidatas.append((m_idx, setup_val))

            # Decisao final
            if candidatas:
                # escolha gulosa: menor setup admissível
                best_m_idx, best_s = min(candidatas, key=lambda x: x[1])
            else:
                # fallback: roleta adaptativa
                best_m_idx = mk_roleta_idx
                last_job = machine_schedules[best_m_idx][-1] if machine_schedules[best_m_idx] else 0
                best_s = float(self.dados["S"].get((best_m_idx + 1, last_job, job), 0))

            # Atualizações
            proc_time = float(self.dados["p"].get((best_m_idx + 1, job), 0.0))

            machine_schedules[best_m_idx].append(job)
            machine_completion_times[best_m_idx] += best_s + proc_time
            cargas_proc[best_m_idx] += proc_time

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

    def _decode_incremental(self, keys: np.ndarray) -> dict:
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

    def decoder(self, keys: np.ndarray) -> dict:
        dec = self.decoder_name.lower()
        dispatch = {
            "ect": self._decode_ect,
            "ksts": self._decode_ksts,
            "m3law": self._decoder_m3law,
            "incremental": self._decode_incremental,
            "cheapest": self._decode_cheapest_insertion,
        }
        func = dispatch.get(dec, self._decode_ect)
        return func(keys)

    def cost(self, solution: dict, final_solution: bool = False) -> float:
        makespan = solution["makespan"]

        if makespan < self.melhor_local:
            self.melhor_local = makespan
            if hasattr(self, 'ui_callback') and self.ui_callback:
                try:
                    # Prepara dados para o Gantt dinamico
                    # Soh calcula se for uma melhoria
                    X, C = self.convert_schedule_to_gantt_format(solution)
                    
                    dados = {
                        "status": "update",
                        "makespan": makespan,
                        "instancia": self.instance_name,
                        "source": getattr(self, "current_agent", "RKO"),
                        "gantt_data": {
                            "M": list(self.dados["M"]), # Lista de maquinas
                            "p": self.dados["p"],       # Tempos de processamento
                            "X": X,                     # Sequenciamento
                            "C": C                      # Tempos de término
                        }
                    }

                    self.ui_callback(dados)
                except Exception:
                    pass

        return makespan
    def convert_schedule_to_gantt_format(self, decoded_solution: dict):
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
