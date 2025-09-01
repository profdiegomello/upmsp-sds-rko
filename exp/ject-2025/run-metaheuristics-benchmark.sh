#!/bin/bash

#
# SA: usa a configuração elite do irace em 22/Ago/2025
#
# 2025-08-22 16:33:27 UTC: Elite configurations (first number is the configuration ID; listed from best to worst according to the sum of ranks):
#     temp_inicial  alpha iter_por_temp p_block p_shift block_size time_limit
# 146     604.2301 0.9987           178  0.0597  0.4605         10       1800
# 222     460.0284 0.9990           172  0.0576  0.4594         11       1800
# 255     437.5871 0.9985           164  0.0587  0.4346         11       1800
# 137     686.7358 0.9989           106  0.0793  0.5898         25       1800

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
    echo "Sintaxe: ./run-metaheuristics-benchmark.sh <pasta de intancias> <time limit>"
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
FILE_CONTROL_SA="sa-bench-control.dat"
FILE_CONTROL_BRKGA="brkga-bench-control.dat"

# Verifica se o arquivo existe; se não, cria-o vazio
if [ ! -f "$FILE_CONTROL_SA" ]; then
    touch "$FILE_CONTROL_SA"
fi
if [ ! -f "$FILE_CONTROL_BRKGA" ]; then
    touch "$FILE_CONTROL_BRKGA"
fi


# Agora, lista todas as instancias da pasta e guarda em uma variavel
BENCHMARK=$(ls $PASTA | grep ".txt" | sort -R)
BENCH_SIZE=$(echo "$BENCHMARK" | wc -l)

echo
echo "Benchmark:"
echo
echo "$BENCHMARK"
echo
echo "Total: $BENCH_SIZE instancias"
echo

# Reseta os contadores
SA_COUNT=0
BRKGA_COUNT=0

# Executa o solver MIP para cada instancia do benchmark informado
for instancia in $BENCHMARK
do

    # Gera os nomes dos arquivos de saida
    relatorio="results/report-mh.dat"
    gantt_sa="results/cronograma-$instancia"
    gantt_brkga="results/cronograma-$instancia"

    # Incrementa contadores            
    SA_COUNT=$((SA_COUNT + 1))
    BRKGA_COUNT=$((BRKGA_COUNT + 1))

    # Verifica se a instância já está listada no arquivo de controle
    if [ $(grep -Fx "$instancia" "$FILE_CONTROL_SA" | wc -l) -gt 0 ]; then
    
        echo "Skipping instance $instancia..."
        continue
        
    else
    
        echo
        echo "SA: Running instance '$instancia' ($SA_COUNT/$BENCH_SIZE), recording at $relatorio, graphics in $gantt_sa..."

        # Invoca o Simulated Annealing, usando os 'melhores parametros' investigados pelo irace            
        PYTHONPATH=../../src python3 -m solvers.solver-sa \
            --nome_instancia $PASTA$instancia \
            --arq_saida $relatorio \
            --arq_gantt $gantt_sa \
            --time_limit $TIMELIMIT \
            --temp_inicial 605 \
            --temp_final 1 \
            --alpha 0.998 \
            --iter_por_temp 178 \
            --p_block 0.06 \
            --p_shift 0.46 \
            --block_size 10 \
            
        # Verifica se o comando Python executou com sucesso. Se deu exit() != 0, não salva porque deu problema
        if [ $? -eq 0 ]; then
            # Concatena o nome da instancia no final do arquivo de controle
            echo $instancia >> $FILE_CONTROL_SA        
        fi
    fi
        

    # Verifica se a instância já está listada no arquivo de controle
    if [ $(grep -Fx "$instancia" "$FILE_CONTROL_BRKGA" | wc -l) -gt 0 ]; then
    
        echo "Skipping instance $instancia..."
        continue
        
    else
    
        echo
        echo "BRKGA: Running instance '$instancia' ($BRKGA_COUNT/$BENCH_SIZE), recording at $relatorio, graphics in $gantt_brkga..."

        # Invoca o BRKGA, usando os 'melhores parametros' investigados pelo irace
        PYTHONPATH=../../src python3 -m solvers.solver-brkga \
            --nome_instancia $PASTA$instancia \
            --arq_saida $relatorio \
            --gantt $gantt_brkga \
            --tempo_limite $TIMELIMIT \
            --n_geracoes 400 \
            --n_individuos 1500 \
            --percentual_elite 0.18 \
            --percentual_mutados 0.095 \
            --chance_cross 0.75 \
            --decoder ect \

        # Verifica se o comando Python executou com sucesso. Se deu exit() != 0, não salva porque deu problema
        if [ $? -eq 0 ]; then
            # Concatena o nome da instancia no final do arquivo de controle
            echo $instancia >> $FILE_CONTROL_BRKGA        
        fi
    fi

done

# Apaga o arquivo de controle
rm $FILE_CONTROL_SA
rm $FILE_CONTROL_BRKGA

