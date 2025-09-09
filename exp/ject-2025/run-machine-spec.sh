#!/bin/bash

# Este script coleta e exibe informações detalhadas do sistema.
# Se rodando no WSL, ele também exibe informações do Windows.

echo "============================================="
echo "       RELATÓRIO DE SISTEMA"
echo "============================================="
echo ""

# --- Informações Gerais (Linux/WSL) ---
echo "--- INFORMAÇÕES GERAIS ---"
echo "Versão da Distribuição:"
lsb_release -d | cut -f2

echo ""

echo "Memória RAM Total:"
free -h | grep Mem | awk '{print $2}'

echo ""

# --- Detalhes do Processador (Linux/WSL) ---
echo "--- DETALHES DO PROCESSADOR ---"

# Usamos 'lscpu' para filtrar informações-chave sobre o processador.
lscpu 

echo ""

# --- Informações do Windows (executa apenas no WSL) ---
if grep -qi Microsoft /proc/version; then
    echo "--- INFORMAÇÕES DO WINDOWS ---"
    echo ""
    echo "Nome do Computador:"
    hostname.exe
    echo ""
    echo "Versão do Windows:"
    wmic.exe os get caption
    echo ""
    echo "Processador (Windows):"
    wmic.exe cpu get name
    echo ""
    echo "Memória RAM Total (Windows):"
    wmic.exe computersystem get totalphysicalmemory | awk 'NR>1 {printf "%.2f GB\n", $1/1024/1024/1024}'
    echo ""
fi

echo "============================================="
