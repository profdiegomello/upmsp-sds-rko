import threading
import os
import traceback
from datetime import datetime
from queue import Queue, Empty

try:
    from backend.rko_dependencies.solver_core import run_rko
except Exception:
    run_rko = None

# FILA GLOBAL DE LOG 
LOG_QUEUE = Queue(maxsize=2000)

# CALLBACK GLOBAL 
def solver_callback(dados: dict):
    # Callback chamado pelo solver
    try:
        LOG_QUEUE.put_nowait(dados)
    except Exception:
        pass  # nunca bloquear o solver

# LOGGER THREAD
def logger_worker(gui_callback):
    # Thread dedicada a atualizar GUI e imprimir logs
    while True:
        try:
            dados = LOG_QUEUE.get(timeout=0.2)
        except Empty:
            continue

        if dados is None:
            break  # sinal de encerramento

        # sempre atualiza GUI
        if gui_callback:
            gui_callback(dados)

# ENTRY POINT DA GUI
def iniciar_resolucao(dados_dict, callback_interface):
    thread = threading.Thread(
        target=_executar_solver, 
        args=(dados_dict, callback_interface), 
        daemon=True 
    )
    thread.start() 

def _executar_solver(dados, callback_interface):
    # 1. CAPTURA DOS CAMINHOS DE IO
    output_path = dados.get('io', {}).get('output_path', '').strip()
    gantt_path = dados.get('io', {}).get('gantt_path', '').strip()  
    try:
        if run_rko is None:
            callback_interface({
                "status": "error",
                "message": "run_rko não disponível."
            })
            return

        # inicia logger thread
        logger = threading.Thread(
            target=logger_worker,
            args=(callback_interface,),
            daemon=True
        )
        logger.start()

        instance_path = dados.get('io', {}).get('instance_path', '').strip()
        decoder = str(dados.get('hyper_parameters', {}).get('decoder', 'ect')).lower()
        time_limit = int(dados.get('hyper_parameters', {}).get('time_limit', 60))
        execution_times = int(dados.get('hyper_parameters', {}).get('execution_times', 1))
        agents = dados.get('agents', {})

        if execution_times < 1:
            execution_times = 1

        # resolve instâncias
        if os.path.isdir(instance_path):
            arquivos = [
                os.path.join(instance_path, f)
                for f in sorted(os.listdir(instance_path))
                if f.endswith(".txt")
            ]
        elif os.path.isfile(instance_path):
            arquivos = [instance_path]
        else:
            callback_interface({
                "status": "error",
                "message": "Caminho de instância inválido."
            })
            LOG_QUEUE.put(None)
            return

        total = len(arquivos) * execution_times
        atual = 0
        
        LOG_QUEUE.put({
            "status": "log",
            "message": f"Instâncias encontradas: {len(arquivos)} | Execuções/instância: {execution_times}"
        })
        LOG_QUEUE.put({
            "status": "log",
            "message": "=" * 50
        })

        for arquivo in arquivos:
            nome = os.path.basename(arquivo)

            for run_idx in range(1, execution_times + 1):
                atual += 1

                LOG_QUEUE.put({
                    "status": "running",
                    "message": f"\nProcessando ({atual}/{total}): {nome} [Run {run_idx}]"
                })

                try:
                    # ENVIO PARA O SOLVER
                    resultado = run_rko(
                        instance_path=arquivo,
                        decoder=decoder,
                        time_limit=time_limit,
                        agents=agents,
                        callback=solver_callback,
                        save_path=output_path,  # Caminho do arq. de saida
                        gantt_path=gantt_path   # Caminho do gantt
                    )

                    LOG_QUEUE.put({
                        "status": "update",
                        "makespan": resultado["makespan"],
                        "instancia": nome
                    })

                    LOG_QUEUE.put({
                        "status": "log",
                        "message": f"Concluído: {nome} [Run {run_idx}]",
                    })

                except Exception as e:
                    tb = traceback.format_exc()
                    LOG_QUEUE.put({
                        "status": "error",
                        "message": f"Erro na instância {nome} (run {run_idx}): {e}\n{tb}"
                    })

        agora = datetime.now().strftime("%d/%m %H:%M:%S")

        LOG_QUEUE.put({
            "status": "finished",
            "message": f"Execução finalizada em: {agora}"
        })

        # encerra logger
        LOG_QUEUE.put(None)

    except Exception as e:
        tb = traceback.format_exc()
        try:
            callback_interface({
                "status": "error",
                "message": f"Erro no gerenciador: {e}\n{tb}"
            })
        except Exception:
            pass