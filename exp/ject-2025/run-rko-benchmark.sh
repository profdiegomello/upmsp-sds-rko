#!/bin/bash

# Testando se foram informados os argumentos necessarios
if [ "$#" -lt 1 ]; then
    echo
    echo "Erro. Folder nao informado."
    echo "Sintaxe: ./run-rko-benchmark.sh <pasta de intancias> <time limit>"
    echo
    exit 1
fi

# Se pasta de instancias nao existir, abortar
if [ ! -d $1 ]; then
    echo
    echo "Pasta '$1' nao existe. Verificar caminho correto"
    echo "Sintaxe: ./run-rko-benchmark.sh <pasta de intancias> <time limit>"
    echo
    exit 1
fi

# Se informou tambem o tempo limite, captura da linha de comando. Senão, assume 5 min de experimento
if [ "$#" -eq 2 ]; then
    TIMELIMIT=$2
else
    TIMELIMIT=300
fi

# Cria a pasta results, se ela ainda nao existir
if [ ! -d results ]; then
    mkdir results
fi

# Recuperando a pasta informada
PASTA=$1

# Nome do arquivo de controle
FILE_CONTROL_RKO="RKO-bench-control.dat"
 
if [ ! -f "$FILE_CONTROL_RKO" ]; then
    touch "$FILE_CONTROL_RKO"
fi


# Agora, lista todas as instancias da pasta e guarda em uma variavel
# BENCHMARK=$(ls -1 $PASTA | grep ".txt" | sort -R)
BENCHMARK=$(find $PASTA -type f -name "*.txt" -exec basename {} \; | sort -R)
BENCH_SIZE=$(echo "$BENCHMARK" | wc -l)

echo
echo "Benchmark:"
echo
echo "$BENCHMARK"
echo
echo "Total: $BENCH_SIZE instancias"
echo

# Reseta os contadores
RKO_COUNT=0

# Executa o solver MIP para cada instancia do benchmark informado
for instancia in $BENCHMARK
do

    # Gera os nomes dos arquivos de saida
    relatorio="results/report-rko.dat"
    gantt_rko="results/cronograma-$instancia"

    # Incrementa contadores            
    RKO_COUNT=$((RKO_COUNT + 1))

    # Verifica se a instância já está listada no arquivo de controle
    if [ $(grep -Fx "$instancia" "$FILE_CONTROL_RKO" | wc -l) -gt 0 ]; then
    
        echo "Skipping instance $instancia..."
        continue
        
    else
    
        echo
        echo "RKO: Running instance '$instancia' ($SA_COUNT/$BENCH_SIZE), recording at $relatorio, graphics in $gantt_sa..."

        # Invoca o Simulated Annealing, usando os 'melhores parametros' investigados pelo irace            
        PYTHONPATH=../../src python3 -m solvers.solver-rko-upmsp-sds \
            --input $PASTA$instancia \
            --output $relatorio \
            --gantt $gantt_rko \
            --time $TIMELIMIT \
            
        # Verifica se o comando Python executou com sucesso. Se deu exit() != 0, não salva porque deu problema
        if [ $? -eq 0 ]; then
            # Concatena o nome da instancia no final do arquivo de controle
            echo $instancia >> $FILE_CONTROL_RKO        
        fi
    fi

done

# Apaga o arquivo de controle
rm $FILE_CONTROL_RKO

