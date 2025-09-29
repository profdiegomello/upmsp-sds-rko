#!/bin/bash

#
# BRKGA: usa a configuração elite do irace em 01/Set/2025
#
# 2025-09-01 10:32:39 UTC: Elite configurations (first number is the configuration ID; listed from best to worst according to the sum of ranks):
#
#     n_geracoes n_individuos percentual_elite percentual_mutados chance_cross decoder tempo_limite
# 159        400         1500           0.1800             0.0947       0.7445     ect          300
# 131        400         1500           0.1806             0.0914       0.7470     ect          300
# 151        400         1500           0.1742             0.0767       0.7830     ect          300
# 153        600         1500           0.1764             0.0788       0.7620     ect          300


# Testando se foram informados os argumentos necessarios
if [ "$#" -lt 1 ]; then
    echo
    echo "Erro. Folder nao informado."
    echo "Sintaxe: ./run-rkga-benchmark.sh <pasta de intancias> <time limit>"
    echo
    exit 1
fi

# Se pasta de instancias nao existir, abortar
if [ ! -d $1 ]; then
    echo
    echo "Pasta '$1' nao existe. Verificar caminho correto"
    echo "Sintaxe: ./run-rkga-benchmark.sh <pasta de intancias> <time limit>"
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
FILE_CONTROL_RKGA="rkga-bench-control.dat"

# Verifica se o arquivo existe; se não, cria-o vazio
if [ ! -f "$FILE_CONTROL_RKGA" ]; then
    touch "$FILE_CONTROL_RKGA"
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
RKGA_COUNT=0

# Executa o solver MIP para cada instancia do benchmark informado
for instancia in $BENCHMARK
do

    # Gera os nomes dos arquivos de saida
    relatorio="results/report-rkga.dat"
    gantt_rkga="results/rkga/png-cronogramas/cronograma-$instancia"

    # Incrementa contadores            
    RKGA_COUNT=$((RKGA_COUNT + 1))

    # Verifica se a instância já está listada no arquivo de controle
    if [ $(grep -Fx "$instancia" "$FILE_CONTROL_RKGA" | wc -l) -gt 0 ]; then
    
        echo "Skipping instance $instancia..."
        continue
        
    else
    
        echo
        echo "RKGA: Running instance '$instancia' ($RKGA_COUNT/$BENCH_SIZE), recording at $relatorio, graphics in $gantt_rkga..."

        # Invoca o RKGA, usando os 'melhores parametros' investigados pelo irace
        PYTHONPATH=../../src python3 -m solvers.solver-rkga \
            --nome_instancia $PASTA$instancia \
            --arq_saida $relatorio \
            --gantt $gantt_rkga \
            --tempo_limite $TIMELIMIT \
            --n_geracoes 400 \
            --n_individuos 1500 \
            --percentual_elite 0.18 \
            --percentual_mutados 0.095 \
            --chance_cross 0.75 \

        # Verifica se o comando Python executou com sucesso. Se deu exit() != 0, não salva porque deu problema
        if [ $? -eq 0 ]; then
            # Concatena o nome da instancia no final do arquivo de controle
            echo $instancia >> $FILE_CONTROL_RKGA        
        fi
    fi

done

# Apaga o arquivo de controle
rm $FILE_CONTROL_RKGA

