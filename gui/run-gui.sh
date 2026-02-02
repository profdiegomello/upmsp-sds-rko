#!/bin/bash

# PYTHON_VERSION="python3.12"
PYTHON_VERSION="python3"
VERSION="${PYTHON_VERSION#python}"

VENV_DIR=".venv"
REQ_FILE="requirements.txt"
SCRIPT_PRINCIPAL="main.py"

echo "--- Verificador de Ambiente Python ---"
if ! $PYTHON_VERSION --version &> /dev/null ;
then
    echo "[x] Erro: $PYTHON_VERSION não está instalado. Por favor, instale-o e tente novamente."
    exit 1
else 
    echo "[✓] $PYTHON_VERSION está instalado."
fi

if $PYTHON_VERSION -c "import _tkinter" &> /dev/null ; then
  echo "[✓] Tkinter está instalado corretamente no sistema operacional."
  $PYTHON_VERSION -c "import tkinter; print(tkinter.__file__)"
else
  echo "[x] Erro: Tkinter não encontrado."
  echo "[!] Aviso: necessita do python-tk@$VERSION instalado no sistema para funcionamento correto da GUI. Por favor, instale-o e tente novamente."
  exit 1
fi

# 1. Verifica se a pasta .venv existe, se não, cria
if [ ! -d "$VENV_DIR" ]; then
    echo "[!] Ambiente virtual não encontrado. Criando em $VENV_DIR..."
    $PYTHON_VERSION -m venv $VENV_DIR
else
    echo "[✓] Ambiente virtual detectado."
fi

# 2. Ativa o ambiente
echo "[+] Ativando ambiente..."
source $VENV_DIR/bin/activate

# 3. Instala dependências
if [ -f "$REQ_FILE" ]; then
    echo "[+] Instalando/Atualizando dependências do $REQ_FILE..."
    $PYTHON_VERSION -m pip install --upgrade pip
    $PYTHON_VERSION -m pip install -r $REQ_FILE
else
    echo "[!] Alerta: $REQ_FILE não encontrado. Pulando instalação."
fi

# 4. Executa o script principal
if [ -f "$SCRIPT_PRINCIPAL" ]; then
    echo "Rodando $SCRIPT_PRINCIPAL..."
    $PYTHON_VERSION $SCRIPT_PRINCIPAL
else
    echo "[x] Erro: Nenhum arquivo '$SCRIPT_PRINCIPAL' encontrado para executar."
    exit 1
fi

# Opcional: Desativa ao terminar
# deactivate
