#!/bin/bash

for i in {1..5}
do
    echo executando baseline: repeticao $i de 5
    mkdir -p baseline_repeticao_$i && cd baseline_repeticao_$i
    python3 ../random-baseline.py --input /home/pesquisa/Desktop/upmsp-sds-rko-versao-normal/bench/rsdst/t --output baseline-results.dat
    cd ../
    cat baseline_repeticao_$i/baseline-results.dat >> ./baseline-results.dat
done
