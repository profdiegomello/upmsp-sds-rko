#!/bin/bash

# MODEL="UPMSP-SDS-MIP"
# FILE="results/report.dat"

# MODEL="RKO"
# FILE="results/report-rko.dat"

MODEL="RKGA"
FILE="results/report-rkga.dat"

echo '[INFO ] verificando instancias não processadas para o modelo' $MODEL 'conforme resultados em ' $FILE

# awk '{if (NR>1 && $4 == "'$MODEL'") print $1}' $FILE | grep '/medium/' | sed 's/.*\///' | sort | uniq -d > medium_duplicados.txt 
# awk '{if (NR>1 && $4 == "'$MODEL'") print $1}' $FILE | grep '/medium/' | sed 's/.*\///' | sort | uniq -u > medium_processados.txt 
awk '{if (NR>1 && $4 == "'$MODEL'") print $1}' $FILE | grep -E '(I_50)|(I_100)' | sed 's/.*\///' | sort | uniq -u > medium_processados.txt 

find ../../bench/benchmark/medium*/ -name "*.txt" | sed 's/.*\///' | sort | uniq > medium_instancias.txt

sort medium_instancias.txt medium_processados.txt | uniq -u > medium_naoprocessados.txt

wc -l medium_*.txt | grep -v total

if [[ -z $1 ]]; then
	echo ''
	echo '[INFO ] movendo as instancias já processadas para uma pasta separada'
	echo '[DEBUG]      FROM bench/benchmark/medium/ TO bench/benchmark/medium_ja_processadas/'

	mkdir -p ../../bench/benchmark/medium_ja_processadas/
	cat medium_processados.txt | xargs -I {} mv ../../bench/benchmark/medium/{} ../../bench/benchmark/medium_ja_processadas/ 2>/dev/null
	cat medium_processados.txt | sed 's/\.txt/\.log/' | xargs -I {} mv ../../bench/benchmark/medium/{} ../../bench/benchmark/medium_ja_processadas/ 2>/dev/null

	echo ''
	echo '[INFO ] quantidade de instancias I_50_ a serem processadas:'
	find ../../bench/benchmark/medium/ -name 'I_50_*.txt' | wc -l
	echo ''
	echo '[INFO ] quantidade de instancias I_100_ a serem processadas:'
	find ../../bench/benchmark/medium/ -name 'I_100_*.txt' | wc -l

fi
