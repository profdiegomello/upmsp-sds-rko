#!/bin/bash

# O irace passa os argumentos na seguinte ordem:
# [ID da config] [ID da instancia] [semente] [caminho da instancia] [param1 valor] [param2 valor] ...

# Captura os argumentos em variáveis
config_id="$1"
instance_id="$2"
seed="$3"
nome_instancia="$4"
arq_saida="$5"
gantt="$6"
tempo_limite="$7"
n_geracoes="$8"
n_individuos="$9"
percentual_elite="$10"
percentual_mutados="$11"
chance_cross="$12"
decoder="$13"
# OBS.: não passamos o --lowerbound pois o irace vai olhar apenas o makespan e não o gap (só disponível para instâncias resolvidas com o MIP/Gurobi)

# Define a pasta raiz do projeto para o Python
export PYTHONPATH=/app/src

# Constrói a linha de comando para o resolvedor Python
# Pro Docker execute como /app
# exec python3 /app/src/solvers/solver-brkga.py \
# Pro Host execute como ./
exec python3 ./src/solvers/solver-brkga.py \
    --nome_instancia "$nome_instancia" \
    --seed "$seed" \
    --arq_saida "$arq_saida" \
    --gantt "$gantt" \
    --tempo_limite "$tempo_limite" \
    --n_geracoes "$n_geracoes" \
    --n_individuos "$n_individuos" \
    --percentual_elite "$percentual_elite" \
    --percentual_mutados "$percentual_mutados" \
    --chance_cross "$chance_cross" \
    --decoder "$decoder"
    