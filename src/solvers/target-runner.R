args <- commandArgs(trailingOnly = TRUE)

instance <- args[1]
candidate_id <- args[2]
params <- args[3:length(args)]

# Parse parameters
param_values <- list()
for (param in params) {
  split_param <- strsplit(param, "=")[[1]]
  param_values[[split_param[1]]] <- split_param[2]
}

# Constrói a linha de comando
cmd <- paste(
  "python",
  "solvers/solver-sa.py",
  paste("--nome_instancia", instance),
  "--arq_saida temp_saida.txt",
  "--arq_gantt temp_gantt.png",
  paste("--time_limit", 30),
  paste("--temp_inicial", param_values$temp_inicial),
  paste("--temp_final", param_values$temp_final),
  paste("--alpha", param_values$alpha),
  paste("--iter_por_temp", param_values$iter_por_temp),
  paste("--p_block", param_values$p_block),
  paste("--block_size", param_values$block_size),
  paste("--p_shift", param_values$p_shift)
)

# Executa o comando e captura a saída
res <- system(cmd, intern = TRUE)

# A última linha da saída deve ser o valor da função objetivo (makespan)
cat(tail(res, 1))
