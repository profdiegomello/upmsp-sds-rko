#!/bin/bash

# Nome do ambiente virtual
VENV_DIR=".venv"
REQ_FILE="requirements.txt"

echo "--- Verificador de Ambiente Python ---"

# 1. Verifica se a pasta .venv existe, se não, cria
if [ ! -d "$VENV_DIR" ]; then
    echo "[!] Ambiente virtual não encontrado. Criando em $VENV_DIR..."
    python3 -m venv $VENV_DIR
else
    echo "[✓] Ambiente virtual detectado."
fi

# 2. Ativa o ambiente
echo "[+] Ativando ambiente..."
source $VENV_DIR/bin/activate

# 3. Verifica se o requirements.txt existe e instala as dependências
if [ -f "$REQ_FILE" ]; then
    echo "[+] Instalando/Atualizando dependências do $REQ_FILE..."
    pip install --upgrade pip
    pip install -r $REQ_FILE
else
    echo "[!] Alerta: $REQ_FILE não encontrado. Pulando instalação."
fi

# 4. Executa o script principal (ajuste o nome do seu arquivo .py aqui)
# Se você tiver um script principal, mude 'seu_script.py' abaixo:
SCRIPT_PRINCIPAL="main.py"

if [ -f "$SCRIPT_PRINCIPAL" ]; then
    echo "Rodando $SCRIPT_PRINCIPAL..."
    python3 $SCRIPT_PRINCIPAL
else
    echo "[!] Erro: Nenhum arquivo '$SCRIPT_PRINCIPAL' encontrado para executar."
fi

# Opcional: Desativa ao terminar
# deactivate
