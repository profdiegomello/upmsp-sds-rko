import threading
import time
import os
import sys
import subprocess
from datetime import datetime, timedelta

#OBS: CODIGO SUJEITO A MUDANCAS E REFATORACOES
#VERSAO 1.0
#19/12/2025 , JOAO VITOR FONSECA



# ==============================================================================
# CONFIGURAÇÃO DE CAMINHOS
# ==============================================================================
current_dir = os.path.dirname(os.path.abspath(__file__))
# Caminho para o script do solver
solver_script_path = os.path.join(current_dir, 'rko_dependencies', 'solver_rko.py')

# ==============================================================================
# LÓGICA DE EXECUÇÃO (VIA SUBPROCESS)
# ==============================================================================

def iniciar_resolucao(dados_dict, funcao_callback_interface):

    #Lança a thread que gerencia a bateria de testes.
    
    thread = threading.Thread(
        target=_rodar_comando_externo, 
        args=(dados_dict, funcao_callback_interface)
    )
    thread.daemon = True 
    thread.start()

def _rodar_comando_externo(dados, callback):
    try:
        # --- 1. Preparar Configurações Gerais ---
        pasta_instancias = dados['io'].get('instance_path', '')
        caminho_saida = dados['io'].get('output_path', '')
        caminho_gantt = dados['io'].get('gantt_path', '')
        
        # Validação da pasta de instâncias
        arquivos_validos = []
        if pasta_instancias and os.path.isdir(pasta_instancias):
            arquivos_validos = [f for f in os.listdir(pasta_instancias) if f.endswith('.txt')]
            arquivos_validos.sort() 
        else:
            if os.path.isfile(pasta_instancias) and pasta_instancias.endswith('.txt'):
                pasta_instancias = os.path.dirname(pasta_instancias)
                arquivos_validos = [os.path.basename(dados['io'].get('instance_path'))]

        if not arquivos_validos:
            callback({"status": "error", "message": "Nenhum arquivo de instância (.txt) encontrado."})
            return

        decoder = dados['hyper_parameters'].get('decoder', 'ect')
        time_limit = dados['hyper_parameters'].get('time_limit', '60')
        
        try:
            numero_execucoes = int(dados['hyper_parameters'].get('execution_times', '1'))
        except ValueError:
            numero_execucoes = 1

        total_tarefas = len(arquivos_validos) * numero_execucoes
        tarefa_atual = 0

        # --- DEFINIÇÃO DO ARQUIVO DE SAÍDA ÚNICO (Lógica Híbrida) ---
        arquivo_resultado_unico = ""
        caminho_usuario = dados['io'].get('output_path', '').strip()

        if caminho_usuario:
            # Caso 1: Usuário digitou um arquivo específico (ex: /home/user/Teste1.txt)
            if caminho_usuario.lower().endswith('.txt'):
                pasta_destino = os.path.dirname(caminho_usuario)
                # Só cria pasta se houver um caminho de diretório
                if pasta_destino:
                    os.makedirs(pasta_destino, exist_ok=True)
                arquivo_resultado_unico = caminho_usuario
            
            # Caso 2: Usuário selecionou apenas uma pasta (ex: /home/user/Resultados)
            else:
                os.makedirs(caminho_usuario, exist_ok=True)
                arquivo_resultado_unico = os.path.join(caminho_usuario, "Resultados.txt")
        # ------------------------------------------------------------
        # -------------------------------------------

        # --- PREPARAÇÃO PARA ESTIMATIVA DE TEMPO ---
        inicio_bateria = time.time()
        
        callback({"status": "log", "message": f"Instâncias: {len(arquivos_validos)} | Execuções/Instância: {numero_execucoes}"})
        if arquivo_resultado_unico:
            callback({"status": "log", "message": f"Saída consolidada em: Resultados.txt"})
        callback({"status": "log", "message": "="*50 + "\n"})

        # --- 2. Loop Principal (Para cada Arquivo) ---
        for arquivo in arquivos_validos:
            caminho_instancia_completo = os.path.join(pasta_instancias, arquivo)
            
            # --- 3. Loop de Repetições ---
            for execucao_atual in range(1, numero_execucoes + 1):
                tarefa_atual += 1
                
                # Cabeçalho da Tarefa
                msg_status = f"Processando ({tarefa_atual}/{total_tarefas}): {arquivo} [Run {execucao_atual}]"
                callback({"status": "running", "message": msg_status})

                # GANTT CONTINUA DINÂMICO (Um arquivo imagem por execução)
                arquivo_gantt = ""
                if caminho_gantt:
                    os.makedirs(caminho_gantt, exist_ok=True)
                    sufixo_run = f"_run{execucao_atual}" if numero_execucoes > 1 else ""
                    # O script adiciona .png, passamos o base name
                    nome_base_gantt = f"Gantt_{os.path.basename(arquivo).replace('.txt', '')}_{decoder}{sufixo_run}"
                    arquivo_gantt = os.path.join(caminho_gantt, nome_base_gantt)

                # Monta comando
                cmd = [
                    sys.executable,
                    "-u",
                    solver_script_path,
                    "--input", caminho_instancia_completo,
                    "--time", str(time_limit),
                    "--decoder", decoder
                ]

                # Configuração Dinâmica dos Agentes (Do passo anterior)
                mapa_agentes = {
                    "BRKGA": "--brkga", "SA": "--sa", "ILS": "--ils",
                    "VNS": "--vns", "PSO": "--pso", "GA1": "--ga", "LNS": "--lns"
                }
                agentes_ativos = dados.get('agents', {})
                for nome_ui, flag_arg in mapa_agentes.items():
                    if nome_ui in agentes_ativos:
                        cmd.extend([flag_arg, "1"])
                    else:
                        cmd.extend([flag_arg, "0"])

                # Passa o Arquivo Único de Resultados
                if arquivo_resultado_unico:
                    cmd.extend(["--output", arquivo_resultado_unico])
                
                # Passa o Arquivo de Gantt Específico
                if arquivo_gantt: 
                    cmd.extend(["--gantt", arquivo_gantt])

                # Executa
                processo = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )

                # Lê logs em tempo real
                while True:
                    linha = processo.stdout.readline()
                    if linha == '' and processo.poll() is not None:
                        break
                    if linha:
                        callback({"status": "log", "message": linha.rstrip()})

                # Captura erros finais
                stdout, stderr = processo.communicate()
                if stderr:
                    callback({"status": "error", "message": f"Erro na instância {arquivo}:\n{stderr}"})
                
                # --- CÁLCULO DE ESTIMATIVA (ETA) ---
                agora = time.time()
                tempo_decorrido = agora - inicio_bateria
                tempo_medio_por_tarefa = tempo_decorrido / tarefa_atual
                tarefas_restantes = total_tarefas - tarefa_atual
                segundos_restantes = int(tempo_medio_por_tarefa * tarefas_restantes)
                data_termino = datetime.now() + timedelta(seconds=segundos_restantes)
                
                log_progresso =  f"\n[PROGRESSO] {tarefa_atual}/{total_tarefas} ({(tarefa_atual/total_tarefas)*100:.1f}%)"
                log_progresso += f" | Faltam: {str(timedelta(seconds=segundos_restantes))}"
                log_progresso += f" | Fim: {data_termino.strftime('%H:%M:%S')}"
                log_progresso += f"\n" + "-"*50
                
                callback({"status": "log", "message": log_progresso})
                
                time.sleep(0.5) 

        callback({"status": "finished", "message": "\nFim.\n"})

    except Exception as e:
        import traceback
        callback({"status": "error", "message": f"Erro no gerenciador de lote: {str(e)}"})
        print(traceback.format_exc())