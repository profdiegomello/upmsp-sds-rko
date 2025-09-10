#!/bin/bash

awk '{if (NR>1 && $4 == "UPMSP-SDS-MIP") print $1}' results/report.dat | sed 's/.*\///' | sort | uniq -d > medium_duplicados.txt 

awk '{if (NR>1 && $4 == "UPMSP-SDS-MIP") print $1}' results/report.dat | sed 's/.*\///' | sort | uniq -u > medium_processados.txt 

find ../../bench/benchmark/medium*/ -name "*.txt" | sed 's/.*\///' | sort > medium_instancias.txt

sort medium_instancias.txt medium_processados.txt | uniq -u > medium_naoprocessados.txt

wc -l medium_*

echo '[INFO ] movendo as instancias já processadas para uma pasta separada'
echo '[DEBUG]      FROM bench/benchmark/medium/ TO bench/benchmark/medium_ja_processadas/'

mkdir -p ../../bench/benchmark/medium_ja_processadas/
cat medium_processados.txt | xargs -I {} mv ../../bench/benchmark/medium/{} ../../bench/benchmark/medium_ja_processadas/ 2>/dev/null
cat medium_processados.txt | sed 's/\.txt/\.log/' | xargs -I {} mv ../../bench/benchmark/medium/{} ../../bench/benchmark/medium_ja_processadas/ 2>/dev/null

echo ''
echo '[INFO ] quantidade de instancias I_50_ a serem processadas:'
find ../../bench/benchmark/medium/ -name 'I_50_*.txt' | wc -l
