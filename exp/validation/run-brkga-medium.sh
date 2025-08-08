#!/bin/bash

PYTHONPATH=../../src python3 -m solvers.solver-brkga \
   --nome_instancia ../../bench/rsdst/small/I_6_2_S_1-9_1.txt \
   --arq_saida teste.dat \
   --gantt I_6_2_S_1-9_1-DecN \
   --tempo_limite 45 \
   --n_geracoes 50 \
   --n_individuos 500 \
   --percentual_elite 0.2 \
   --percentual_mutados 0.2 \
   --chance_cross 0.7
   --decoder n

PYTHONPATH=../../src python3 -m solvers.solver-brkga \
   --nome_instancia ../../bench/rsdst/small/I_10_2_S_1-49_6.txt \
   --arq_saida teste.dat \
   --gantt I_10_2_S_1-49_6-DecN \
   --tempo_limite 45 \
   --n_geracoes 50 \
   --n_individuos 500 \
   --percentual_elite 0.2 \
   --percentual_mutados 0.2 \
   --chance_cross 0.7
   --decoder n


PYTHONPATH=../../src python3 -m solvers.solver-brkga \
   --nome_instancia ../../bench/rsdst/small/I_12_5_S_1-124_10.txt \
   --arq_saida teste.dat \
   --gantt I_12_5_S_1-124_10-DecN \
   --tempo_limite 45 \
   --n_geracoes 100 \
   --n_individuos 1000 \
   --percentual_elite 0.2 \
   --percentual_mutados 0.2 \
   --chance_cross 0.7
   --decoder n

PYTHONPATH=../../src python3 -m solvers.solver-brkga \
   --nome_instancia ../../bench/rsdst/large/I_50_10_S_1-9_1.txt \
   --arq_saida teste.dat \
  --gantt I_50_10_S_1-9_1-DecN \
   --tempo_limite 600 \
   --n_geracoes 200 \
   --n_individuos 3000 \
   --percentual_elite 0.15 \
   --percentual_mutados 0.15 \
   --chance_cross 0.7 \
   --decoder n
   
   
################################################################################
   
PYTHONPATH=../../src python3 -m solvers.solver-brkga \
   --nome_instancia ../../bench/rsdst/small/I_6_2_S_1-9_1.txt \
   --arq_saida teste.dat \
   --gantt I_6_2_S_1-9_1-Dec2N \
   --tempo_limite 45 \
   --n_geracoes 50 \
   --n_individuos 500 \
   --percentual_elite 0.2 \
   --percentual_mutados 0.2 \
   --chance_cross 0.7
   --decoder 2n

PYTHONPATH=../../src python3 -m solvers.solver-brkga \
   --nome_instancia ../../bench/rsdst/small/I_10_2_S_1-49_6.txt \
   --arq_saida teste.dat \
   --gantt I_10_2_S_1-49_6-Dec2N \
   --tempo_limite 45 \
   --n_geracoes 50 \
   --n_individuos 500 \
   --percentual_elite 0.2 \
   --percentual_mutados 0.2 \
   --chance_cross 0.7
   --decoder 2n


PYTHONPATH=../../src python3 -m solvers.solver-brkga \
   --nome_instancia ../../bench/rsdst/small/I_12_5_S_1-124_10.txt \
   --arq_saida teste.dat \
   --gantt I_12_5_S_1-124_10-Dec2N \
   --tempo_limite 45 \
   --n_geracoes 100 \
   --n_individuos 1000 \
   --percentual_elite 0.2 \
   --percentual_mutados 0.2 \
   --chance_cross 0.7
   --decoder 2n

PYTHONPATH=../../src python3 -m solvers.solver-brkga \
   --nome_instancia ../../bench/rsdst/large/I_50_10_S_1-9_1.txt \
   --arq_saida teste.dat \
  --gantt I_50_10_S_1-9_1-Dec2N \
   --tempo_limite 600 \
   --n_geracoes 200 \
   --n_individuos 3000 \
   --percentual_elite 0.15 \
   --percentual_mutados 0.15 \
   --chance_cross 0.7 \
   --decoder 2n
   
###################################################################################


PYTHONPATH=../../src python3 -m solvers.solver-brkga \
   --nome_instancia ../../bench/rsdst/small/I_6_2_S_1-9_1.txt \
   --arq_saida teste.dat \
   --gantt I_6_2_S_1-9_1-Dec2NStar \
   --tempo_limite 45 \
   --n_geracoes 50 \
   --n_individuos 500 \
   --percentual_elite 0.2 \
   --percentual_mutados 0.2 \
   --chance_cross 0.7
   --decoder 2n*

PYTHONPATH=../../src python3 -m solvers.solver-brkga \
   --nome_instancia ../../bench/rsdst/small/I_10_2_S_1-49_6.txt \
   --arq_saida teste.dat \
   --gantt I_10_2_S_1-49_6-Dec2NStar \
   --tempo_limite 45 \
   --n_geracoes 50 \
   --n_individuos 500 \
   --percentual_elite 0.2 \
   --percentual_mutados 0.2 \
   --chance_cross 0.7
   --decoder 2n*


PYTHONPATH=../../src python3 -m solvers.solver-brkga \
   --nome_instancia ../../bench/rsdst/small/I_12_5_S_1-124_10.txt \
   --arq_saida teste.dat \
   --gantt I_12_5_S_1-124_10-Dec2NStar \
   --tempo_limite 45 \
   --n_geracoes 100 \
   --n_individuos 1000 \
   --percentual_elite 0.2 \
   --percentual_mutados 0.2 \
   --chance_cross 0.7
   --decoder 2n*
   

PYTHONPATH=../../src python3 -m solvers.solver-brkga \
   --nome_instancia ../../bench/rsdst/large/I_50_10_S_1-9_1.txt \
   --arq_saida teste.dat \
  --gantt I_50_10_S_1-9_1-Dec2NStar \
   --tempo_limite 600 \
   --n_geracoes 200 \
   --n_individuos 3000 \
   --percentual_elite 0.15 \
   --percentual_mutados 0.15 \
   --chance_cross 0.7 \
   --decoder 2n*
   
########################################################################################
   
PYTHONPATH=../../src python3 -m solvers.solver-brkga \
   --nome_instancia ../../bench/rsdst/small/I_6_2_S_1-9_1.txt \
   --arq_saida teste.dat \
   --gantt I_6_2_S_1-9_1-ECT \
   --tempo_limite 45 \
   --n_geracoes 50 \
   --n_individuos 500 \
   --percentual_elite 0.2 \
   --percentual_mutados 0.2 \
   --chance_cross 0.7
   --decoder ect

PYTHONPATH=../../src python3 -m solvers.solver-brkga \
   --nome_instancia ../../bench/rsdst/small/I_10_2_S_1-49_6.txt \
   --arq_saida teste.dat \
   --gantt I_10_2_S_1-49_6-ECT \
   --tempo_limite 45 \
   --n_geracoes 50 \
   --n_individuos 500 \
   --percentual_elite 0.2 \
   --percentual_mutados 0.2 \
   --chance_cross 0.7
   --decoder ect


PYTHONPATH=../../src python3 -m solvers.solver-brkga \
   --nome_instancia ../../bench/rsdst/small/I_12_5_S_1-124_10.txt \
   --arq_saida teste.dat \
   --gantt I_12_5_S_1-124_10-ECT \
   --tempo_limite 45 \
   --n_geracoes 100 \
   --n_individuos 1000 \
   --percentual_elite 0.2 \
   --percentual_mutados 0.2 \
   --chance_cross 0.7
   --decoder ect

PYTHONPATH=../../src python3 -m solvers.solver-brkga \
   --nome_instancia ../../bench/rsdst/large/I_50_10_S_1-9_1.txt \
   --arq_saida teste.dat \
  --gantt I_50_10_S_1-9_1-ECT \
   --tempo_limite 600 \
   --n_geracoes 200 \
   --n_individuos 3000 \
   --percentual_elite 0.15 \
   --percentual_mutados 0.15 \
   --chance_cross 0.7 \
   --decoder ect
   
##########################################################################################

PYTHONPATH=../../src python3 -m solvers.solver-brkga \
   --nome_instancia ../../bench/rsdst/small/I_6_2_S_1-9_1.txt \
   --arq_saida teste.dat \
   --gantt I_6_2_S_1-9_1-INC \
   --tempo_limite 45 \
   --n_geracoes 50 \
   --n_individuos 500 \
   --percentual_elite 0.2 \
   --percentual_mutados 0.2 \
   --chance_cross 0.7
   --decoder incremental

PYTHONPATH=../../src python3 -m solvers.solver-brkga \
   --nome_instancia ../../bench/rsdst/small/I_10_2_S_1-49_6.txt \
   --arq_saida teste.dat \
   --gantt I_10_2_S_1-49_6-INC \
   --tempo_limite 45 \
   --n_geracoes 50 \
   --n_individuos 500 \
   --percentual_elite 0.2 \
   --percentual_mutados 0.2 \
   --chance_cross 0.7
   --decoder incremental


PYTHONPATH=../../src python3 -m solvers.solver-brkga \
   --nome_instancia ../../bench/rsdst/small/I_12_5_S_1-124_10.txt \
   --arq_saida teste.dat \
   --gantt I_12_5_S_1-124_10-INC \
   --tempo_limite 45 \
   --n_geracoes 100 \
   --n_individuos 1000 \
   --percentual_elite 0.2 \
   --percentual_mutados 0.2 \
   --chance_cross 0.7
   --decoder incremental

PYTHONPATH=../../src python3 -m solvers.solver-brkga \
   --nome_instancia ../../bench/rsdst/large/I_50_10_S_1-9_1.txt \
   --arq_saida teste.dat \
  --gantt I_50_10_S_1-9_1-INC \
   --tempo_limite 600 \
   --n_geracoes 200 \
   --n_individuos 3000 \
   --percentual_elite 0.15 \
   --percentual_mutados 0.15 \
   --chance_cross 0.7 \
   --decoder incremental
   
