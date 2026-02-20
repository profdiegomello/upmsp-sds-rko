import time
import sys
import os
import threading
import multiprocessing
from queue import Empty
from typing import Callable, Optional
from multiprocessing import Manager

from backend.rko_dependencies.rkolib.RKO import RKO
from backend.rko_dependencies.problem_upmspsds import UPMSPSDSProblem
import backend.rko_dependencies.input_output.output_writer as output_writer

class StdoutProxy:
    def __init__(self, callback: Callable[[dict], None], old_stdout, min_interval: float = 0.05):
        self.main_pid = os.getpid()
        self.callback = callback
        self.old_stdout = old_stdout
        self.min_interval = min_interval
        self._last_emit = 0.0
        self._buffer = ""
        
    def write(self, text: str):
        if not text: return
        # Trabalhadores zumbis não podem imprimir nada
        if os.getpid() != self.main_pid: return 
            
        self._buffer += text
        if "\n" in text or (time.time() - self._last_emit >= self.min_interval):
            self.flush()
            
    def flush(self):
        if os.getpid() != self.main_pid: return
        if not self._buffer: return
        msg = self._buffer
        self._buffer = ""
        self._last_emit = time.time()
        if self.callback:
            self.callback({"status": "log", "message": msg.rstrip()})

def _queue_reader(q, callback: Optional[Callable[[dict], None]], history_list: list, start_time: float, stop_event: threading.Event):
    local_best_makespan = float('inf')
    
    while not stop_event.is_set():
        try: 
            msg = q.get(timeout=0.2)
        except Empty: 
            continue 
        except Exception: 
            continue 
            
        if not msg: continue
        
        try:
            if isinstance(msg, dict):
                if msg.get("status") == "DONE": 
                    stop_event.set()
                    break
                    
                if msg.get("status") == "update" and "makespan" in msg:
                    mksp = float(msg["makespan"])
                    if mksp < local_best_makespan:
                        local_best_makespan = mksp
                        tempo = msg.get("time_to_best")
                        if tempo is None: tempo = time.time() - start_time
                        else: tempo = float(tempo)
                        history_list.append((tempo, mksp))
                        
                # Adiciona tag padrão para o pool
                if "agent" not in msg: msg["agent"] = "pool"
                if callback: callback(msg)
            else:
                texto_msg = str(msg).rstrip()
                if texto_msg and callback: callback({"status": "log", "message": texto_msg})
        except Exception: 
            continue

def run_rko(instance_path: str, decoder: str, time_limit: int, agents: dict, callback: Optional[Callable[[dict], None]] = None, save_path: str = None, gantt_path: str = None) -> dict:
    stdout_execution_history = [] 
    env = UPMSPSDSProblem(instance_path=instance_path, decoder=decoder, time_limit=time_limit)
    
    # --- FIX 1: QUARENTENA DA UI ---
    # Nunca enviamos o callback da interface para o problema, 
    # evitando que o proxy do Manager seja corrompido pelos trabalhadores.
    env.ui_callback = None 
    # -------------------------------
    
    clean_agents = {}
    valid_agents = ["BRKGA", "SA", "ILS", "VNS", "PSO", "GA", "LNS"]
    
    def force_number(v):
        try:
            if isinstance(v, str):
                v = v.strip()
                if '.' in v: return float(v)
                return int(v)
            return v if isinstance(v, (int, float)) else 0
        except: return 0

    def normalize_dict(cfg):
        if not isinstance(cfg, dict): return {"workers": force_number(cfg)}
        norm = {}
        for k, v in cfg.items():
            kl = str(k).lower().strip()
            val = force_number(v)
            if kl in ["pop", "population"]: norm["population"] = int(val)
            elif kl in ["gen", "generations"]: norm["generations"] = int(val)
            elif kl in ["iter", "iterations"]: norm["iterations"] = int(val)
            elif kl in ["temp", "temperature"]: norm["temperature"] = float(val)
            elif kl in ["prob", "probability", "cr", "f"]: norm[kl] = float(val)
            elif kl in ["threads", "workers"]: norm["workers"] = int(val)
            else: norm[k] = val
        return norm

    total_w = 0
    for ag in valid_agents:
        raw_cfg = agents.get(ag, {})
        cfg = normalize_dict(raw_cfg)
        w = int(cfg.get("workers", 0))
        if w > 0:
            clean_agents[ag] = cfg
            total_w += w
            
    if total_w == 0:
        if callback: callback({"status": "log", "message": "[SYSTEM FIX] Missing or invalid Agent config. Forcing BRKGA=1 to avoid crash."})
        clean_agents["BRKGA"] = {"workers": 1}
        
    env.agent_config = clean_agents

    old_stdout = sys.stdout
    if callback: sys.stdout = StdoutProxy(callback, old_stdout=old_stdout, min_interval=0.05)

    log_queue = None
    queue_manager = None
    reader_thread = None
    stop_event = threading.Event()
    start_time_global = time.time()

    if callback:
        try:
            queue_manager = Manager()
            log_queue = queue_manager.Queue() 
            reader_thread = threading.Thread(target=_queue_reader, args=(log_queue, callback, stdout_execution_history, start_time_global, stop_event), daemon=True)
            reader_thread.start()
        except Exception as e: 
            print(f"Erro ao criar fila: {e}")
            log_queue = None
            queue_manager = None

    final_cost = float('inf'); final_schedule = {}; raw_gantt_data = None; runtime = 0; final_time_to_best = 0

    try:
        def get_w(nome_agente):
            return int(clean_agents.get(nome_agente, {}).get("workers", 0))

        solver = RKO(env, print_best=True, save_directory=None, log_queue=log_queue)
        start_time_solver = time.time()
        
        active_agents = []
        for k, v in clean_agents.items():
            w = get_w(k)
            if w > 0: active_agents.append(f"{k}({w})")
            
        str_parameters = "+".join(active_agents) if active_agents else "RKO_DEFAULT"

        solver_final_cost, final_solution_keys, solver_time_to_best = solver.solve(
            time_total=time_limit, 
            runs=1,
            brkga=get_w("BRKGA"), 
            sa=get_w("SA"), 
            ils=get_w("ILS"),
            vns=get_w("VNS"), 
            pso=get_w("PSO"), 
            ga=get_w("GA"), 
            lns=get_w("LNS")
        )

        runtime = time.time() - start_time_solver
        final_time_to_best = solver_time_to_best

        if log_queue is not None:
            try: log_queue.put({"status": "DONE"})
            except: pass
        if reader_thread is not None: reader_thread.join(timeout=3.0)

        final_schedule = env.decoder(final_solution_keys)
        calculated_makespan = 0
        try:
            for job_info in final_schedule.values():
                val_comp = 0
                if isinstance(job_info, (list, tuple)):
                    raw_comp = job_info[2]
                    val_comp = max(raw_comp) if isinstance(raw_comp, (list, tuple)) else float(raw_comp)
                elif isinstance(job_info, (float, int)): val_comp = float(job_info)
                elif isinstance(job_info, dict): val_comp = float(job_info.get('completion', 0))
                if val_comp > calculated_makespan: calculated_makespan = val_comp
        except Exception: calculated_makespan = float('inf') 

        final_cost = min(solver_final_cost, calculated_makespan)
        if calculated_makespan == float('inf'): final_cost = solver_final_cost

        if stdout_execution_history:
            stdout_execution_history.sort(key=lambda x: x[0])
            last_time, last_val = stdout_execution_history[-1]
            tempo_limite_float = float(time_limit)
            if tempo_limite_float > last_time:
                 stdout_execution_history.append((tempo_limite_float, last_val))

    finally:
        sys.stdout = old_stdout
        
        if callback:
            tempo_final_bypass = max(float(time_limit), runtime)
            try:
                callback({
                    "status": "final_plateau",
                    "instancia": env.instance_name,
                    "final_time": tempo_final_bypass,
                    "final_makespan": final_cost
                })
            except: pass

        if log_queue is not None:
            stop_event.set()
            
        # --- FIX 2: EXTERMINADOR DE ZUMBIS ---
        # Mata qualquer PoolWorker que tenha travado antes de desligar o Manager
        for child in multiprocessing.active_children():
            if "PoolWorker" in child.name:
                try:
                    child.terminate()
                    child.join(timeout=0.5)
                except: pass
        # -------------------------------------
        
        if queue_manager is not None:
            try: queue_manager.shutdown()
            except: pass

    try:
        M = env.dados["M"]; p = env.dados["p"]
        X, C = env.convert_schedule_to_gantt_format(final_schedule)
        raw_gantt_data = {"M": M, "p": p, "X": X, "C": C}
    except Exception: pass

    if save_path:
        try:
            path_limpo = save_path.strip()
            if os.path.isdir(path_limpo) or not os.path.splitext(path_limpo)[1]:
                os.makedirs(path_limpo, exist_ok=True)
                csv_filename = os.path.join(path_limpo, "resultados.txt")
                base_dir = path_limpo
            else:
                os.makedirs(os.path.dirname(path_limpo), exist_ok=True)
                base_dir = os.path.dirname(path_limpo)
                csv_filename = path_limpo
            
            nome_arq_curva = f"{env.instance_name}_timeXmksp.txt"
            with open(os.path.join(base_dir, nome_arq_curva), "w") as f_curva:
                f_curva.write("TEMPO\tMAKESPAN\n")
                for t, mksp in stdout_execution_history:
                    f_curva.write(f"{t:.2f}\t{mksp:.4f}\n")
            
            model_name = f"RKO-{env.decoder_name.upper()}"
            output_writer.salvar_resultado(
                arquivo_saida=csv_filename, instancia=env.instance_name, modelo=model_name,
                objetivo=final_cost, lowerbound=None, gap=None, runtime=runtime, 
                constraints=0, variables=0, parameters=str_parameters,
                jobs=len(env.dados.get("N", [])), machines=len(env.dados.get("M", [])), status="FEASIBLE"
            )
        except Exception: pass

    if gantt_path and raw_gantt_data:
        try:
            if not os.path.exists(gantt_path): os.makedirs(gantt_path, exist_ok=True)
            output_writer.gantt_chart(
                M=raw_gantt_data["M"], N=env.dados["N"], N0=[0]+list(env.dados["N"]), p=raw_gantt_data["p"], s=env.dados["S"], 
                X=raw_gantt_data["X"], C=raw_gantt_data["C"], arq_gantt=os.path.join(gantt_path, f"gantt_{env.instance_name}"), 
                instancia=env.instance_name, makespan=final_cost, str_metodo=f"RKO-{env.decoder_name.upper()}"
            )
        except Exception: pass
    
    setup_range_str = "N/A"
    try:
        if hasattr(env, 'dados') and "S" in env.dados:
            s_data = env.dados["S"]
            valores_validos = []

            def extrair_setups(obj):
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        if isinstance(k, tuple) and len(k) >= 2 and k[-1] == k[-2]: continue 
                        extrair_setups(v)
                elif isinstance(obj, (list, tuple)):
                    for v in obj: extrair_setups(v)
                elif isinstance(obj, (int, float)):
                    if obj > 0: valores_validos.append(obj)

            extrair_setups(s_data)
            if valores_validos:
                setup_range_str = f"({min(valores_validos)}-{max(valores_validos)})"
    except Exception: pass

    return {
        "makespan": final_cost, 
        "schedule": final_schedule, 
        "time_to_best": final_time_to_best, 
        "runtime": runtime, 
        "instance": env.instance_name, 
        "decoder": env.decoder_name,
        "history_data": stdout_execution_history, 
        "gantt_data": raw_gantt_data,
        "setup_range": setup_range_str 
    }