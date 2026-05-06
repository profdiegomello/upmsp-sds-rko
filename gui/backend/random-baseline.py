import os
import sys
import time
import glob
import argparse
import numpy as np

# Adiciona o diretório raiz para os imports funcionarem conforme a sua estrutura
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.rko_dependencies.problem_upmspsds import UPMSPSDSProblem
import backend.rko_dependencies.input_output.output_writer as output_writer


def run_random_baseline(instance_path: str, decoder: str, time_limit: int, save_path: str):
    """
    Executa um baseline puramente estocástico.
    Gera chaves K ~ U(0,1) e avalia no decodificador informado até o tempo limite.
    """
    env = UPMSPSDSProblem(instance_path=instance_path, decoder=decoder, time_limit=time_limit)
    vector_size = env.tam_solution
    
    best_makespan = float('inf')
    best_schedule = None
    time_to_best = 0.0
    history = []
    
    print("==========================================================")
    print(f" INSTANCIA: {env.instance_name}")
    print(f" DECODER  : {decoder.upper()} (Tamanho do Vetor: {vector_size})")
    print(f" LIMITE   : {time_limit}s")
    print("==========================================================")
    
    start_time = time.time()
    
    while True:
        current_time = time.time() - start_time
        if current_time >= time_limit:
            break
            
        random_keys = np.random.rand(vector_size)
        solution = env.decoder(random_keys)
        current_makespan = solution["makespan"]
        
        if current_makespan < best_makespan:
            best_makespan = current_makespan
            best_schedule = solution["schedule"]
            time_to_best = current_time
            history.append((time_to_best, best_makespan))
            
            print(f" [t={time_to_best:05.2f}s] Novo Incumbente: {best_makespan:.4f}")
            
    runtime = time.time() - start_time
    
    print("==========================================================")
    print(f" BUSCA ENCERRADA. Tempo Total: {runtime:.2f}s")
    print(f" Melhor Makespan Encontrado: {best_makespan:.4f}")
    print(f" Tempo ate a melhor solucao (t_best): {time_to_best:.2f}s")
    print("==========================================================\n")
    
    if save_path:
        # Extrai o diretório de destino. Se vazio (ex: "resultados.txt"), usa o diretório atual "."
        dir_path = os.path.dirname(save_path)
        if not dir_path:
            dir_path = "."
        
        nome_arq_curva = f"{env.instance_name}_timeXmksp_BASELINE.txt"
        curva_path = os.path.join(dir_path, nome_arq_curva)
        
        # Salva o log de convergência
        with open(curva_path, "w") as f_curva:
            f_curva.write("TEMPO\tMAKESPAN\n")
            for t, mksp in history:
                f_curva.write(f"{t:.2f}\t{mksp:.4f}\n")
                
        n_jobs = len(env.dados.get("N", []))
        n_machines = len(env.dados.get("M", []))
        model_name = f"BASELINE-{decoder.upper()}"
        
        # Salva o resultado final sem criar diretórios
        output_writer.salvar_resultado(
            arquivo_saida=save_path, 
            instancia=env.instance_name, 
            modelo=model_name,
            objetivo=best_makespan, 
            lowerbound=None, 
            gap=None, 
            runtime=runtime, 
            constraints=0, 
            variables=0, 
            parameters="Random_Uniform(0,1)",
            jobs=n_jobs, 
            machines=n_machines, 
            status="FEASIBLE"
        )

    return best_makespan, time_to_best

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Baseline Randomico para UPMSP-SDS")
    parser.add_argument("-i", "--input", required=True, help="Caminho para o arquivo da instancia ou pasta contendo instancias.")
    parser.add_argument("-o", "--output", required=True, help="Caminho para o arquivo de saida (ex: resultados.txt).")
    parser.add_argument("-t", "--time", type=int, default=60, help="Tempo limite de execucao por instancia em segundos (padrao: 60).")
    parser.add_argument("-d", "--decoder", type=str, default="2n", help="Decodificador utilizado (padrao: 2n).")
    
    args = parser.parse_args()
    
    if os.path.isfile(args.input):
        instancias = [args.input]
    elif os.path.isdir(args.input):
        instancias = glob.glob(os.path.join(args.input, "*.txt"))
        instancias.sort()
        if not instancias:
            print(f"Erro: Nenhum arquivo .txt encontrado no diretorio {args.input}")
            sys.exit(1)
    else:
        print(f"Erro: Caminho de entrada invalido: {args.input}")
        sys.exit(1)

    print(f"Iniciando processamento de {len(instancias)} instancia(s)...\n")

    for inst in instancias:
        try:
            run_random_baseline(
                instance_path=inst, 
                decoder=args.decoder, 
                time_limit=args.time, 
                save_path=args.output
            )
        except Exception as e:
            print(f"Erro ao processar a instancia {inst}: {e}")
