import threading
import os
import traceback
from datetime import datetime
from queue import Queue, Empty

try:
    from backend.rko_dependencies.solver_core import run_rko
except Exception:
    run_rko = None

# =============================================================================
# VARIÁVEIS GLOBAIS DE CONTROLE
# =============================================================================
LOG_QUEUE = Queue(maxsize=2000)
STOP_EVENT = threading.Event()
SOLVER_THREAD = None 

# =============================================================================
# FUNÇÕES AUXILIARES
# =============================================================================
def solicitar_parada():
    """Chamado pela GUI para abortar a execução."""
    STOP_EVENT.set()

def solver_callback(dados: dict):
    """Callback chamado pelo solver (RKO) para enviar logs."""
    try:
        LOG_QUEUE.put_nowait(dados)
    except Exception:
        pass  # nunca bloquear o solver

def logger_worker(gui_callback):
    """Thread dedicada a consumir a fila e atualizar a GUI."""
    while True:
        try:
            dados = LOG_QUEUE.get(timeout=0.2)
        except Empty:
            continue

        if dados is None:
            break  # sinal de encerramento

        if gui_callback:
            gui_callback(dados)

# ENTRY POINT DA GUI 
def iniciar_resolucao(dados_dict, callback_interface):
    global SOLVER_THREAD

    # Se jA existe uma thread e ela esta viva, NaO inicia outra.
    if SOLVER_THREAD is not None and SOLVER_THREAD.is_alive():
        callback_interface({
            "status": "error",
            "message": "O Solver já está em execução. Aguarde o término."
        })
        return

    # Remove lixo de execuções anteriores para evitar logs fantasmas
    while not LOG_QUEUE.empty():
        try:
            LOG_QUEUE.get_nowait()
        except Empty:
            break

    STOP_EVENT.clear()
    
    #CRIACAO E REGISTRO DA THREAD
    SOLVER_THREAD = threading.Thread(
        target=_executar_solver, 
        args=(dados_dict, callback_interface), 
        daemon=True 
    )
    SOLVER_THREAD.start()

# LÓGICA DO GERENTE DE EXECUÇÃO
def _executar_solver(dados, callback_interface):

    # 1. CAPTURA DOS CAMINHOS DE IO
    output_path = dados.get('io', {}).get('output_path', '').strip()
    gantt_path = dados.get('io', {}).get('gantt_path', '').strip()

    try:
        if run_rko is None:
            callback_interface({
                "status": "error",
                "message": "run_rko não disponível (Erro de importação)."
            })
            return

        # inicia logger thread
        logger = threading.Thread(
            target=logger_worker,
            args=(callback_interface,),
            daemon=True
        )
        logger.start()

        data_inicio = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        
        LOG_QUEUE.put({
            "status": "log",
            "message": f"Começando bateria de testes em: {data_inicio}"
        })

        # 2. CAPTURA DE PARÂMETROS
        instance_path = dados.get('io', {}).get('instance_path', '').strip()
        decoder = str(dados.get('hyper_parameters', {}).get('decoder', 'ect')).lower()
        time_limit = int(dados.get('hyper_parameters', {}).get('time_limit', 60))
        execution_times = int(dados.get('hyper_parameters', {}).get('execution_times', 1))
        agents = dados.get('agents', {})

        if execution_times < 1:
            execution_times = 1

        # 3. LISTAGEM DE ARQUIVOS
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

        # 4. LOOP PRINCIPAL COM VERIFICAÇÃO DE PARADA
        for arquivo in arquivos:
            
            # Checa se usuário clicou em STOP antes de iniciar novo arquivo
            if STOP_EVENT.is_set():
                break

            nome = os.path.basename(arquivo)

            for run_idx in range(1, execution_times + 1):
                
                # Checa se usuário clicou em STOP antes de iniciar nova rodada
                if STOP_EVENT.is_set():
                    LOG_QUEUE.put({
                        "status": "error", 
                        "message": ">>> INTERROMPIDO PELO USUÁRIO <<<"
                    })
                    break

                atual += 1
                LOG_QUEUE.put({
                    "status": "running",
                    "message": f"Processando ({atual}/{total}): {nome} [Run {run_idx}]"
                })

                try:
                    # Chama o Solver passando todos os caminhos
                    resultado = run_rko(
                        instance_path=arquivo,
                        decoder=decoder,
                        time_limit=time_limit,
                        agents=agents,
                        callback=solver_callback,
                        save_path=output_path,  # CSV
                        gantt_path=gantt_path   # Gráfico
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
            
            # Quebra o loop externo também se o stop foi acionado
            if STOP_EVENT.is_set():
                break

        # 5. FINALIZAÇÃO
        if STOP_EVENT.is_set():
             LOG_QUEUE.put({
                "status": "finished",
                "message": "PROCESSO ABORTADO MANUALMENTE."
            })
        else:
             # Captura o momento atual para o log de sucesso
             agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
             LOG_QUEUE.put({
                "status": "finished",
                "message": f"Execução da bateria finalizada em: {agora}"
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