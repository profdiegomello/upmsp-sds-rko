import time
import sys
import os
import threading
import re
from typing import Callable, Optional
from multiprocessing import Queue

from backend.rko_dependencies.rkolib.RKO import RKO
from backend.rko_dependencies.problem_upmspsds import UPMSPSDSProblem
import backend.rko_dependencies.input_output.output_writer as output_writer

# PARSER DE LOGS (Para capturar dados de convergencia do texto)
def _parse_and_store(text: str, history_list: list):
    try:
        match = re.search(r"BEST: (\d+\.?\d*) .* Time: (\d+\.?\d*)", text)
        if match:
            makespan = float(match.group(1))
            tempo = float(match.group(2))
            history_list.append((tempo, makespan))
    except Exception:
        pass

# STDOUT INTERCEPTOR (Processo Pai)
class StdoutProxy:
    def __init__(self, callback: Callable[[dict], None], history_list: list, min_interval: float = 0.3):
        self.callback = callback
        self.history_list = history_list
        self.min_interval = min_interval
        self._last_emit = 0.0
        self._buffer = ""

    def write(self, text: str):
        if not text.strip(): return
        _parse_and_store(text, self.history_list)
        self._buffer += text
        now = time.time()
        if now - self._last_emit >= self.min_interval:
            self.flush()

    def flush(self):
        if not self._buffer: return
        msg = self._buffer
        try:
            if hasattr(self, "env") and hasattr(self.env, "current_agent"):
                msg = f"[{self.env.current_agent}] {msg}"
        except Exception: pass
        self._buffer = ""
        self._last_emit = time.time()
        if self.callback:
            self.callback({"status": "log", "message": msg.rstrip()})

# QUEUE READER
def _queue_reader(q: Queue, callback: Optional[Callable[[dict], None]], history_list: list, stop_event: threading.Event):
    if callback is None:
        while not stop_event.is_set():
            try: _ = q.get(timeout=0.2)
            except Exception: continue
        return

    while not stop_event.is_set() or not q.empty():
        try: 
            msg = q.get(timeout=0.2)
        except Exception: continue
        
        try:
            if isinstance(msg, dict):
                callback(msg)
            else:
                texto_msg = str(msg).rstrip()
                if texto_msg:
                    _parse_and_store(texto_msg, history_list)
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
    env.ui_callback = callback
    env.agent_config = agents 

    old_stdout = sys.stdout
    if callback:
        sys.stdout = StdoutProxy(callback, history_list=stdout_execution_history, min_interval=0.25)
        sys.stdout.env = env

    log_queue = None
    reader_thread = None
    stop_event = None

    if callback:
        try:
            log_queue = Queue()
            stop_event = threading.Event()
            reader_thread = threading.Thread(
                target=_queue_reader, 
                args=(log_queue, callback, stdout_execution_history, stop_event), 
                daemon=True
            )
            reader_thread.start()
        except Exception:
            log_queue = None

    try:
        solver = RKO(env, print_best=True, save_directory=None, log_queue=log_queue)
        start_time = time.time()

        active_agents = [k for k, v in agents.items() if v]
        str_parameters = "+".join(active_agents) if active_agents else "RKO_DEFAULT"

        final_cost, final_solution_keys, time_to_best = solver.solve(
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

        if stdout_execution_history:
            # Varre o historico que foi capturado em tempo real 
            melhor_via_log = min([p[1] for p in stdout_execution_history])
            # Se o log viu um numero menor que o retorno oficial
            if melhor_via_log < final_cost:
                #debug: print(f"Solver retornou {final_cost}, mas o  Log registrou: {melhor_via_log}.")
                final_cost = melhor_via_log

                # TODO: encontrar o valor de makespan em p[1] de hist_curve e retornar o p[0] para a variável time_melhor_via_log
                for p in reversed(stdout_execution_history):
                    if p[1] == melhor_via_log:
                        time_melhor_via_log = abs(p[0])
                        stdout_execution_history.append((time_melhor_via_log, melhor_via_log))   #TODO: verifique se deveria utilizar pro Y melhor_via_log o time_to_best 
                        break
            else :
                runtime = time.time() - start_time
                # Adiciona ponto final no historico
                # stdout_execution_history.append((runtime, final_cost))   #BUG: verifique se deveria utilizar pro Y melhor_via_log o runtime 
                stdout_execution_history.append((abs(time_to_best), final_cost))


    finally:
        sys.stdout = old_stdout
        if stop_event is not None:
            try:
                stop_event.set()
                if reader_thread is not None: reader_thread.join(timeout=1.0)
            except Exception: pass
        if log_queue is not None:
            try:
                while not log_queue.empty(): _ = log_queue.get_nowait()
            except Exception: pass

    # PREPARA DADOS COMPLETOS PARA O RETORNO (Gantt + History)
    raw_gantt_data = None
    try:
        M = env.dados["M"]
        p = env.dados["p"]
        decoded = env.decoder(final_solution_keys)
        X, C = env.convert_schedule_to_gantt_format(decoded)
        
        raw_gantt_data = {
            "M": M, "p": p, "X": X, "C": C
        }
    except Exception as e:
        print(f"[WARN] Erro ao preparar Gantt Data: {e}")

    # SALVAR EM DISCO OS RESULTADOS DA CURVA DE CONVERGENCIA 
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
                if directory:
                    os.makedirs(directory, exist_ok=True)
                    base_dir = directory
                else:
                    base_dir = "."
                csv_filename = path_limpo
            
            nome_arq_curva = f"{env.instance_name}_timeXmksp.txt"
            caminho_curva = os.path.join(base_dir, nome_arq_curva)
            
            try:
                stdout_execution_history.sort(key=lambda x: x[0])
                with open(caminho_curva, "w") as f_curva:
                    f_curva.write("TEMPO\tMAKESPAN\n")
                    for t, mksp in stdout_execution_history:
                        f_curva.write(f"{t:.2f}\t{mksp:.4f}\n")
                print(f"[IO] Curva salva em: {nome_arq_curva}")
            except Exception: pass

            model_name = f"RKO-{env.decoder_name.upper()}"
            n_jobs = len(env.dados.get("N", []))
            n_machines = len(env.dados.get("M", []))

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
            print(f"[IO] Resultado salvo em: {csv_filename}")
            
        except Exception as e:
            print(f"[ERROR] Falha ao salvar resultados: {e}")

    # GERAR EM DISCO IMAGEM DO GANTT (SCHEDULE)
    if gantt_path and raw_gantt_data:
        try:
            if not os.path.exists(gantt_path):
                os.makedirs(gantt_path, exist_ok=True)
            
            nome_base_gantt = os.path.join(gantt_path, f"gantt_{env.instance_name}")
            N = env.dados["N"]
            N0 = [0] + list(N)
            s = env.dados["S"]

            output_writer.gantt_chart(
                M=raw_gantt_data["M"], N=N, N0=N0, p=raw_gantt_data["p"], s=s, 
                X=raw_gantt_data["X"], C=raw_gantt_data["C"], 
                arq_gantt=nome_base_gantt, 
                instancia=env.instance_name, 
                makespan=final_cost, 
                str_metodo=f"RKO-{env.decoder_name.upper()}"
            )
            print(f"[IO] Gantt final salvo em: {gantt_path}")

        except Exception as e:
            print(f"[ERROR] Falha ao gerar Gantt Final: {e}")

    final_schedule = env.decoder(final_solution_keys)
    
    # RETORNA O PACOTE COMPLETO
    return {
        "makespan": final_cost,
        "schedule": final_schedule,
        "time_to_best": time_to_best,
        "runtime": runtime,
        "instance": env.instance_name,
        "decoder": env.decoder_name,
        "history_data": stdout_execution_history, 
        "gantt_data": raw_gantt_data       
    }