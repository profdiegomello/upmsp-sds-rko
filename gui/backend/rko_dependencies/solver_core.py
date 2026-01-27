import time
import sys
import os
import threading
import re
from typing import Callable, Optional
from multiprocessing import Queue

# --- IMPORTS DO PROJETO ---
from backend.rko_dependencies.rkolib.RKO import RKO
from backend.rko_dependencies.problem_upmspsds import UPMSPSDSProblem
import backend.rko_dependencies.input_output.output_writer as output_writer



# PARSER DE LOGS (Para capturar dados de convergencia do texto)
def _parse_and_store(text: str, history_list: list):
    """
    Lê uma linha de log e, se for uma melhoria, salva em history_list.
    """
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


# QUEUE READER (Consome dados dos Processos Filhos)
def _queue_reader(q: Queue, callback: Optional[Callable[[dict], None]], history_list: list, stop_event: threading.Event):
    # Se nao tiver callback, apenas esvazia a fila
    if callback is None:
        while not stop_event.is_set():
            try: _ = q.get(timeout=0.2)
            except Exception: continue
        return

    while not stop_event.is_set() or not q.empty():
        try: 
            msg = q.get(timeout=0.2)
        except Exception: 
            continue
        
        try:
            # Se for dict repassa direto
            if isinstance(msg, dict):
                callback(msg)
            
            #Se for STRING (Texto/Log), processa como log
            else:
                texto_msg = str(msg).rstrip()
                if texto_msg:
                    _parse_and_store(texto_msg, history_list)
                    callback({"status": "log", "message": texto_msg})
                    
        except Exception: 
            continue

def run_rko(
    instance_path: str,
    decoder: str,
    time_limit: int,
    agents: dict,
    callback: Optional[Callable[[dict], None]] = None,
    save_path: str = None, 
    gantt_path: str = None
) -> dict:

    execution_history = [] 

    # Cria Ambiente
    env = UPMSPSDSProblem(
        instance_path=instance_path,
        decoder=decoder,
        time_limit=time_limit
    )
    env.ui_callback = callback
    env.agent_config = agents # Anexa config para os workers lerem

    # Configura Interceptação de Logs (Pai)
    old_stdout = sys.stdout
    if callback:
        sys.stdout = StdoutProxy(callback, history_list=execution_history, min_interval=0.25)
        sys.stdout.env = env

    # Configura Fila de Logs (Filhos)
    log_queue = None
    reader_thread = None
    stop_event = None

    if callback:
        try:
            log_queue = Queue()
            stop_event = threading.Event()
            reader_thread = threading.Thread(
                target=_queue_reader, 
                args=(log_queue, callback, execution_history, stop_event), 
                daemon=True
            )
            reader_thread.start()
        except Exception:
            log_queue = None

    try:
        #Instancia e Roda o Solver
        solver = RKO(
            env,
            print_best=True,
            save_directory=None, 
            log_queue=log_queue
        )

        start_time = time.time()

        active_agents = [k for k, v in agents.items() if v]
        str_parameters = "+".join(active_agents) if active_agents else "RKO_DEFAULT"

        # Chama o solve com os parametros mapeados corretamente
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

        runtime = time.time() - start_time
        execution_history.append((runtime, final_cost))

    finally:
        # Limpeza
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

    # 5. SALVAR RESULTADOS 
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
            
            # Salvar Curva
            nome_arq_curva = f"{env.instance_name}_timeXmksp.txt"
            caminho_curva = os.path.join(base_dir, nome_arq_curva)
            
            try:
                execution_history.sort(key=lambda x: x[0])
                with open(caminho_curva, "w") as f_curva:
                    f_curva.write("TEMPO\tMAKESPAN\n")
                    for t, mksp in execution_history:
                        f_curva.write(f"{t:.4f}\t{mksp:.4f}\n")
                print(f"[IO] Curva salva em: {nome_arq_curva}")
            except Exception: pass

            # Salvar CSV Geral
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

    # GERAR GANTT
    if gantt_path:
        try:
            if not os.path.exists(gantt_path):
                os.makedirs(gantt_path, exist_ok=True)
            
            M = env.dados["M"]
            N = env.dados["N"]
            N0 = [0] + list(N)
            p = env.dados["p"]
            s = env.dados["S"]
            
            decoded = env.decoder(final_solution_keys)
            X, C = env.convert_schedule_to_gantt_format(decoded)
            
            nome_base_gantt = os.path.join(gantt_path, f"gantt_{env.instance_name}")
            
            output_writer.gantt_chart(
                M=M, N=N, N0=N0, p=p, s=s, 
                X=X, C=C, 
                arq_gantt=nome_base_gantt, 
                instancia=env.instance_name, 
                makespan=final_cost, 
                str_metodo=f"RKO-{env.decoder_name.upper()}"
            )
            print(f"[IO] Gantt final salvo em: {gantt_path}")

        except Exception as e:
            print(f"[ERROR] Falha ao gerar Gantt Final: {e}")

    final_schedule = env.decoder(final_solution_keys)
    return {
        "makespan": final_cost,
        "schedule": final_schedule,
        "time_to_best": time_to_best,
        "runtime": runtime,
        "instance": env.instance_name,
        "decoder": env.decoder_name
    }