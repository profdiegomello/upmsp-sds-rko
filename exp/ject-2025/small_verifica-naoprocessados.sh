#!/bin/bash

# MODEL="UPMSP-SDS-MIP"
# FILE="results/report.dat"

MODEL="RKO"
FILE="results/report-rko.dat"

echo '[INFO ] verificando instancias não processadas para o modelo' $MODEL 'conforme resultados em ' $FILE

# awk '{if (NR>1 && $4 == "'$MODEL'") print $1}' $FILE | grep '/small/' | sed 's/.*\///' | sort | uniq -d > small_duplicados.txt 
# awk '{if (NR>1 && $4 == "'$MODEL'") print $1}' $FILE | grep '/small/' | sed 's/.*\///' | sort | uniq -u > small_processados.txt
awk '{if (NR>1 && $4 == "'$MODEL'") print $1}' $FILE | grep -v -E '(I_50)|(I_100)' | sed 's/.*\///' | sort | uniq -d > small_duplicados.txt  
awk '{if (NR>1 && $4 == "'$MODEL'") print $1}' $FILE | grep -v -E '(I_50)|(I_100)' | sed 's/.*\///' | sort | uniq -u > small_processados.txt 

find ../../bench/benchmark/small*/ -name "*.txt" | sed 's/.*\///' | sort | uniq > small_instancias.txt

sort small_instancias.txt small_processados.txt | uniq -u > small_naoprocessados.txt

wc -l small_*.txt | grep -v total

if [[ -z $1 ]]; then
	echo ''
	echo '[INFO ] movendo as instancias já processadas para uma pasta separada'
	echo '[DEBUG]      FROM bench/benchmark/small/ TO bench/benchmark/small_ja_processadas/'

	mkdir -p ../../bench/benchmark/small_ja_processadas/
	cat small_processados.txt | xargs -I {} mv ../../bench/benchmark/small/{} ../../bench/benchmark/small_ja_processadas/ 2>/dev/null
	cat small_processados.txt | sed 's/\.txt/\.log/' | xargs -I {} mv ../../bench/benchmark/small/{} ../../bench/benchmark/small_ja_processadas/ 2>/dev/null

	echo ''
	echo '[INFO ] quantidade de instancias a serem processadas:'
	find ../../bench/benchmark/small/ -name 'I_*.txt' | wc -l

fi
