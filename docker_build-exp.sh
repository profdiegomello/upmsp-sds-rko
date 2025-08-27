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

## se precisar liberar espaço em disco, apague o cache do docker build: 
# $SUDO docker buildx prune -f