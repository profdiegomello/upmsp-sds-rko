#!/bin/bash

PYTHONPATH=../../src python3 -m solvers.solver-brkga \
    --nome_instancia ../../bench/rsdst/large/I_250_30_S_1-124_10.txt \
    --arq_saida teste.dat \
    --gantt I_250_30_S_1-124_10-DecN \
    --tempo_limite 600 \
    --n_geracoes 500 \
    --n_individuos 5000 \
    --percentual_elite 0.15 \
    --percentual_mutados 0.15 \
    --chance_cross 0.7 \
    --decoder n
    

PYTHONPATH=../../src python3 -m solvers.solver-brkga \
    --nome_instancia ../../bench/rsdst/large/I_250_30_S_1-124_10.txt \
    --arq_saida teste.dat \
    --gantt I_250_30_S_1-124_10-Dec2N \
    --tempo_limite 600 \
    --n_geracoes 500 \
    --n_individuos 5000 \
    --percentual_elite 0.15 \
    --percentual_mutados 0.15 \
    --chance_cross 0.7 \
    --decoder 2n
    

PYTHONPATH=../../src python3 -m solvers.solver-brkga \
    --nome_instancia ../../bench/rsdst/large/I_250_30_S_1-124_10.txt \
    --arq_saida teste.dat \
    --gantt I_250_30_S_1-124_10-2NStar \
    --tempo_limite 600 \
    --n_geracoes 500 \
    --n_individuos 5000 \
    --percentual_elite 0.15 \
    --percentual_mutados 0.15 \
    --chance_cross 0.7 \
    --decoder 2n*
    

PYTHONPATH=../../src python3 -m solvers.solver-brkga \
    --nome_instancia ../../bench/rsdst/large/I_250_30_S_1-124_10.txt \
    --arq_saida teste.dat \
    --gantt I_250_30_S_1-124_10-ECT \
    --tempo_limite 600 \
    --n_geracoes 500 \
    --n_individuos 5000 \
    --percentual_elite 0.15 \
    --percentual_mutados 0.15 \
    --chance_cross 0.7 \
    --decoder ect
    

PYTHONPATH=../../src python3 -m solvers.solver-brkga \
    --nome_instancia ../../bench/rsdst/large/I_250_30_S_1-124_10.txt \
    --arq_saida teste.dat \
    --gantt I_250_30_S_1-124_10-INC \
    --tempo_limite 600 \
    --n_geracoes 500 \
    --n_individuos 5000 \
    --percentual_elite 0.15 \
    --percentual_mutados 0.15 \
    --chance_cross 0.7 \
    --decoder incremental
    
