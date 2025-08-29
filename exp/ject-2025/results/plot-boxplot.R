# Instala e carrega o pacote ggplot2
if (!require(ggplot2)) {
  install.packages("ggplot2")
  library(ggplot2)
}

# ---
# Leitura dos dados
# ---
# Define o nome do arquivo
file_path <- "report-mh.dat"

# Lê o arquivo, ignorando o cabeçalho inicial
data <- read.table(file_path, header = TRUE, fill = TRUE, stringsAsFactors = FALSE)

# ---
# Limpeza e preparação dos dados
# ---
# Remove linhas com valores ausentes ou não numéricos nas colunas OBJECTIVE e RUNTIME
data <- data[complete.cases(data$OBJECTIVE, data$RUNTIME) & 
             !is.na(as.numeric(data$OBJECTIVE)) & 
             !is.na(as.numeric(data$RUNTIME)), ]
data$OBJECTIVE <- as.numeric(data$OBJECTIVE)
data$RUNTIME <- as.numeric(data$RUNTIME)

# Extrai o "grupo" do nome do arquivo (INSTANCE)
# O padrão 'I_\\d+_\\d+_S_\\d+-\\d+_\\d+' captura as partes relevantes
data$GROUP <- sub("^.*/(I_\\d+_\\d+_S_\\d+-\\d+_).*", "\\1", data$INSTANCE)

# ---
# Geração e salvamento do boxplot de OBJECTIVE
# ---
plot_objective <- ggplot(data, aes(x = MODEL, y = OBJECTIVE, fill = MODEL)) +
  geom_boxplot() +
  facet_wrap(~ GROUP, scales = "free_y") + # Separa os gráficos por grupo
  scale_fill_manual(values = c("SA" = "yellow", "BRKGA" = "cyan")) + # Define as cores dos boxplots
  labs(
    title = "Comparação dos Objetivos por Grupo e Modelo",
    x = "Modelo",
    y = "Valor do Objetivo"
  ) +
  theme_minimal() + # Estilo do tema
  theme(
    axis.text.x = element_text(angle = 45, hjust = 1), # Gira os nomes dos modelos
    plot.title = element_text(hjust = 0.5), # Centraliza o título
    plot.background = element_rect(fill = "white") # Define o fundo branco
  )

# Salva o gráfico em um arquivo
ggsave("boxplot-objective.png", plot = plot_objective, width = 10, height = 8)

# ---
# Geração e salvamento do boxplot de RUNTIME
# ---
plot_runtime <- ggplot(data, aes(x = MODEL, y = RUNTIME, fill = MODEL)) +
  geom_boxplot() +
  facet_wrap(~ GROUP, scales = "free_y") + # Separa os gráficos por grupo
  scale_fill_manual(values = c("SA" = "yellow", "BRKGA" = "cyan")) + # Define as cores dos boxplots
  labs(
    title = "Comparação dos Tempos de Execução por Grupo e Modelo",
    x = "Modelo",
    y = "Tempo de Execução (s)"
  ) +
  theme_minimal() + # Estilo do tema
  theme(
    axis.text.x = element_text(angle = 45, hjust = 1), # Gira os nomes dos modelos
    plot.title = element_text(hjust = 0.5), # Centraliza o título
    plot.background = element_rect(fill = "white") # Define o fundo branco
  )

# Salva o gráfico em um arquivo
ggsave("boxplot-runtime.png", plot = plot_runtime, width = 10, height = 8)
