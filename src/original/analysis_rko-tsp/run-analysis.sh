#!/bin/bash

# listas de parâmetros
# agentes=("vns" "ils" "lns" "ga" "brkga" "grasp" "pso" "sa") ## OBS.: agente pso está gerando resultados ruins ainda, agente sa não está respeitando o tempo limite
agentes=("vns" "ils" "lns" "ga" "brkga" "grasp" "brkga,ils,grasp" "brkga,lns" "grasp,ils,vns" "ga,grasp" "ils,lns,vns" "brkga,ga,grasp,ils,lns,vns")

# instancias=("eil51" "a280" "att48" "kroA200")
instancias=("eil51" "a280")

for instancia in "${instancias[@]}"; do
  for agente in "${agentes[@]}"; do

    mkdir -p "./${instancia}"
    logfile="./${instancia}/${instancia}_${agente}.log"

    if [ -s "$logfile" ]; then
      echo "Pulando $agente em $instancia (log já existe: $logfile)"
      continue
    fi

    echo "Executando $agente em $instancia..."
    ## OBS.: precisei desabilitar o buffer do stdout do python (-u) para os prints aparecerem em tempo real no terminal
    PYTHONUNBUFFERED=1 python3 -u ../rko-tsp/rko-tsp-complete.py --agents "$agente" ../rko-tsp/"$instancia".tsp | tee "$logfile" #2>&1
    mv "${instancia}-solution.png" "./${instancia}/${instancia}_${agente}-solution.png"
  done
  ## Gerar gráfico
  python3 plot-logs-rko-tsp.py "./${instancia}/" "${instancia}"
done

