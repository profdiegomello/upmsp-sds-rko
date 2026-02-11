import threading
import os
import time
import traceback
from datetime import datetime
from queue import Queue, Empty

# Tenta importar o motor de resolução (Solver Core)
try:
    from backend.rko_dependencies.solver_core import run_rko
except Exception:
    run_rko = None


LOG_QUEUE = Queue() 

# Eventos de Controle de Thread
STOP_EVENT = threading.Event()
RESUME_EVENT = threading.Event() 
RESUME_EVENT.set() # Começa "Setado" (Executando)

SOLVER_THREAD = None 

# Estado Global para Checkpoint
FILA_TAREFAS = [] 
PARAMS_ATUAIS = {} 

# --- FUNCOES DE COMUNICACAO COM A GUI ---

def solicitar_parada():
    """Chamado pela GUI para abortar a execução."""
    STOP_EVENT.set()
    RESUME_EVENT.set() 

def alternar_pausa(pausar: bool):
    """Chamado pela GUI para Pausar/Retomar."""
    if pausar:
        RESUME_EVENT.clear() 
        LOG_QUEUE.put({"status": "log", "message": ">>> PAUSE REQUESTED... Waiting for current task to finish."})
    else:
        RESUME_EVENT.set()   
        LOG_QUEUE.put({"status": "resumed", "message": ">>> SYSTEM RESUMED."})

def obter_estado_checkpoint():
    """Retorna o estado atual para o Pickle salvar."""
    return {
        "fila_tarefas": list(FILA_TAREFAS), 
        "params": PARAMS_ATUAIS.copy()
    }

def restaurar_e_continuar(estado, callback_interface):
    """Recebe o estado do Pickle e reinicia a thread."""
    global FILA_TAREFAS, PARAMS_ATUAIS, SOLVER_THREAD
    
    if SOLVER_THREAD is not None and SOLVER_THREAD.is_alive():
        return 

    FILA_TAREFAS = estado["fila_tarefas"]
    PARAMS_ATUAIS = estado["params"]
    
    STOP_EVENT.clear()
    RESUME_EVENT.set() 
    
    SOLVER_THREAD = threading.Thread(
        target=_consumir_fila_tarefas, 
        args=(callback_interface,), 
        daemon=True 
    )
    SOLVER_THREAD.start()

# --- ENTRY POINT PADRÃO ---

def iniciar_resolucao(dados_dict, callback_interface):
    global SOLVER_THREAD, FILA_TAREFAS, PARAMS_ATUAIS

    if SOLVER_THREAD is not None and SOLVER_THREAD.is_alive():
        callback_interface({"status": "error", "message": "Solver is already running."})
        return

    while not LOG_QUEUE.empty():
        try: LOG_QUEUE.get_nowait()
        except Empty: break

    STOP_EVENT.clear()
    RESUME_EVENT.set()
    
    sucesso = _preparar_fila_execucao(dados_dict, callback_interface)
    if not sucesso: return

    SOLVER_THREAD = threading.Thread(
        target=_consumir_fila_tarefas, 
        args=(callback_interface,), 
        daemon=True 
    )
    SOLVER_THREAD.start()

# --- LÓGICA INTERNA ---

def solver_callback(dados: dict):
    LOG_QUEUE.put(dados)

def logger_worker(gui_callback):
    while True:
        try:
            dados = LOG_QUEUE.get(timeout=0.2)
        except Empty:
            if SOLVER_THREAD is None or not SOLVER_THREAD.is_alive():
                break
            continue
        if dados is None: break 
        if gui_callback: gui_callback(dados)

def _preparar_fila_execucao(dados, callback_interface):
    global FILA_TAREFAS, PARAMS_ATUAIS

    instance_path = dados.get('io', {}).get('instance_path', '').strip()
    execution_times = int(dados.get('hyper_parameters', {}).get('execution_times', 1))
    
    if execution_times < 1: execution_times = 1

    arquivos = []
    if os.path.isdir(instance_path):
        arquivos = [os.path.join(instance_path, f) for f in sorted(os.listdir(instance_path)) if f.endswith(".txt")]
    elif os.path.isfile(instance_path):
        arquivos = [instance_path]
    else:
        callback_interface({"status": "error", "message": "Invalid instance path."})
        return False

    FILA_TAREFAS = []
    for arq in arquivos:
        for i in range(1, execution_times + 1):
            FILA_TAREFAS.append({
                "arquivo": arq,
                "run_atual": i,
                "total_runs": execution_times
            })
    
    PARAMS_ATUAIS = dados
    return True

def _consumir_fila_tarefas(callback_interface):
    global FILA_TAREFAS 

    threading.Thread(target=logger_worker, args=(callback_interface,), daemon=True).start()

    try:
        if run_rko is None:
            raise Exception("Dependency 'run_rko' not found.")

        output_path = PARAMS_ATUAIS.get('io', {}).get('output_path', '').strip()
        gantt_path = PARAMS_ATUAIS.get('io', {}).get('gantt_path', '').strip()
        decoder = str(PARAMS_ATUAIS.get('hyper_parameters', {}).get('decoder', 'ect')).lower()
        time_limit = int(PARAMS_ATUAIS.get('hyper_parameters', {}).get('time_limit', 60))
        agents = PARAMS_ATUAIS.get('agents', {})
        exec_times = int(PARAMS_ATUAIS.get('hyper_parameters', {}).get('execution_times', 1))

        data_inicio = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        qtd_tarefas = len(FILA_TAREFAS)
        
        LOG_QUEUE.put({"status": "log", "message": f"Starting experiment at: {data_inicio} (Brazilian Date)"})
        LOG_QUEUE.put({"status": "log", "message": f"Tasks in queue: {qtd_tarefas} | Runs per instance: {exec_times}"})
        LOG_QUEUE.put({"status": "log", "message": "=" * 50})

        # --- MAIN LOOP ---
        while len(FILA_TAREFAS) > 0:
            
            if STOP_EVENT.is_set(): break

            if not RESUME_EVENT.is_set():
                LOG_QUEUE.put({"status": "paused", "message": ">>> SYSTEM PAUSED."})
            
            RESUME_EVENT.wait() 
            
            if STOP_EVENT.is_set(): break

            tarefa = FILA_TAREFAS.pop(0) 
            
            arquivo = tarefa["arquivo"]
            run_idx = tarefa["run_atual"]
            nome = os.path.basename(arquivo)

            LOG_QUEUE.put({
                "status": "running",
                "message": f"Processing: {nome} [Run {run_idx}]... (Remaining: {len(FILA_TAREFAS)})",
                "instancia": nome
            })

            try:
                resultado = run_rko(
                    instance_path=arquivo, 
                    decoder=decoder, 
                    time_limit=time_limit,
                    agents=agents, 
                    callback=solver_callback, 
                    save_path=output_path, 
                    gantt_path=gantt_path
                )

                # --- FIX: PLATEAU ---
                # Envia sinal para UI desenhar a linha reta até o final do time_limit
                LOG_QUEUE.put({
                    "status": "final_plateau",
                    "instancia": nome,
                    "final_time": float(time_limit), 
                    "final_makespan": resultado["makespan"]
                })
                # --------------------

                # Update Forçado (para garantir Gantt final)
                LOG_QUEUE.put({
                    "status": "update",
                    "makespan": resultado["makespan"],
                    "instancia": nome,
                    "gantt_data": resultado.get("gantt_data"),
                    "time_to_best": resultado.get("time_to_best"),
                    "agent": resultado.get("agent", "Final") 
                })

                lista_agentes_ativos = [k for k, v in agents.items() if v] if agents else ["Default"]

                LOG_QUEUE.put({
                    "status": "instancia_concluida",
                    "instancia": nome,
                    "makespan": resultado["makespan"],
                    "history_curve": resultado.get("history_data", []), 
                    "gantt_data": resultado.get("gantt_data"),
                    "decoder": decoder,            
                    "agentes": lista_agentes_ativos,
                })

                LOG_QUEUE.put({"status": "log", "message": f"Finished: {nome} [Run {run_idx}] - Makespan: {resultado['makespan']}"})
                LOG_QUEUE.put({"status": "log", "message": "==================================================\n"})

            except Exception as e:
                tb = traceback.format_exc()
                LOG_QUEUE.put({"status": "error", "message": f"Failure in {nome}: {e}\n{tb}"})

            time.sleep(0.1)

        if STOP_EVENT.is_set():
             LOG_QUEUE.put({"status": "finished", "message": "EXECUTION ABORTED BY USER"})
        elif len(FILA_TAREFAS) == 0:
             agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
             LOG_QUEUE.put({"status": "completed_all", "message": f"All tasks completed at: {agora}"})

    except Exception as e:
        tb = traceback.format_exc()
        LOG_QUEUE.put({"status": "error", "message": f"Fatal error in worker: {e}\n{tb}"})
    
    finally:
        LOG_QUEUE.put(None)