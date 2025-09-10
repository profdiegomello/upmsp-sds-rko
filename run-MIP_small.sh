#!/usr/bin/env bash

source ~/.venv/bin/activate

cd ./exp/ject-2025/
./small_verifica-naoprocessados-duplicados.sh
./run-mip-benchmark.sh ../../bench/benchmark/small/ 1200
