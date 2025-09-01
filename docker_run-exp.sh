#!/usr/bin/env bash

# Detecta o sistema
OS=$(uname -s)

# Define se precisa de sudo
if [ "$OS" = "Linux" ]; then
    SUDO="sudo"
else
    SUDO=""
fi

$SUDO docker build --tag upmsp -f Dockerfile ./ 

# $SUDO docker run -it --volume ./:/app upmsp bash
$SUDO docker run -it --volume ./:/app upmsp bash -c 'cd ./exp/ject-2025/ && ( ./run-metaheuristics-benchmark.sh ../../bench/benchmark/small/ 300 ; ./run-metaheuristics-benchmark.sh ../../bench/benchmark/medium/ 300 )'

## se precisar liberar espaço em disco, apague o cache do docker build: 
# $SUDO docker buildx prune -f

## DICA: para pausar a execução do container e fazer checkpoint (ex.: para desligar a máquina e depois retomar do ponto pausado): 
##       OBS.: não pode rodar o container com --rm senão não tem como fazer checkpoint
# $SUDO docker ps 
# $SUDO docker checkpoint create NOME_CONTAINER checkpoint1
# $SUDO docker start --checkpoint checkpoint1 -ai NOME_CONTAINER