import argparse
import os
import sys
import random
import time
import math

# Adicionando a pasta raiz do codigo fonte para que todos os demais imports sejam relativos
# Para executar, usar 'python3 -m solvers.solver-brkga.py'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

print(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import input_output.input_reader as entrada
import input_output.output_writer as saida
import mip_model.upmsp_model as upmsp

#
# Funcao principal que executa o modelo MIP do
#
def main():

    parser = argparse.ArgumentParser(description="Simulated Annealing para UPMS-ST")
    parser.add_argument("--nome_instancia", required=True, help="Caminho para o arquivo da instância.")
    parser.add_argument("--arq_saida", default="resultados.txt", help="Arquivo de saída dos resultados.")
    parser.add_argument("--arq_gantt", default="gantt.png", help="Arquivo de saída do gráfico Gantt.")
    parser.add_argument("--time_limit", type=int, default=30, help="Limite de tempo em segundos.")

    # Processa os argumentos de linha de comando
    args = parser.parse_args()

    # Le os dados do arquivo de entrada
    dados = entrada.le_arquivo(args) 
    
    # Se a instancia não passar as máquinas elegíveis:     
    # Coloco que todas as máquinas são elegíveis para todos os jobs
    if 'maquinasElegiveis' not in dados: dados['maquinasElegiveis'] = {j: dados['M'] for j in dados['N']}

    log_path = args.nome_instancia + ".log"

    resultado = upmsp.modelSolving(dados["M"], dados["N"], dados["N0"], dados["p"], dados["S"], log_path, args.time_limit)

    #if resultado.get("lowerbound") is not None:
    #    print(f"Lowerbound: {resultado['lowerbound']}")

    parametros = f"M-{len(dados['M'])}|N-{len(dados['N'])}|N0-{len(dados['N0'])}|p-{len(dados['p'])}|S-{len(dados['S'])}|tl-{args.time_limit}"

    saida.salvar_resultado(args.arq_saida, args.nome_instancia, 'UPMSP-SDS-MIP', 
                    resultado['objetivo'], resultado['lowerbound'], None, resultado['runtime'],
                    resultado.get('constraints', 0), resultado.get('variables', 0), 
                    parametros, len(dados["N"]), len(dados["M"]), resultado["status_code"])
    
    #if "solucao" in resultado and resultado["solucao"]:
    #    saida.gerar_gantt(resultado["solucao"], dados, args.arq_gantt, tipo_solucao=args.modelo.upper())

if __name__ == "__main__":
    main()

