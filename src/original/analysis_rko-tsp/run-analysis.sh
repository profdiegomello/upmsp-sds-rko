#!/bin/bash

# listas de parâmetros
# heuristicas=("vns" "ils" "lns" "ga" "brkga" "grasp" "pso" "sa")
heuristicas=("vns" "ils" "lns" "ga" "brkga" "grasp" "brkga,ils,grasp" "brkga,lns" "grasp,ils,vns" "ga,grasp")

# instancias=("eil51" "a280" "att48" "kroA200")
instancias=("eil51" "a280")

for instancia in "${instancias[@]}"; do
  for heuristica in "${heuristicas[@]}"; do

    mkdir -p "./${instancia}"
    logfile="./${instancia}/${instancia}_${heuristica}.log"

    if [ -s "$logfile" ]; then
      echo "Pulando $heuristica em $instancia (log já existe: $logfile)"
      continue
    fi

    echo "Executando $heuristica em $instancia..."
    PYTHONUNBUFFERED=1 python3 -u ../rko-tsp/rko-tsp-complete.py --agents "$heuristica" ../rko-tsp/"$instancia".tsp | tee "$logfile" #2>&1
    mv "${instancia}-solution.png" "./${instancia}/${instancia}_${heuristica}-solution.png"
  done
  ## Gerar gráfico
  python3 plot-logs-rko-tsp.py "./${instancia}/" "${instancia}"
done

