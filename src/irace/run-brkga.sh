#!/bin/bash

# O irace passa os argumentos na seguinte ordem:
# [ID da config] [ID da instancia] [semente] [caminho da instancia] [param1 valor] [param2 valor] ...

# Captura os argumentos em variáveis
config_id="${1}"
instance_id="${2}"
seed="${3}"
nome_instancia="${4}"
n_geracoes="${5}"
n_individuos="${6}"
percentual_elite="${7}"
percentual_mutados="${8}"
chance_cross="${9}"
decoder="${10}"
tempo_limite="${11}"
# OBS.: não passamos o --lowerbound pois o irace vai olhar apenas o makespan e não o gap (só disponível para instâncias resolvidas com o MIP/Gurobi)

# Define a pasta raiz do projeto para o Python
export PYTHONPATH=/app/src

# Constrói a linha de comando para o resolvedor Python
# Pro Docker execute como /app
# exec python3 /app/src/solvers/solver-brkga.py \
# Pro Host execute como ./
exec python3 ./src/solvers/solver-brkga.py \
    --arq_saida "./output/irace-brkga_output.dat" \
    --nome_instancia "${nome_instancia}" \
    --seed "${seed}" \
    --n_geracoes "${n_geracoes}" \
    --n_individuos "${n_individuos}" \
    --percentual_elite "${percentual_elite}" \
    --percentual_mutados "${percentual_mutados}" \
    --chance_cross "${chance_cross}" \
    --decoder "${decoder}" \
    --tempo_limite "${tempo_limite}"
    