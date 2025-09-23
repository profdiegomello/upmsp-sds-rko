# solver-rko-upmsp-sds.py

import numpy as np
import os
import sys
import argparse
import time # Adicionado para medir o tempo total
from types import SimpleNamespace

# Adicionando a pasta raiz do codigo fonte para que todos os demais imports sejam relativos
# Para executar, usar 'python3 -m solvers.solver-brkga.py'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from metaheuristics.rkolib.RKO import RKO
from metaheuristics.rkolib.Environment import RKOEnvAbstract, check_env
import input_output.input_reader as input_reader
import input_output.output_writer as output_writer


class UPMSPSDSProblem(RKOEnvAbstract):
    """
    Implementação do ambiente do Problema de Sequenciamento em Máquinas Paralelas
    Não-Relacionadas com Tempos de Setup Dependentes da Sequência (UPMSP-SDS)
    para o framework RKO.
    """
    def __init__(self, instance_path: str):
        super().__init__()
        print(f"Carregando instância do UPMSP-SDS de: {instance_path}")

        # Carrega os dados da instância usando o leitor fornecido
        self.dados = self._load_data(instance_path)
        
        # --- Configuração dos Atributos Obrigatórios da RKOEnvAbstract ---
        self.instance_name = os.path.basename(instance_path)
        self.tam_solution = len(self.dados["N"])  # O tamanho do vetor de chaves é o número de tarefas
        self.LS_type: str = 'Best'
        self.dict_best: dict = {} # Pode ser preenchido com valores ótimos conhecidos
        self.save_q_learning_report = False

        # --- Configuração de Parâmetros das Meta-heurísticas ---
        # Estes parâmetros podem ser ajustados para otimizar a busca.
        # Fornecer múltiplos valores em uma lista ativa o Q-Learning para ajuste online.
        self.BRKGA_parameters = {'p': [100], 'pe': [0.20], 'pm': [0.10], 'rhoe': [0.70]}
        self.SA_parameters = {'SAmax': [50], 'alphaSA': [0.99], 'betaMin': [0.05], 'betaMax': [0.25], 'T0': [10000]}
        self.ILS_parameters = {'betaMin': [0.10, 0.2], 'betaMax': [0.20, 0.3]}
        self.VNS_parameters = {'kMax': [5, 3], 'betaMin': [0.05, 0.1]}
        self.PSO_parameters = {'PSize': [100], 'c1': [2.05], 'c2': [2.05], 'w': [0.73]}
        self.GA_parameters = {'sizePop': [100], 'probCros': [0.98], 'probMut': [0.005]}
        self.LNS_parameters = {'betaMin': [0.10], 'betaMax': [0.30], 'TO': [1000], 'alphaLNS': [0.95]}

    def _load_data(self, instance_path: str):
        """Usa o módulo input_reader para carregar os dados da instância."""
        # O leitor espera um objeto 'args' com o atributo 'nome_instancia'.
        mock_args = SimpleNamespace(nome_instancia=instance_path)
        return input_reader.le_arquivo(mock_args)

    def decoder(self, keys: np.ndarray) -> dict:
        """
        Decodificador ECT (Earliest Completion Time).
        Converte um vetor de chaves aleatórias em um cronograma factível.
        A ordem das chaves define a prioridade das tarefas. Cada tarefa é então
        alocada na máquina que permite seu término o mais cedo possível.
        """
        num_jobs = len(self.dados["N"])
        num_machines = len(self.dados["M"])
        
        # As chaves definem a ordem de prioridade das tarefas
        # np.argsort nos dá os índices das tarefas na ordem de processamento
        job_sequence = np.argsort(keys)

        # Estruturas para manter o estado do cronograma
        machine_schedules = [[] for _ in range(num_machines)]
        machine_completion_times = np.zeros(num_machines)

        for job_idx in job_sequence:
            job = job_idx + 1 # As tarefas nas instâncias são 1-based

            best_machine = -1
            min_completion_time = float('inf')

            # Testa a alocação da tarefa em cada máquina para encontrar a melhor
            for machine_idx in range(num_machines):
                machine = machine_idx + 1 # As máquinas são 1-based

                # A tarefa anterior é a última na lista da máquina ou a tarefa dummy '0'
                last_job_on_machine = machine_schedules[machine_idx][-1] if machine_schedules[machine_idx] else 0
                
                # Tempo de início mais cedo possível para a nova tarefa
                earliest_start_time = machine_completion_times[machine_idx]

                # Obtém os tempos de setup e processamento dos dados da instância
                setup_time = self.dados["S"].get((machine, last_job_on_machine, job), 0)
                processing_time = self.dados["p"].get((machine, job), 0)
                
                completion_time = earliest_start_time + setup_time + processing_time
                
                if completion_time < min_completion_time:
                    min_completion_time = completion_time
                    best_machine = machine_idx
            
            # Aloca a tarefa na melhor máquina encontrada
            machine_schedules[best_machine].append(job)
            machine_completion_times[best_machine] = min_completion_time

        # O makespan é o maior tempo de conclusão entre todas as máquinas
        makespan = np.max(machine_completion_times)
        
        return {"schedule": machine_schedules, "makespan": makespan}

    def cost(self, solution: dict, final_solution: bool = False) -> float:
        """
        Calcula o custo de uma solução, que é o makespan do cronograma.
        O RKO irá minimizar este valor.
        """
        return solution["makespan"]
    
    def convert_schedule_to_gantt_format(self, decoded_solution: dict) -> (dict, dict):
        """
        Converte a solução do decodificador para os formatos X e C exigidos
        pela função de plotagem do gráfico de Gantt.
        """
        schedule = decoded_solution["schedule"]
        X = {} # Dicionário de sequenciamento: X[(i, k, j)] = 1 se j sucede k na máquina i
        C = {} # Dicionário de conclusão: C[(i, j)] = tempo de término de j na máquina i

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
    args = parser.parse_args()

    # 1. Instancia o ambiente do problema
    env = UPMSPSDSProblem(instance_path=args.input)
    
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
        params_str += f"brkga:p={env.BRKGA_parameters['p']}|"
        
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
        params_str += f"PSO:c1={env.PSO_parameters['c1']}|"
        params_str += f"PSO:c2={env.PSO_parameters['c2']}|"
        params_str += f"PSO:w={env.PSO_parameters['w']}|"

        params_str += f"GA:sizePop={env.GA_parameters['sizePop']}|"
        params_str += f"GA:probCros={env.GA_parameters['probCros']}|"
        params_str += f"GA:probMut={env.GA_parameters['probMut']}|"

        params_str += f"LNS:betaMin={env.LNS_parameters['betaMin']}|"
        params_str += f"LNS:betaMax={env.LNS_parameters['betaMax']}|"
        params_str += f"LNS:TO={env.LNS_parameters['TO']}|"
        params_str += f"LNS:alphaLNS={env.LNS_parameters['alphaLNS']}|"

        params_str += 'decoder=ECT'
        
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
        print(f"\nGerando Gráfico de Gantt como '{args.gantt}-RKO-ECT.png'...")
        X, C = env.convert_schedule_to_gantt_format(final_schedule)
        output_writer.gantt_chart(
            M=env.dados["M"], N=env.dados["N"], N0=env.dados["N0"],
            p=env.dados["p"], s=env.dados["S"], X=X, C=C,
            arq_gantt=args.gantt, instancia=env.instance_name,
            makespan=final_cost, str_metodo="RKO-ECT"
        )
        print("Gráfico de Gantt salvo.")

    # 7. Exibe os resultados finais
    print("\n" + "="*30)
    print("      RESULTADOS FINAIS      ")
    print("="*30)
    print(f"Instância: {env.instance_name}")
    print(f"Melhor Makespan Encontrado: {final_cost:.4f}")
    print(f"Tempo para Melhor Solução: {time_to_best:.2f}s")
    print(f"Tempo Total de Execução: {total_runtime:.2f}s")
    print("Cronograma por Máquina:")
    for i, machine_schedule in enumerate(final_schedule["schedule"]):
        print(f"  Máquina {i+1}: {machine_schedule}")
