#!/bin/bash

export GUROBI_HOME="/opt/gurobi1202/linux64"
export PATH="${PATH}:${GUROBI_HOME}/bin"
export LD_LIBRARY_PATH="${LD_LIBRARY_PATH}:${GUROBI_HOME}/lib"

if [ -f ~/gurobi.lic ]; then
    echo "O arquivo gurobi.lic já existe."
else
    echo "O arquivo gurobi.lic NÃO existe."

    # importar licença
    grbgetkey c1a01529-61b6-4e54-b791-603adacac76e
fi

echo "########################################"
# testar solver
[ -f ~/gurobi.lic ] && gurobi_cl /opt/gurobi1202/linux64/examples/data/afiro.mps

echo "########################################"
echo /opt/gurobi1202/linux64/bin/gurobi.sh

echo "Pressione ENTER para sair..."
read

