#!/bin/bash

VENV_DIR=".venv"
REQ_FILE="requirements.txt"
SCRIPT_PRINCIPAL="main.py"

echo "--- Verificador de Ambiente Python ---"

# 1. Verifica se a pasta .venv existe, se não, cria
if [ ! -d "$VENV_DIR" ]; then
    echo "[!] Ambiente virtual não encontrado. Criando em $VENV_DIR..."
    python3.12 -m venv $VENV_DIR
else
    echo "[✓] Ambiente virtual detectado."
fi

# 2. Ativa o ambiente
echo "[+] Ativando ambiente..."
source $VENV_DIR/bin/activate

# 3. Instala dependências
if [ -f "$REQ_FILE" ]; then
    echo "[+] Instalando/Atualizando dependências do $REQ_FILE..."
    python -m pip install --upgrade pip
    python -m pip install -r $REQ_FILE
else
    echo "[!] Alerta: $REQ_FILE não encontrado. Pulando instalação."
fi

# 4. Executa o script principal
if [ -f "$SCRIPT_PRINCIPAL" ]; then
    echo "Rodando $SCRIPT_PRINCIPAL..."
    python $SCRIPT_PRINCIPAL
else
    echo "[!] Erro: Nenhum arquivo '$SCRIPT_PRINCIPAL' encontrado para executar."
fi

# Opcional: Desativa ao terminar
# deactivate
