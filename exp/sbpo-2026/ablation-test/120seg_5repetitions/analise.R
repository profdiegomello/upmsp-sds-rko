library(ggplot2)
library(dplyr)

# ==============================================================================
# 1. CARREGAMENTO E PREPARAÇÃO DOS DADOS BASE
# ==============================================================================
df <- read.table("report-unified_sbpo.dat", header = TRUE, sep = "\t", stringsAsFactors = FALSE)

# Substituir a nomenclatura da estratégia aleatória
df <- df %>%
  mutate(PARAMETERS = ifelse(PARAMETERS == "Random_Uniform(0,1)", "Baseline", PARAMETERS))

# Definir a ordem dos tratamentos no eixo horizontal
ordem_parametros <- c(
  "Baseline",
  "GA",
  "ILS",
  "VNS",
  "GA,ILS",
  "GA,VNS",
  "VNS,ILS",
  "GA,VNS,ILS"
)

df$PARAMETERS <- factor(df$PARAMETERS, levels = ordem_parametros)

# Ordenar explicitamente o grupo de máquinas
df$MACHINES <- factor(df$MACHINES, levels = c(10, 15, 20, 25, 30))

# Criar rótulos descritivos para os painéis individuais
df$LABEL_MAQUINAS <- factor(
  paste("Máquinas:", df$MACHINES),
  levels = paste("Máquinas:", c(10, 15, 20, 25, 30))
)

# Definir paleta de cores fixa (padrão Okabe-Ito)
paleta_cores <- c(
  "Baseline"   = "#999999",
  "GA"         = "#E69F00",
  "ILS"        = "#56B4E9",
  "VNS"        = "#009E73",
  "GA,ILS"     = "#F0E442",
  "GA,VNS"     = "#0072B2",
  "VNS,ILS"    = "#D55E00",
  "GA,VNS,ILS" = "#CC79A7"
)

# ==============================================================================
# 2. GERAÇÃO DOS BOXPLOTS
# ==============================================================================

# --- Configuração (i): Boxplot em Grid 1x5 (Apenas subgrupos) ---
p_grid_1x5 <- ggplot(df, aes(x = PARAMETERS, y = GAP, fill = PARAMETERS)) +
  geom_boxplot() +
  scale_fill_manual(values = paleta_cores) +
  facet_wrap(~ LABEL_MAQUINAS, nrow = 1, ncol = 5) +
  theme_bw() +
  theme(
    legend.position = "none",
    axis.text.x = element_text(angle = 90, vjust = 0.5, hjust = 1)
  ) +
  labs(x = "Combinação", y = "Gap")

ggsave(filename = "boxplot_gap_grid_1x5.png", plot = p_grid_1x5, width = 16, height = 5, dpi = 300)

# --- Configuração (ii): Boxplot em Grid 2x3 (Incluindo o painel geral) ---
# Criar cópia dos dados agregando todas as observações em um único rótulo
df_geral <- df %>% mutate(LABEL_MAQUINAS = "Todas as Máquinas")

# Unificar a base original com a base agregada
df_2x3 <- bind_rows(df, df_geral)

# Definir a ordem dos painéis garantindo o geral na sexta posição
df_2x3$LABEL_MAQUINAS <- factor(
  df_2x3$LABEL_MAQUINAS,
  levels = c(paste("Máquinas:", c(10, 15, 20, 25, 30)), "Todas as Máquinas")
)

p_grid_2x3 <- ggplot(df_2x3, aes(x = PARAMETERS, y = GAP, fill = PARAMETERS)) +
  geom_boxplot() +
  scale_fill_manual(values = paleta_cores) +
  facet_wrap(~ LABEL_MAQUINAS, nrow = 2, ncol = 3) +
  theme_bw() +
  theme(
    legend.position = "none",
    axis.text.x = element_text(angle = 90, vjust = 0.5, hjust = 1)
  ) +
  labs(x = "Combinação", y = "Gap")

ggsave(filename = "boxplot_gap_grid_2x3.png", plot = p_grid_2x3, width = 12, height = 8, dpi = 300)

# ==============================================================================
# 3. GERAÇÃO DOS INTERVALOS DE CONFIANÇA (95%)
# ==============================================================================

# Calcular a média, erro padrão e os limites do IC de 95%
df_resumo <- df %>%
  group_by(MACHINES, PARAMETERS) %>%
  summarise(
    n = n(),
    media = mean(GAP, na.rm = TRUE),
    desvio = sd(GAP, na.rm = TRUE),
    .groups = "drop"
  ) %>%
  mutate(
    erro_padrao = desvio / sqrt(n),
    t_critico = qt(0.975, df = n - 1),
    limite_inferior = media - (t_critico * erro_padrao),
    limite_superior = media + (t_critico * erro_padrao),
    LABEL_MAQUINAS = factor(
      paste("Máquinas:", MACHINES),
      levels = paste("Máquinas:", c(10, 15, 20, 25, 30))
    )
  )

# Gerar o plot de intervalos de confiança em grid 1x5
p_ic_1x5 <- ggplot(df_resumo, aes(x = PARAMETERS, y = media, color = PARAMETERS)) +
  geom_pointrange(aes(ymin = limite_inferior, ymax = limite_superior), size = 0.6) +
  scale_color_manual(values = paleta_cores) +
  facet_wrap(~ LABEL_MAQUINAS, nrow = 1, ncol = 5) +
  theme_bw() +
  theme(
    legend.position = "none",
    axis.text.x = element_text(angle = 90, vjust = 0.5, hjust = 1)
  ) +
  labs(
    x = "Combinação",
    y = "Média do Gap (IC 95%)"
  )

ggsave(filename = "ic_media_gap_grid_1x5.png", plot = p_ic_1x5, width = 16, height = 5, dpi = 300)

# ==============================================================================
# 4. ANÁLISE DE DIFERENÇA ESTATÍSTICA
# ==============================================================================

grupos_maquinas <- c(10, 15, 20, 25, 30)

for (m in grupos_maquinas) {
  # Filtrar e preparar os dados mantendo a ordenação correta para o pareamento
  df_grupo <- df %>% 
    filter(MACHINES == m) %>%
    group_by(PARAMETERS) %>%
    mutate(block_id = row_number()) %>%
    ungroup() %>%
    arrange(PARAMETERS, block_id)
  
  cat("\n==============================================================================\n")
  cat("ANÁLISE ESTATÍSTICA - MÁQUINAS:", m, "\n")
  cat("==============================================================================\n")
  
  # Teste de Friedman
  res_friedman <- friedman.test(GAP ~ PARAMETERS | block_id, data = df_grupo)
  cat("Teste de Friedman: p-valor =", sprintf("%g", res_friedman$p.value), "\n")
  
  if (res_friedman$p.value < 0.05) {
    cat("Diferença global detectada. Executando Wilcoxon signed rank test com Bonferroni...\n")
    
    # Pairwise Wilcoxon signed rank test
    res_wilcox <- pairwise.wilcox.test(
      x = df_grupo$GAP, 
      g = df_grupo$PARAMETERS, 
      p.adjust.method = "bonferroni", 
      paired = TRUE, 
      exact = FALSE
    )
    
    cat("\nPares com diferença estatisticamente significativa (p-ajustado < 0.05):\n")
    p_mat <- res_wilcox$p.value
    encontrou_diferenca <- FALSE
    
    for (r in 1:nrow(p_mat)) {
      for (c in 1:ncol(p_mat)) {
        if (!is.na(p_mat[r, c]) && p_mat[r, c] < 0.05) {
          cat(sprintf("  %-10s vs %-10s | p-ajustado = %g\n", 
                      rownames(p_mat)[r], colnames(p_mat)[c], p_mat[r, c]))
          encontrou_diferenca <- TRUE
        }
      }
    }
    
    if (!encontrou_diferenca) {
      cat("  Nenhum par apresentou diferença significativa após o ajuste de Bonferroni.\n")
    }
  } else {
    cat("Nenhuma diferença global detectada pelo teste de Friedman.\n")
  }
}
