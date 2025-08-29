#!/bin/bash
awk 'NR > 1' irace-brkga_output.dat | sort -k1,6 -n |  awk '{count[$1]++} count[$1] <= 5' > brkga-melhores.txt 

awk '{print $1, $6, $12}' brkga-melhores.txt| sed 's/.*\///' | sort -k1,2 -n | sed 's/|/ /g; s/pe-//' | awk '{print $5}' > brkga-melhores_percentual_elite.txt
awk '{print $1, $6, $12}' brkga-melhores.txt| sed 's/.*\///' | sort -k1,2 -n | sed 's/|/ /g; s/pm-//' | awk '{print $6}' > brkga-melhores_percentual_mutados.txt
awk '{print $1, $6, $12}' brkga-melhores.txt| sed 's/.*\///' | sort -k1,2 -n | sed 's/|/ /g; s/c-//' | awk '{print $7}' > brkga-melhores_chance_cross.txt
awk '{print $1, $6, $12}' brkga-melhores.txt| sed 's/.*\///' | sort -k1,2 -n | sed 's/|/ /g; s/d-//' | awk '{print $8}' | sort | uniq -c > brkga-melhores_decoder.txt

awk '{print $9}' brkga-melhores.txt  > brkga-melhores_runtime.txt
awk '{if (NR > 1) print $9}' irace-brkga_output.dat  > brkga-all_runtime.txt