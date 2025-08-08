import sys, os
import argparse
import time

# Adicionando a pasta raiz do codigo fonte para que todos os demais imports sejam relativos
# Para executar, usar 'python3 -m solvers.solver-brkga.py'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

print(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import input_output.input_reader as entrada
import input_output.output_writer as saida
import metaheuristics.brkga.brkga as brkga


if __name__ == "__main__":

    # Recebe argumentos do terminal e os armazena em args
    parser=argparse.ArgumentParser(description="BRKGA para UPMS-ST")
    parser.add_argument("--nome_instancia", required=True, type=str, default=None, help="Nome da instância")
    parser.add_argument("--arq_saida", required=True, type=str, default=None, help="Arquivo de saída dos resultados")
    parser.add_argument("--gantt", type=str, default=None, help="Saída grafico de Gantt")
    parser.add_argument("--tempo_limite", type=int, default=-1, help="Limite de tempo em segundos")
    parser.add_argument("--n_geracoes", type=int, default=0, help="Número de gerações a ser computada")
    parser.add_argument("--n_individuos", type=int, default=0, help="Número de individuos a ser gerado")
    parser.add_argument("--percentual_elite", type=float, default=0, help="Número percentual de 1 a 0 de indivíduos da elite")
    parser.add_argument("--percentual_mutados", type=float, default=0, help="Número percentual de 1 a 0 de indivíduos mutados")
    parser.add_argument("--chance_cross", type=float, default=0, help="Número percentual de 1 a 0 de genes fazerem crossover")
    parser.add_argument("--lowerbound", type=float, default=None, help="Número de lowerbound do Gurobi para calcular o gap")
    parser.add_argument("--mostra_gantt", type=int, default=0, help="Deseja ver o grafico de gantt (0-Não 1-Sim)")
    parser.add_argument("--parcial", action="store_const", const=1, default=0, help="Deseja resultado parcial (0-Não 1-Sim)")
    parser.add_argument("--decoder", type=str, default="n", help="Modelo do decoder")
    
    # Processa os argumentos
    args = parser.parse_args()

    # Le os dados da instância e preenche na estrutura de dados retornada
    dados = entrada.le_arquivo(args) 

    # Executa o solver
    solution, runtime, status, C, X = brkga.solve(dados, 
                args.nome_instancia, 
                args.tempo_limite, 
                args.n_individuos, 
                args.n_geracoes, 
                args.percentual_elite,
                args.percentual_mutados,
                args.chance_cross,
                args.parcial,
                args.decoder
                )
    
    # Escreve a string de parametros para depuracao 
    parametros=f"i-{args.n_individuos}|g-{args.n_geracoes}|pe-{args.percentual_elite}|pm-{args.percentual_mutados}|c-{args.chance_cross}|d-{args.decoder}"

    # Salva saida em arquivo de relatorio
    saida.salvar_resultado(args.arq_saida, args.nome_instancia, "BRKGA", solution[0], args.lowerbound, None, runtime, 0, 0, parametros, len(dados["N"]), len(dados["M"]), status)

    # Grava o arquivo de Gantt, se informado
    if(args.gantt is not None):
        saida.gantt_chart(dados['M'], dados['N'], dados['N0'], dados['p'], dados['S'], 
                          X, C, args.gantt, 
                          args.nome_instancia, solution[0], f'BRKGA-{args.decoder}')


    
    #escreve_final(populacao_f, populacao_m_f, results, t_inicio, "saidabrkga.txt", saida, geracao)
    

    #TODO:
    #-Corrigir entrada do argparse formato ->Ex01: -input 100 FEITO!
    #-Renomear crossover para geranovapopulacao() FEITO!
    #-Mudar separador do PARAMETERS FEITO!
    #Implementar Gantt
    #Corrigir LowerBound
