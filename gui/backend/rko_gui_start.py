import threading
import os
import time
import traceback
import multiprocessing
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
RESUME_EVENT.set() 

SOLVER_THREAD = None 

# Estado Global para Checkpoint
FILA_TAREFAS = [] 
PARAMS_ATUAIS = {} 

# --- CLASSE AUXILIAR PARA O CACHE DE SEGURANÇA (GLOBAL) ---
class SafetyCallbackWrapper:
    """
    Wrapper para interceptar atualizações do solver.
    Precisa ser uma classe global para funcionar com o Pickle/Multiprocessing.
    """
    def __init__(self, cache_compartilhado, callback_original):
        self.cache = cache_compartilhado
        self.callback_original = callback_original

    def __call__(self, dados):
        # 1. Executa o callback original (Manda pra UI/Log)
        if self.callback_original:
            self.callback_original(dados)

        # 2. Intercepta e salva no cache compartilhado se for melhor
        if dados.get("status") == "update":
            try:
                mksp = float(dados.get("makespan", float('inf')))
                # Acessa o valor atual do cache (Manager Dict)
                melhor_atual = self.cache.get("makespan", float('inf'))
                
                if mksp < melhor_atual:
                    self.cache["makespan"] = mksp
                    self.cache["gantt_data"] = dados.get("gantt_data")
                    self.cache["encontrado_por"] = dados.get("agent")
            except: 
                pass

# --- FUNCOES DE COMUNICACAO COM A GUI ---
def atualizar_parametros_runtime(novos_dados):
    """Permite atualizar parametros globais enquanto pausado."""
    global PARAMS_ATUAIS
    if novos_dados:
        PARAMS_ATUAIS = novos_dados
        LOG_QUEUE.put({"status": "log", "message": ">>> Runtime Parameters Updated."})

def solicitar_parada():
    """Chamado pela GUI para abortar a execução."""
    STOP_EVENT.set()
    RESUME_EVENT.set() 

def alternar_pausa(pausar: bool):
    """Chamado pela GUI para Pausar/Retomar."""
    if pausar:
        RESUME_EVENT.clear() 
        # Envia apenas log, a UI trata o visual
        LOG_QUEUE.put({"status": "log", "message": ">>> PAUSE REQUESTED... Waiting for current task to finish."})
    else:
        RESUME_EVENT.set()   
        LOG_QUEUE.put({"status": "resumed", "message": ">>> SYSTEM RESUMED."})

def atualizar_parametros_runtime(novos_dados):
    """Permite atualizar parametros enquanto pausado."""
    global PARAMS_ATUAIS
    if novos_dados:
        PARAMS_ATUAIS = novos_dados
        LOG_QUEUE.put({"status": "log", "message": ">>> Runtime Parameters Updated."})

def obter_estado_checkpoint():
    """Retorna o estado atual para o Pickle salvar."""
    return {
        "fila_tarefas": list(FILA_TAREFAS), 
        "params": PARAMS_ATUAIS.copy()
    }

def restaurar_e_continuar(estado, callback_interface, start_paused=False):
    global FILA_TAREFAS, PARAMS_ATUAIS, SOLVER_THREAD
    
    if SOLVER_THREAD is not None and SOLVER_THREAD.is_alive():
        return 

    FILA_TAREFAS = estado["fila_tarefas"]
    PARAMS_ATUAIS = estado["params"]
    
    STOP_EVENT.clear()
    
    if start_paused:
        RESUME_EVENT.clear() # Inicia travado
        LOG_QUEUE.put({"status": "log", "message": ">>> CHECKPOINT RESTORED."})
    else:
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
    total_instancias = len(arquivos)

    # Usa enumerate para pegar o índice (1, 2, 3...)
    for idx, arq in enumerate(arquivos, 1):
        for i in range(1, execution_times + 1):
            FILA_TAREFAS.append({
                "arquivo": arq,
                "run_atual": i,
                "total_runs": execution_times,
                "inst_idx": idx,              # Índice atual
                "inst_total": total_instancias # Total
            })
    
    PARAMS_ATUAIS = dados
    return True

def _consumir_fila_tarefas(callback_interface):
    global FILA_TAREFAS, PARAMS_ATUAIS 

    threading.Thread(target=logger_worker, args=(callback_interface,), daemon=True).start()

    # Gerenciador de memória compartilhada entre processos
    with multiprocessing.Manager() as manager:
        try:
            if run_rko is None:
                raise Exception("Dependency 'run_rko' not found.")

            data_inicio = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            LOG_QUEUE.put({"status": "log", "message": f"Starting experiment at: {data_inicio}"})
            
            while len(FILA_TAREFAS) > 0:
                
                if STOP_EVENT.is_set(): break

                if not RESUME_EVENT.is_set():
                    LOG_QUEUE.put({"status": "paused", "message": ">>> SYSTEM PAUSED (Queue held)."})
                
                RESUME_EVENT.wait() 
                
                if STOP_EVENT.is_set(): break

                # --- LEITURA DINÂMICA ---
                output_path = PARAMS_ATUAIS.get('io', {}).get('output_path', '').strip()
                gantt_path = PARAMS_ATUAIS.get('io', {}).get('gantt_path', '').strip()
                decoder = str(PARAMS_ATUAIS.get('hyper_parameters', {}).get('decoder', 'ect')).lower()
                time_limit = int(PARAMS_ATUAIS.get('hyper_parameters', {}).get('time_limit', 60))
                agents = PARAMS_ATUAIS.get('agents', {})
                path_interface_atual = PARAMS_ATUAIS.get('io', {}).get('instance_path', '').strip()

                tarefa = FILA_TAREFAS.pop(0) 
                arquivo = tarefa["arquivo"]
                
                # Smart Path Recovery
                if not os.path.exists(arquivo):
                    nome_base = os.path.basename(arquivo)
                    candidato = ""
                    if os.path.isdir(path_interface_atual):
                        candidato = os.path.join(path_interface_atual, nome_base)
                    elif os.path.isfile(path_interface_atual):
                        candidato = os.path.join(os.path.dirname(path_interface_atual), nome_base)
                    
                    if candidato and os.path.exists(candidato):
                        arquivo = candidato
                    else:
                        LOG_QUEUE.put({"status": "log", "message": f"File not found (skipped): {nome_base}"})
                        continue 

                run_idx = tarefa["run_atual"]
                total_runs = tarefa["total_runs"]
                inst_idx = tarefa.get("inst_idx", "?")
                inst_total = tarefa.get("inst_total", "?")
                nome = os.path.basename(arquivo)

                LOG_QUEUE.put({
                    "status": "running", 
                    "message": f"Processing: {nome} (Inst {inst_idx}/{inst_total}) [Run {run_idx}/{total_runs}]... (Decoder: {decoder.upper()})",
                    "instancia": nome
                })

                try:
                    # --- CACHE DE SEGURANÇA (MULTIPROCESSING SAFE) ---
                    # Criamos um dict compartilhado que funciona entre processos
                    cache_compartilhado = manager.dict()
                    cache_compartilhado["makespan"] = float('inf')
                    cache_compartilhado["gantt_data"] = None
                    cache_compartilhado["encontrado_por"] = None

                    # Instanciamos a classe GLOBAL passando o cache compartilhado
                    wrapper = SafetyCallbackWrapper(cache_compartilhado, solver_callback)

                    resultado = run_rko(
                        instance_path=arquivo, 
                        decoder=decoder, 
                        time_limit=time_limit,
                        agents=agents, 
                        callback=wrapper, 
                        save_path=output_path, 
                        gantt_path=gantt_path
                    )

                    mksp_final = float(resultado.get("makespan", float('inf')))
                    mksp_melhor = cache_compartilhado["makespan"] # Lê do manager

                    if mksp_melhor < mksp_final and cache_compartilhado["gantt_data"] is not None:
                        diff = mksp_final - mksp_melhor
                        agente = cache_compartilhado.get("encontrado_por", "Unknown")
                        
                        LOG_QUEUE.put({
                            "status": "log", 
                            "message": f"[SYSTEM FIX] Final result corrected! Solver returned {mksp_final}, but {agente} found {mksp_melhor} earlier. Restoring best."
                        })
                        
                        resultado["makespan"] = mksp_melhor
                        resultado["gantt_data"] = cache_compartilhado["gantt_data"]
                    # ------------------------------------

                    LOG_QUEUE.put({
                        "status": "final_plateau",
                        "instancia": nome,
                        "final_time": float(time_limit), 
                        "final_makespan": resultado["makespan"]
                    })

                    LOG_QUEUE.put({
                        "status": "update",
                        "makespan": resultado["makespan"],
                        "instancia": nome,
                        "gantt_data": resultado.get("gantt_data"),
                        "time_to_best": resultado.get("time_to_best"),
                        "agent": "Best Final" 
                    })

                    # Lista Detalhada (Tooltip)
                    lista_agentes_detalhada = []
                    if agents:
                        for nome_agente, config in agents.items():
                            workers = 0
                            if isinstance(config, dict): workers = int(config.get("workers", 0))
                            elif isinstance(config, int): workers = config
                            
                            if workers > 0:
                                detalhes_extras = [f"Threads: {workers}"]
                                if isinstance(config, dict):
                                    for k, v in config.items():
                                        if k not in ["workers", "enabled"]:
                                            k_fmt = k.capitalize()
                                            if "population" in k.lower(): k_fmt = "Pop"
                                            elif "generations" in k.lower(): k_fmt = "Gen"
                                            elif "iterations" in k.lower(): k_fmt = "Iter"
                                            elif "temperature" in k.lower(): k_fmt = "Temp"
                                            elif "probability" in k.lower(): k_fmt = "Prob"
                                            detalhes_extras.append(f"{k_fmt}: {v}")
                                lista_agentes_detalhada.append(f"{nome_agente} [" + ", ".join(detalhes_extras) + "]")

                    if not lista_agentes_detalhada: lista_agentes_detalhada = ["None"]

                    LOG_QUEUE.put({
                        "status": "instancia_concluida",
                        "instancia": nome,
                        "makespan": resultado["makespan"],
                        "history_curve": resultado.get("history_data", []), 
                        "gantt_data": resultado.get("gantt_data"),
                        "decoder": decoder,            
                        "agentes": lista_agentes_detalhada,
                        "meta_setup_range": resultado.get("setup_range", "N/A")
                    })

                    LOG_QUEUE.put({"status": "log", "message": f"Finished: {nome} - Makespan: {resultado['makespan']}"})
                    LOG_QUEUE.put({"status": "log", "message": "==================================================\n"})

                except Exception as e:
                    import traceback
                    tb = traceback.format_exc()
                    LOG_QUEUE.put({"status": "error", "message": f"Failure in {nome}: {e}\n{tb}"})

                time.sleep(0.1)

            if STOP_EVENT.is_set():
                LOG_QUEUE.put({"status": "finished", "message": "EXECUTION ABORTED BY USER"})
            elif len(FILA_TAREFAS) == 0:
                agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                LOG_QUEUE.put({"status": "completed_all", "message": f"All tasks completed at: {agora}"})

        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            LOG_QUEUE.put({"status": "error", "message": f"Fatal error in worker: {e}\n{tb}"})
        
        finally:
            LOG_QUEUE.put(None)