import time
import sys
import os
import threading
import re
from typing import Callable, Optional
from multiprocessing import Queue, Manager

from backend.rko_dependencies.rkolib.RKO import RKO
from backend.rko_dependencies.problem_upmspsds import UPMSPSDSProblem
import backend.rko_dependencies.input_output.output_writer as output_writer

# CLASSE DE CALLBACK 
class MainThreadCallbackWrapper:
    """
    Empacota o callback da UI para ser usado pela thread principal.
    Injeta a tag 'agent': 'pool' se ela não existir.
    """
    def __init__(self, original_callback):
        self.original_callback = original_callback

    def __call__(self, dados):
        if self.original_callback:
            if isinstance(dados, dict) and "agent" not in dados:
                dados["agent"] = "pool" # [AJUSTE] Voltamos para 'pool'
            self.original_callback(dados)

# STDOUT INTERCEPTOR
class StdoutProxy:
    def __init__(self, callback: Callable[[dict], None], min_interval: float = 0.05):
        self.callback = callback
        self.min_interval = min_interval
        self._last_emit = 0.0
        self._buffer = ""

    def write(self, text: str):
        if not text: return
        self._buffer += text
        if "\n" in text or (time.time() - self._last_emit >= self.min_interval):
            self.flush()

    def flush(self):
        if not self._buffer: return
        msg = self._buffer
        self._buffer = ""
        self._last_emit = time.time()
        if self.callback:
            self.callback({"status": "log", "message": msg.rstrip()})

# QUEUE READER
def _queue_reader(q: Queue, callback: Optional[Callable[[dict], None]], history_list: list, start_time: float):
    local_best_makespan = float('inf')

    if callback is None:
        while True:
            try: 
                msg = q.get(timeout=1.0)
                if isinstance(msg, dict) and msg.get("status") == "DONE": break
            except Exception: continue 
        return

    while True:
        try: 
            msg = q.get(timeout=0.5)
        except Exception: 
            continue
        
        try:
            if isinstance(msg, dict):
                if msg.get("status") == "DONE":
                    break

                if msg.get("status") == "update" and "makespan" in msg:
                    mksp = float(msg["makespan"])
                    
                    if mksp < local_best_makespan:
                        local_best_makespan = mksp
                        tempo = msg.get("time_to_best")
                        if tempo is None:
                            tempo = time.time() - start_time
                        else:
                            tempo = float(tempo)
                        history_list.append((tempo, mksp))
                
                callback(msg)
            else:
                texto_msg = str(msg).rstrip()
                if texto_msg:
                    callback({"status": "log", "message": texto_msg})
        except Exception: continue

def run_rko(
    instance_path: str,
    decoder: str,
    time_limit: int,
    agents: dict,
    callback: Optional[Callable[[dict], None]] = None,
    save_path: str = None, 
    gantt_path: str = None
) -> dict:

    stdout_execution_history = [] 

    # Cria Ambiente
    env = UPMSPSDSProblem(
        instance_path=instance_path,
        decoder=decoder,
        time_limit=time_limit
    )

    if callback:
        env.ui_callback = MainThreadCallbackWrapper(callback)
    else:
        env.ui_callback = None

    env.agent_config = agents 

    old_stdout = sys.stdout
    if callback:
        sys.stdout = StdoutProxy(callback, min_interval=0.05)

    log_queue = None
    queue_manager = None 
    reader_thread = None
    
    start_time_global = time.time()

    if callback:
        try:
            queue_manager = Manager()
            log_queue = queue_manager.Queue()
            
            reader_thread = threading.Thread(
                target=_queue_reader, 
                args=(log_queue, callback, stdout_execution_history, start_time_global), 
                daemon=True
            )
            reader_thread.start()
        except Exception as e:
            print(f"Erro ao criar fila gerenciada: {e}")
            log_queue = None

    final_cost = float('inf')
    final_schedule = {}
    raw_gantt_data = None
    runtime = 0
    final_time_to_best = 0

    try:
        solver = RKO(env, print_best=True, save_directory=None, log_queue=log_queue)
        start_time_solver = time.time()

        active_agents = [k for k, v in agents.items() if v]
        str_parameters = "+".join(active_agents) if active_agents else "RKO_DEFAULT"

        # EXECUTA O SOLVER
        solver_final_cost, final_solution_keys, solver_time_to_best = solver.solve(
            time_total=time_limit,
            runs=1,
            brkga=1 if agents.get("BRKGA") else 0,
            sa=1 if agents.get("SA") else 0,
            ils=1 if agents.get("ILS") else 0,
            vns=1 if agents.get("VNS") else 0,
            pso=1 if agents.get("PSO") else 0,
            ga=1 if agents.get("GA") else 0, 
            lns=1 if agents.get("LNS") else 0
        )
        
        runtime = time.time() - start_time_solver
        final_time_to_best = solver_time_to_best

        if log_queue is not None:
            try: log_queue.put({"status": "DONE"})
            except: pass

        if reader_thread is not None:
            reader_thread.join(timeout=5.0)

        # PROVA REAL
        final_schedule = env.decoder(final_solution_keys)
        
        calculated_makespan = 0
        try:
            for job_info in final_schedule.values():
                val_comp = 0
                if isinstance(job_info, (list, tuple)):
                    raw_comp = job_info[2]
                    if isinstance(raw_comp, (list, tuple)):
                        val_comp = max(raw_comp)
                    else:
                        val_comp = float(raw_comp)
                elif isinstance(job_info, (float, int)):
                    val_comp = float(job_info)
                elif isinstance(job_info, dict):
                    val_comp = float(job_info.get('completion', 0))
                
                if val_comp > calculated_makespan:
                    calculated_makespan = val_comp
        except Exception:
            calculated_makespan = float('inf') 

        final_cost = min(solver_final_cost, calculated_makespan)
        if calculated_makespan == float('inf'):
            final_cost = solver_final_cost

        if stdout_execution_history:
            stdout_execution_history.sort(key=lambda x: x[0])

    finally:
        sys.stdout = old_stdout
        if queue_manager is not None:
            try: queue_manager.shutdown()
            except: pass

    # PREPARA DADOS GANTT
    try:
        M = env.dados["M"]; p = env.dados["p"]
        X, C = env.convert_schedule_to_gantt_format(final_schedule)
        raw_gantt_data = {"M": M, "p": p, "X": X, "C": C}
    except Exception as e:
        print(f"\n[WARN] Erro ao preparar Gantt Data: {e}")

    # SALVAR ARQUIVOS
    if save_path:
        try:
            path_limpo = save_path.strip()
            eh_diretorio = os.path.isdir(path_limpo) or path_limpo.endswith('/') or path_limpo.endswith('\\')
            sem_extensao = len(os.path.splitext(path_limpo)[1]) == 0

            if eh_diretorio or sem_extensao:
                os.makedirs(path_limpo, exist_ok=True)
                csv_filename = os.path.join(path_limpo, "resultados.txt")
                base_dir = path_limpo
            else:
                directory = os.path.dirname(path_limpo)
                if directory: os.makedirs(directory, exist_ok=True)
                base_dir = directory if directory else "."
                csv_filename = path_limpo
            
            nome_arq_curva = f"{env.instance_name}_timeXmksp.txt"
            caminho_curva = os.path.join(base_dir, nome_arq_curva)
            
            try:
                with open(caminho_curva, "w") as f_curva:
                    f_curva.write("TEMPO\tMAKESPAN\n")
                    for t, mksp in stdout_execution_history:
                        f_curva.write(f"{t:.2f}\t{mksp:.4f}\n")
                print(f"[IO] Curva salva em: {nome_arq_curva}\n") 
            except Exception: pass

            model_name = f"RKO-{env.decoder_name.upper()}"
            n_jobs = len(env.dados.get("N", []))
            n_machines = len(env.dados.get("M", []))

            print("-" * 40 + "\n") 

            output_writer.salvar_resultado(
                arquivo_saida=csv_filename,
                instancia=env.instance_name,
                modelo=model_name,
                objetivo=final_cost, 
                lowerbound=None,
                gap=None,
                runtime=runtime, 
                constraints=0,
                variables=0,
                parameters=str_parameters,
                jobs=n_jobs,
                machines=n_machines,
                status="FEASIBLE"
            )
            print(f"\n[IO] Resultado salvo em: {csv_filename}\n") 
            
        except Exception as e:
            print(f"[ERROR] Falha ao salvar resultados: {e}\n")

    if gantt_path and raw_gantt_data:
        try:
            if not os.path.exists(gantt_path): os.makedirs(gantt_path, exist_ok=True)
            nome_base_gantt = os.path.join(gantt_path, f"gantt_{env.instance_name}")
            N = env.dados["N"]; N0 = [0] + list(N); s = env.dados["S"]

            output_writer.gantt_chart(
                M=raw_gantt_data["M"], N=N, N0=N0, p=raw_gantt_data["p"], s=s, 
                X=raw_gantt_data["X"], C=raw_gantt_data["C"], 
                arq_gantt=nome_base_gantt, 
                instancia=env.instance_name, 
                makespan=final_cost, 
                str_metodo=f"RKO-{env.decoder_name.upper()}"
            )
            print(f"[IO] Gantt final salvo em: {gantt_path}\n")
        except Exception as e:
            print(f"[ERROR] Falha ao gerar Gantt Final: {e}\n")
    
    return {
        "makespan": final_cost,
        "schedule": final_schedule,
        "time_to_best": final_time_to_best, 
        "runtime": runtime,                 
        "instance": env.instance_name,
        "decoder": env.decoder_name,
        "history_data": stdout_execution_history, 
        "gantt_data": raw_gantt_data        
    }