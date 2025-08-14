library(irace)

scenario <- list(
  parameterFile = "parameters.txt",
  # Aponte para o script shell que executa o resolvedor Python
  targetRunner = "exp/validation/run-sa-irace.sh",
  # O execDir deve ser o diretório raiz do projeto
  execDir = ".",
  trainInstancesDir = "bench/rsdst/small/",
  trainInstancesFile = "instances-list.txt",
  maxExperiments = 1500,
  logFile = "irace.log",
  seed = 12345
)

irace(scenario = scenario)