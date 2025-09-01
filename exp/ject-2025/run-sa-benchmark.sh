#!/bin/bash

# Testando se foram informados os argumentos necessarios
if [ "$#" -lt 1 ]; then
    echo
    echo "Erro. Folder nao informado."
    echo "Sintaxe: ./run-sa-benchmark.sh <pasta de intancias> <time limit>"
    echo
    exit 1
fi

# Se pasta de instancias nao existir, abortar
if [ ! -d $1 ]; then
    echo
    echo "Pasta '$1' nao existe. Verificar caminho correto"
    echo "Sintaxe: ./run-sa-benchmark.sh <pasta de intancias> <time limit>"
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

# Nome do arquivo de controle
FILE_CONTROL="sa-bench-control.dat"

# Verifica se o arquivo existe; se não, cria-o vazio
if [ ! -f "$FILE_CONTROL" ]; then
    touch "$FILE_CONTROL"
fi

# Agora, lista todas as instancias da pasta e guarda em uma variavel
# BENCHMARK=$(ls -1 $PASTA | grep ".txt" | sort -R)
BENCHMARK=$(find $PASTA -type f -name "*.txt" -exec basename {} \; | sort -R)

# Executa o solver MIP para cada instancia do benchmark informado
for instancia in $BENCHMARK
do

    # Gera os nomes dos arquivos de saida
    relatorio="results/report-sa.dat"
    gantt="results/cronograma-sa-$instancia"
    
    # Verifica se a instância já está listada no arquivo de controle
    if [ $(grep -Fx "$instancia" "$FILE_CONTROL" | wc -l) -gt 0 ]; then
    
        echo "Skipping instance $instancia..."
        continue
        
    else
    
        echo "Running instance '$instancia', recording at $relatorio, graphics in $gantt..."

        # Invoca o Simulated Annealing, usando os 'melhores parametros' investigados pelo irace            
        PYTHONPATH=../../src python3 -m solvers.solver-sa \
            --nome_instancia $PASTA$instancia \
            --arq_saida $relatorio \
            --arq_gantt $gantt \
            --time_limit $TIMELIMIT \
            --temp_inicial 1150\
            --temp_final 1 \
            --alpha 0.998 \
            --iter_por_temp 160 \
            --p_block 0.05 \
            --p_shift 0.7 \
            --block_size 8 \

        # Verifica se o comando Python executou com sucesso. Se deu exit() != 0, não salva porque deu problema
        if [ $? -eq 0 ]; then
            # Concatena o nome da instancia no final do arquivo de controle
            echo $instancia >> $FILE_CONTROL        
        fi
    fi
        
done

# Apaga o arquivo de controle
rm $FILE_CONTROL
