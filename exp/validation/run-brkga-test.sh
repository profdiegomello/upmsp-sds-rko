#!/bin/bash

PYTHONPATH=../../src python3 -m solvers.solver-brkga \
   --nome_instancia ../../bench/rsdst/small/I_6_2_S_1-9_1.txt \
   --arq_saida teste.dat \
   --gantt I_6_2_S_1-9_1 \
   --tempo_limite 45 \
   --n_geracoes 50 \
   --n_individuos 500 \
   --percentual_elite 0.2 \
   --percentual_mutados 0.2 \
   --chance_cross 0.7


PYTHONPATH=../../src python3 -m solvers.solver-brkga \
   --nome_instancia ../../bench/rsdst/small/I_10_2_S_1-49_6.txt \
   --arq_saida teste.dat \
   --gantt I_10_2_S_1-49_6 \
   --tempo_limite 45 \
   --n_geracoes 50 \
   --n_individuos 500 \
   --percentual_elite 0.2 \
   --percentual_mutados 0.2 \
   --chance_cross 0.7


PYTHONPATH=../../src python3 -m solvers.solver-brkga \
   --nome_instancia ../../bench/rsdst/small/I_12_5_S_1-124_10.txt \
   --arq_saida teste.dat \
   --gantt I_12_5_S_1-124_10 \
   --tempo_limite 45 \
   --n_geracoes 100 \
   --n_individuos 1000 \
   --percentual_elite 0.2 \
   --percentual_mutados 0.2 \
   --chance_cross 0.7



