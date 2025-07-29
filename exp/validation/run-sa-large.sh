#!/bin/bash

PYTHONPATH=../../src python3 -m solvers.solver-sa \
    --nome_instancia ../../bench/rsdst/large/I_50_10_S_1.txt \
    --arq_saida teste.dat \
    --arq_gantt I_50_10_S_1-9_1 \
    --time_limit 45 \
    --temp_inicial 1000\
    --temp_final 1 \
    --alpha 0.99 \
    --iter_por_temp 150 \
    --p_block 0.2 \
    --p_shift 0.5 \
    --block_size 5 \
    

PYTHONPATH=../../src python3 -m solvers.solver-sa \
    --nome_instancia ../../bench/rsdst/large/I_250_30_S_1-124_10.txt \
    --arq_saida teste.dat \
    --arq_gantt I_250_30_S_1-124_10 \
    --time_limit 45 \
    --temp_inicial 1000\
    --temp_final 1 \
    --alpha 0.99 \
    --iter_por_temp 150 \
    --p_block 0.2 \
    --p_shift 0.5 \
    --block_size 5 \
    


