#####################################################################################
#
# Modulo que gerencia a entrada de dados para os resolvedores
#
#
#####################################################################################

import os
import sys

# Adicionando a pasta raiz do codigo fonte para que todos os demais imports sejam relativos
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

#
# Le arquvo no formato informado.
#
def le_formato_variavel(diretorio, formato):

    # Dicionário contendo os parametros da instância informada
    dados={
        #Definição dos conjuntos
        "M":[], #Máquinas
        "N":[], #Jobs
        "N0":[], #Jobs + dummy 0
        #Constantes
        "V":0, #Constante grande
        #Parâmetros
        "p":{}, #p[ij]: Tempo de processamento do job j na máquina i
        "S":{} #S[i,j,k]: Tempo de setup do job j=>k na máquina i
    }

    ordem = formato.split(";")

    with open(diretorio, "r") as f:
        linhas = f.read().splitlines()

    linha_atual = 0

    for campo in ordem:
        if campo == "MNNO":
            # Aqui invertemos M e N, pois o formato do arquivo é: N M N0
            parts = linhas[linha_atual].split()
            # Proteção contra linhas vazias ou malformadas
            if not parts: 
                linha_atual += 1
                parts = linhas[linha_atual].split()
                
            N, M, N0 = map(int, parts)
            dados["M"] = list(range(1, M + 1))  # máquinas: 1..M
            dados["N"] = list(range(1, N + 1))  # jobs: 1..N
            dados["N0"] = [0] + dados["N"]      # inclui dummy job 0
            linha_atual += 1

        elif campo == "V":
            # Pula linhas vazias se houver
            while not linhas[linha_atual].strip():
                linha_atual += 1
            V = int(linhas[linha_atual])
            dados["V"] = V
            linha_atual += 1

        elif campo == "p":
            # Leitura dos tempos de processamento da tarefa j na máquina i
            N_ids = dados["N"]
            M_ids = dados["M"]
            p = {}
            for j in N_ids:
                partes = list(map(int, linhas[linha_atual].split()))
                for i in range(0, len(partes), 2):
                    maquina = partes[i] + 1  # índice 1-based
                    tempo = partes[i + 1]
                    p[(maquina, j)] = tempo
                linha_atual += 1
            dados["p"] = p

        elif campo == "S":
            # Pula linhas vazias até achar SSD ou fim
            while linha_atual < len(linhas) and not linhas[linha_atual].strip():
                linha_atual += 1
                
            if linha_atual < len(linhas) and linhas[linha_atual].strip() != "SSD":
                raise ValueError("Esperado marcador 'SSD' não encontrado")
            linha_atual += 1

            S = {}
            M_ids = dados["M"]
            N_ids = dados["N"]

            for m_index in range(len(M_ids)):
                maquina = M_ids[m_index]

                if linha_atual >= len(linhas): break
                marcador_maquina = linhas[linha_atual].strip()
                if not marcador_maquina.startswith("M"):
                    raise ValueError(f"Esperado marcador de máquina, obtido '{marcador_maquina}'")
                linha_atual += 1

                for i_index, j in enumerate(N_ids):  # para cada linha da matriz (job j)
                    if linha_atual >= len(linhas): break
                    valores = list(map(int, linhas[linha_atual].split()))
                    for k_index, k in enumerate(N_ids):  # para cada coluna da matriz (job k)
                        # A matriz de setup no arquivo geralmente inclui o dummy? 
                        # Assumindo que a leitura segue a lógica original 1:1
                        if k_index < len(valores):
                            S[(maquina, j, k)] = valores[k_index]
                    linha_atual += 1
            dados["S"] = S
         
    # Devolve a estrutura de dados que representa a instância
    return dados

#
# Verifica se o arquivo informado existe. 
#
def le_arquivo(args):
    
    caminho = args.nome_instancia
    
    if not os.path.exists(caminho):
        # Lança erro limpo para que o rko_gui_start.py possa tratar
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")
        
    return le_formato_variavel(caminho, "MNNO;V;p;S")