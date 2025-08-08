#!/bin/bash

INSTANCE_FILE="$1"
SEED="$2"
shift 2

export PYTHONPATH=/app/src

exec python3 /app/src/solvers/solver-sa.py \
    --nome_instancia "$INSTANCE_FILE" \
    --seed "$SEED" \
    --arq_saida irace_output.dat \
    --time_limit 45 \
    "$@"