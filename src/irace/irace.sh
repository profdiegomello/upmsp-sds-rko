#!/bin/bash
docker build --tag irace -f Dockerfile_R ./ \
  && docker run --rm -it --name irace --volume ./output:/app/output irace \
    bash -c "Rscript src/irace/irace-sa-scenario.R"
    # bash -c "Rscript src/irace/irace-brkga-scenario.R"

## se precisar liberar espaço em disco, apague o cache do docker build: 
# docker builder prune