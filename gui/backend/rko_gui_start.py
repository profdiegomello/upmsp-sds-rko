import threading
import os
import time
import traceback
from datetime import datetime
from queue import Queue, Empty

try:
    from backend.rko_dependencies.solver_core import run_rko
except Exception:
    run_rko = None

# VARIAVEIS GLOBAIS DE CONTROLE

#Queue agora nao tem limites (maximo RAM eh o limite )
LOG_QUEUE = Queue() 

STOP_EVENT = threading.Event()
SOLVER_THREAD = None 

# FUNCOES AUXILIARES
def solicitar_parada():
    """Chamado pela GUI para abortar a execução."""
    STOP_EVENT.set()

def solver_callback(dados: dict):
    """Callback chamado pelo solver (RKO) para enviar logs."""
    LOG_QUEUE.put(dados)

def logger_worker(gui_callback):
    """Thread dedicada a consumir a fila e atualizar a GUI."""
    while True:
        try:
            dados = LOG_QUEUE.get(timeout=0.2)
        except Empty:
            continue

        if dados is None:
            break

        if gui_callback:
            gui_callback(dados)

# ENTRY POINT DA GUI 
def iniciar_resolucao(dados_dict, callback_interface):
    global SOLVER_THREAD

    if SOLVER_THREAD is not None and SOLVER_THREAD.is_alive():
        callback_interface({
            "status": "error",
            "message": "O Solver já está em execução. Aguarde o término."
        })
        return

    while not LOG_QUEUE.empty():
        try: LOG_QUEUE.get_nowait()
        except Empty: break

    STOP_EVENT.clear()
    
    SOLVER_THREAD = threading.Thread(
        target=_executar_solver, 
        args=(dados_dict, callback_interface), 
        daemon=True 
    )
    SOLVER_THREAD.start()

# LOGICA DO GERENTE DE EXECUCAO
def _executar_solver(dados, callback_interface):

    output_path = dados.get('io', {}).get('output_path', '').strip()
    gantt_path = dados.get('io', {}).get('gantt_path', '').strip()

    try:
        if run_rko is None:
            callback_interface({"status": "error", "message": "run_rko não disponível."})
            return

        logger = threading.Thread(target=logger_worker, args=(callback_interface,), daemon=True)
        logger.start()

        data_inicio = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        LOG_QUEUE.put({"status": "log", "message": f"Começando os testes em: {data_inicio}"})

        instance_path = dados.get('io', {}).get('instance_path', '').strip()
        decoder = str(dados.get('hyper_parameters', {}).get('decoder', 'ect')).lower()
        time_limit = int(dados.get('hyper_parameters', {}).get('time_limit', 60))
        execution_times = int(dados.get('hyper_parameters', {}).get('execution_times', 1))
        agents = dados.get('agents', {})

        if execution_times < 1: execution_times = 1

        if os.path.isdir(instance_path):
            arquivos = [os.path.join(instance_path, f) for f in sorted(os.listdir(instance_path)) if f.endswith(".txt")]
        elif os.path.isfile(instance_path):
            arquivos = [instance_path]
        else:
            callback_interface({"status": "error", "message": "Caminho de instância inválido."})
            LOG_QUEUE.put(None)
            return

        total = len(arquivos) * execution_times
        atual = 0
        
        LOG_QUEUE.put({"status": "log", "message": f"Instâncias encontradas: {len(arquivos)} | Execuções/instância: {execution_times}"})
        LOG_QUEUE.put({"status": "log", "message": "=" * 50})

        for arquivo in arquivos:
            if STOP_EVENT.is_set(): break
            nome = os.path.basename(arquivo)

            for run_idx in range(1, execution_times + 1):
                if STOP_EVENT.is_set():
                    LOG_QUEUE.put({"status": "error", "message": ">>> INTERROMPIDO PELO USUÁRIO <<<"})
                    break

                atual += 1
                
                LOG_QUEUE.put({
                    "status": "running",
                    "message": f"Processando ({atual}/{total}): {nome} [Run {run_idx}]",
                    "instancia": nome
                })

                try:
                    resultado = run_rko(
                        instance_path=arquivo, decoder=decoder, time_limit=time_limit,
                        agents=agents, callback=solver_callback, save_path=output_path, gantt_path=gantt_path
                    )

                    # Update visual 
                    LOG_QUEUE.put({
                        "status": "update",
                        "makespan": resultado["makespan"],
                        "instancia": nome,
                        "gantt_data": resultado.get("gantt_data"),
                        "time_to_best": resultado.get("time_to_best")
                    })
                    
                    lista_agentes_ativos = [k for k, v in agents.items() if v] if agents else ["Padrão"]

                    LOG_QUEUE.put({
                        "status": "instancia_concluida",
                        "instancia": nome,
                        "makespan": resultado["makespan"],
                        "history_curve": resultado.get("history_data", []), 
                        "gantt_data": resultado.get("gantt_data"),
                        "decoder": decoder,            
                        "agentes": lista_agentes_ativos,
                    })

                    LOG_QUEUE.put({"status": "log", "message": f"Concluído: {nome} [Run {run_idx}]"})
                    
                    # Pausa para UI 
                    time.sleep(0.3)

                except Exception as e:
                    tb = traceback.format_exc()
                    LOG_QUEUE.put({"status": "error", "message": f"Erro na instância {nome}: {e}\n{tb}"})
            
            if STOP_EVENT.is_set(): break

        if STOP_EVENT.is_set():
             LOG_QUEUE.put({"status": "finished", "message": "PROCESSO ABORTADO MANUALMENTE."})
        else:
             agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
             LOG_QUEUE.put({"status": "finished", "message": f"Execução finalizada em: {agora}"})

        LOG_QUEUE.put(None)

    except Exception as e:
        tb = traceback.format_exc()
        try:
            callback_interface({"status": "error", "message": f"Erro no gerenciador: {e}\n{tb}"})
        except Exception: pass