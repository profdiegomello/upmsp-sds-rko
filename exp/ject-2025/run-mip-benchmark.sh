#!/bin/bash

# Testando se foram informados os argumentos necessarios
if [ "$#" -lt 1 ]; then
    echo
    echo "Erro. Folder nao informado."
    echo "Sintaxe: ./run-mip-small.sh <pasta de intancias> <time limit>"
    echo
    exit 1
fi

# Se pasta de instancias nao existir, abortar
if [ ! -d $1 ]; then
    echo
    echo "Pasta $1 nao existe. Verificar caminho correto"
    echo "Sintaxe: ./run-mip-small.sh <pasta de intancias> <time limit>"
    echo
    exit 1
fi

# Se informou tambem o tempo limite, captura da linha de comando. Senão, assume 1 hs de experimento
if [ "$#" -eq 2 ]; then
    TIMELIMIT=$2
else
    TIMELIMIT=3600
fi

# Cria a pasta results, se ela ainda nao existir
if [ ! -d results ]; then
    mkdir results
fi

# Recuperando a pasta informada
PASTA=$1

# Agora, lista todas as instancias da pasta e guarda em uma variavel
BENCHMARK=$(ls $PASTA | grep ".txt")

# Executa o solver MIP para cada instancia do benchmark informado
for instancia in $BENCHMARK
do

    # Gera os nomes dos arquivos de saida
    relatorio="results/report.dat"
    gantt="results/cronograma-$instancia"

    echo "Running instance '$instancia', recording at $relatorio, graphics in $gantt..."
    
    PYTHONPATH=../../src python3 -m solvers.solver-mip \
        --nome_instancia $PASTA$instancia \
        --arq_saida  $relatorio \
        --arq_gantt $gantt \
        --time_limit $TIMELIMIT
        
done
