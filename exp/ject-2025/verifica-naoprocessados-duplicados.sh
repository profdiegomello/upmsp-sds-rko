#!/bin/bash

awk '{if (NR>1 && $4 == "UPMSP-SDS-MIP") print $1}' results/report.dat | sed 's/.*\///' | sort | uniq -d > report.dat_duplicados.txt 

awk '{if (NR>1 && $4 == "UPMSP-SDS-MIP") print $1}' results/report.dat | sed 's/.*\///' | sort | uniq -u > report.dat_processados.txt 

find ../../bench/benchmark/medium*/ -name "*.txt" | sed 's/.*\///' | sort > report.dat_instancias.txt

sort report.dat_instancias.txt report.dat_processados.txt | uniq -u > report.dat_naoprocessados.txt

wc -l report.dat_*

echo '[INFO ] movendo as instancias já processadas para uma pasta separada'
echo '[DEBUG]      FROM bench/benchmark/medium/ TO bench/benchmark/medium_ja_processadas/'

cat report.dat_processados.txt | xargs -I {} mv ../../bench/benchmark/medium/{} ../../bench/benchmark/medium_ja_processadas/ 2>/dev/null
cat report.dat_processados.txt | sed 's/\.txt/\.log/' | xargs -I {} mv ../../bench/benchmark/medium/{} ../../bench/benchmark/medium_ja_processadas/ 2>/dev/null

echo ''
echo '[INFO ] quantidade de instancias I_50_ a serem processadas:'
find ../../bench/benchmark/medium/ -name 'I_50_*.txt' | wc -l
