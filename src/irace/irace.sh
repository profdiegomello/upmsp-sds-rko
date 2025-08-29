#!/usr/bin/env bash

# Detecta o sistema
OS=$(uname -s)

# Define se precisa de sudo
if [ "$OS" = "Linux" ]; then
    SUDO="sudo"
else
    SUDO=""
fi

$SUDO docker build --tag irace -f Dockerfile_iRace ./ \
  && $SUDO docker run --name irace -it --volume ./:/app irace \
    bash -c 'Rscript src/irace/irace-brkga-scenario.R | tee -a "output/irace-brkga_$(date +%Y-%m-%d)_stdout.txt"'
    # bash 
    # bash -c 'Rscript src/irace/irace-sa-scenario.R | tee -a "output/irace-sa_$(date +%Y-%m-%d)_stdout.txt"'

## se precisar liberar espaço em disco, apague o cache do docker build: 
# $SUDO docker buildx prune -f

## DICA: para pausar a execução do container e fazer checkpoint (ex.: para desligar a máquina e depois retomar do ponto pausado): 
##       OBS.: não pode rodar o container com --rm senão não tem como fazer checkpoint
# $SUDO docker checkpoint create irace checkpoint1
# $SUDO docker start --checkpoint checkpoint1 irace