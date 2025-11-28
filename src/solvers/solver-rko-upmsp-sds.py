# solver-rko-upmsp-sds.py

import numpy as np
import os
import sys
import argparse
import time
from types import SimpleNamespace

# Adicionando a pasta raiz do codigo fonte para que todos os demais imports sejam relativos
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from metaheuristics.rkolib.RKO import RKO
from metaheuristics.rkolib.Environment import RKOEnvAbstract
import input_output.input_reader as input_reader
import input_output.output_writer as output_writer


class UPMSPSDSProblem(RKOEnvAbstract):
    """
    Implementação do ambiente UPMSP-SDS para o framework RKO.
    Suporta múltiplos decoders (ECT e M3LAW).
    """
    def __init__(self, instance_path: str, decoder_strategy: str = 'ECT'):
        super().__init__()
        print(f"Carregando instância do UPMSP-SDS de: {instance_path}")
        print(f"Estratégia de Decoder selecionada: {decoder_strategy}")

        self.dados = self._load_data(instance_path)
        self.decoder_strategy = decoder_strategy.upper()
        
        # --- Configuração dos Atributos Obrigatórios da RKOEnvAbstract ---
        self.instance_name = os.path.basename(instance_path)
        self.tam_solution = len(self.dados["N"])
        self.LS_type: str = 'Best'
        self.dict_best: dict = {}
        self.save_q_learning_report = False

        # --- Configuração de Parâmetros das Meta-heurísticas ---
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

    def decoder(self, keys: np.ndarray) -> dict:
        """
        Método despachante: escolhe qual algoritmo de decodificação usar
        com base na configuração inicial.
        """
        if self.decoder_strategy == 'M3LAW' or self.decoder_strategy == 'm3law':
            return self._decoder_m3law(keys)
        elif self.decoder_strategy == 'ECT' or self.decoder_strategy == 'ect':
            return self._decoder_ect(keys)
        else:
            return self._decoder_ect(keys)

    def _decoder_ect(self, keys: np.ndarray) -> dict:
        """
        Decoder ECT: Earliest Completion Time.
        """
        num_machines = len(self.dados["M"])
        
        # Ordena tarefas pela chave (prioridade)
        job_sequence = np.argsort(keys)

        machine_schedules = [[] for _ in range(num_machines)]
        machine_completion_times = np.zeros(num_machines)

        for job_idx in job_sequence:
            job = job_idx + 1 

            best_machine = -1
            min_completion_time = float('inf')

            for machine_idx in range(num_machines):
                machine = machine_idx + 1
                last_job_on_machine = machine_schedules[machine_idx][-1] if machine_schedules[machine_idx] else 0
                
                earliest_start_time = machine_completion_times[machine_idx]
                setup_time = self.dados["S"].get((machine, last_job_on_machine, job), 0)
                processing_time = self.dados["p"].get((machine, job), 0)
                
                completion_time = earliest_start_time + setup_time + processing_time
                
                if completion_time < min_completion_time:
                    min_completion_time = completion_time
                    best_machine = machine_idx
            
            machine_schedules[best_machine].append(job)
            machine_completion_times[best_machine] = min_completion_time

        makespan = np.max(machine_completion_times)
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
    parser.add_argument("--gantt", type=str, default=None, help="Nome base para o arquivo do gráfico de Gantt.")
    parser.add_argument("--output", type=str, default=None, help="Arquivo de saída para registrar os resultados.")
    # NOVO: Argumento para selecionar o decoder
    parser.add_argument("--decoder", type=str, default="ECT", choices=["ECT", "M3LAW"], help="Estratégia de decodificação (ECT ou M3LAW).")
    
    args = parser.parse_args()

    # 1. Instancia o ambiente passando o decoder escolhido
    env = UPMSPSDSProblem(instance_path=args.input, decoder_strategy=args.decoder)
    
    # 2. Instancia o solver RKO
    solver = RKO(env=env, print_best=True)
    
    start_time = time.time()

    # 3. Executa o solver
    final_cost, final_solution_keys, time_to_best = solver.solve(
        time_total=args.time, 
        runs=1,
        brkga=1, lns=1, vns=1, ils=1, sa=1, pso=1, ga=1
    )
    
    total_runtime = time.time() - start_time
    final_schedule = env.decoder(final_solution_keys)

    # 5. Salva os resultados
    if args.output:
        print(f"\nSalvando resultado no arquivo: {args.output}")
        
        params_str = ''
        # ... (parâmetros das metaheurísticas omitidos para brevidade, mas mantidos iguais) ...
        # Adiciona apenas o decoder na string
        params_str += f'decoder={args.decoder}|'
        
        output_writer.salvar_resultado(
            arquivo_saida=args.output,
            instancia=env.instance_name,
            modelo="RKO",
            objetivo=final_cost,
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

    # 6. Gera o gráfico de Gantt
    if args.gantt:
        print(f"\nGerando Gráfico de Gantt...")
        X, C = env.convert_schedule_to_gantt_format(final_schedule)
        output_writer.gantt_chart(
            M=env.dados["M"], N=env.dados["N"], N0=env.dados["N0"],
            p=env.dados["p"], s=env.dados["S"], X=X, C=C,
            arq_gantt=args.gantt, instancia=env.instance_name,
            makespan=final_cost, str_metodo=f"RKO-{args.decoder}"
        )
        print("Gráfico de Gantt salvo.")

    print("\n" + "="*30)
    print("      RESULTADOS FINAIS      ")
    print("="*30)
    print(f"Decoder: {args.decoder}")
    print(f"Melhor Makespan: {final_cost:.4f}")
    print(f"Tempo Total: {total_runtime:.2f}s")