## DÚVIDA: Gabriel, isso era só um teste de script R ou isso realmente é usado no iRace? 

# O irace passa os argumentos em pares: [instance] [ID] [seed] [param_name_1] [valor_1]...
args <- commandArgs(trailingOnly = TRUE)

instance_path <- args[1]
candidate_id <- args[2]
seed <- args[3]
params_irace <- args[4:length(args)]

# Constrói a linha de comando para o Python
# Usamos um loop para passar todos os parâmetros do irace de forma correta
cmd_python <- c(
    "python3",
    "../solvers/solver-sa.py",
    "--nome_instancia", instance_path,
    "--seed", seed,
    "--arq_saida", "temp_saida.txt",
    "--arq_gantt", "temp_gantt.png",
    "--time_limit", "30"
)

# Adiciona os parâmetros do irace a partir do que foi passado
for (i in seq(1, length(params_irace), by = 2)) {
    cmd_python <- c(cmd_python, params_irace[i], params_irace[i+1])
}

# Executa o comando e captura a saída
res <- system(paste(cmd_python, collapse = " "), intern = TRUE)

# A saída do seu solver-sa.py é "custo semente". Capturamos apenas o custo.
output_line <- tail(res, 1)
cost <- strsplit(output_line, " ")[[1]][1]

# Imprime o custo para o irace
cat(cost)