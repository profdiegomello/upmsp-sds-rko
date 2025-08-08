import sys, os
import argparse
import time

# Adicionando a pasta raiz do codigo fonte para que todos os demais imports sejam relativos
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

print(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import input_output.input_reader as entrada
import input_output.output_writer as saida
import metaheuristics.sa.simulated_annealing as sa


def main():
    parser = argparse.ArgumentParser(description="Simulated Annealing para UPMS-ST")
    parser.add_argument("--nome_instancia", required=True, help="Caminho para o arquivo da instância.")
    parser.add_argument("--arq_saida", required=True, default="resultados.txt", help="Arquivo de saída dos resultados.")
    parser.add_argument("--arq_gantt", default="gantt.png", help="Arquivo de saída do gráfico Gantt.")
    parser.add_argument("--time_limit", type=int, default=30, help="Limite de tempo em segundos.")
    parser.add_argument("--temp_inicial", type=float, default=1000.0)
    parser.add_argument("--temp_final", type=float, default=1.0)
    parser.add_argument("--alpha", type=float, default=0.95)
    parser.add_argument("--iter_por_temp", type=int, default=100)
    parser.add_argument("--p_block",type=float, default=0)
    parser.add_argument("--block_size", type=int, default=0)
    parser.add_argument("--p_shift", type=float, default=0)
    parser.add_argument("--lowerbound", type=float, default=None, help="Número de lowerbound do Gurobi para calcular o gap")
    parser.add_argument("--seed", type=int, default=None, help="Semente de aleatoriedade") # Nova linha
    
    args = parser.parse_args()

    # Carrega os dados da instância
    dados = entrada.le_arquivo(args) 
    
    # Se a instancia não passar as máquinas elegíveis:
    if 'maquinasElegiveis' not in dados: dados['maquinasElegiveis'] = {j: dados['M'] for j in dados['N']}
    
    # Executa o simulated annealing com os parametro dados
    # Inclui o argumento seed
    resultado = sa.rodar_simulated_annealing(dados, args.temp_inicial, args.temp_final, args.alpha, args.iter_por_temp, args.p_block, args.block_size, args.p_shift, args.time_limit)
    
    # Constroi a string de parametros
    parametros = f"ti-{args.temp_inicial}|tf-{args.temp_final}|a-{args.alpha}|it-{args.iter_por_temp}|b-{args.p_block}|bs-{args.block_size}|ps-{args.p_shift}|tl-{args.time_limit}"
        
    # Salva os resultados calculados
    saida.salvar_resultado(args.arq_saida, args.nome_instancia, 'SA', 
                            resultado['objetivo'], args.lowerbound, None, resultado['runtime'],
                            resultado.get('constraints', 0), resultado.get('variables', 0), 
                            parametros, len(dados["N"]), len(dados["M"]), resultado["status_code"])
    
    if "solucao" in resultado and resultado["solucao"]:
        saida.gantt_chart(dados['M'], dados['N'], dados['N0'], dados['p'], dados['S'], 
                            resultado['X_dict'], resultado['C_dict'], args.arq_gantt, 
                            args.nome_instancia, resultado['objetivo'], 'SA')

    # Altera a linha para imprimir o custo e a semente
    print(f"{resultado['objetivo']} {args.seed}")

if __name__ == "__main__":
    main()