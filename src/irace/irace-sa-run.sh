#!/bin/bash

# O irace passa os argumentos na seguinte ordem:
# [ID da config] [ID da instancia] [semente] [caminho da instancia] [param1 valor] [param2 valor] ...

# Captura os argumentos em variáveis
config_id="$1"
instance_id="$2"
seed="$3"
instance_path="$4"
temp_inicial="$5"
alpha="$6"
iter_por_temp="$7"
p_block="$8"
p_shift="$9"
block_size="${10}"

# Define a pasta raiz do projeto para o Python
export PYTHONPATH=/app/src

# Constrói a linha de comando para o resolvedor Python
# Pro Docker execute como /app
# exec python3 /app/src/solvers/solver-sa.py \
# Pro Host execute como ./
exec python3 ./src/solvers/solver-sa.py \
    --nome_instancia "$instance_path" \
    --seed "$seed" \
    --arq_saida "irace_output.dat" \
    --time_limit 30 \
    --temp_inicial "$temp_inicial" \
    --alpha "$alpha" \
    --iter_por_temp "$iter_por_temp" \
    --p_block "$p_block" \
    --block_size "$block_size" \
    --p_shift "$p_shift"