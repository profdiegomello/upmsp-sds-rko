#!/usr/bin/env bash

source ~/.venv/bin/activate

cd ./exp/ject-2025/
./verifica-naoprocessados-duplicados.sh
./run-mip-benchmark.sh ../../bench/benchmark/medium/ 1200
