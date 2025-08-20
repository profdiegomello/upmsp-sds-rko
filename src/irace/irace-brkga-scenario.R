## DÚVIDA: Gabriel, os arquivos scenario.txt e lista_de_instancias.txt são usados ainda? Se não, podemos removê-los?

## OBS.: execute o script scenario.R, que chama o run-XXX-irace.sh, que invoca o script Python do solver

library(irace)

config_scenario <- list(
  parameterFile = "parameters.txt",
  # Aponte para o script shell que executa o resolvedor Python
  targetRunner = "./run-brkga-irace.sh",
  # O execDir deve ser o diretório raiz do projeto
  execDir = ".",
  trainInstancesDir = "../../bench/rsdst/small/",
  trainInstancesFile = "instances-list.txt",
  maxExperiments = 1500,
  logFile = "irace-brkga.log",
  seed = 12345
)

irace(scenario = config_scenario)