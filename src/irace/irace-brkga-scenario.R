## DÚVIDA: Gabriel, os arquivos scenario.txt e lista_de_instancias.txt são usados ainda? Se não, podemos removê-los?

## OBS.: execute o script scenario.R, que chama o run-brkga.sh, que invoca o script Python do solver

library(irace)

config_scenario <- list(
  parameterFile = "src/irace/irace-brkga-parameters_v2.txt",
  # Aponte para o script shell que executa o resolvedor Python
  targetRunner = "./src/irace/run-brkga.sh",
  # O execDir deve ser o diretório raiz do projeto
  execDir = ".",
  trainInstancesDir = "bench/rsdst/",
  trainInstancesFile = "src/irace/instances-list.txt",
  maxExperiments = 1500,
  logFile = "output/irace-brkga.log",
  seed = 12345
)

irace(scenario = config_scenario)

#OBS.: no R, leia o logFile do iRace com: 
#            results <- readIrace("nome_do_logFile")