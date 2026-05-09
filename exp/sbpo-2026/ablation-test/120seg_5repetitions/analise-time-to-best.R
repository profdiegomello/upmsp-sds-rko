library(ggplot2)
library(dplyr)

# ==============================================================================
# 1. CARREGAMENTO E PREPARAÇÃO DOS DADOS BASE [cite: 3]
# ==============================================================================
df <- read.table("report-unified_sbpo.dat", header = TRUE, sep = "\t", stringsAsFactors = FALSE)

# Substituir a nomenclatura da estratégia aleatória [cite: 3]
df <- df %>%
  mutate(PARAMETERS = ifelse(PARAMETERS == "Random_Uniform(0,1)", "Baseline", PARAMETERS))

# Definir a ordem dos tratamentos no eixo horizontal [cite: 3]
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

# Ordenar explicitamente o grupo de máquinas [cite: 3]
df$MACHINES <- factor(df$MACHINES, levels = c(10, 15, 20, 25, 30))

# Criar rótulos descritivos para os painéis individuais [cite: 3]
df$LABEL_MAQUINAS <- factor(
  paste("Máquinas:", df$MACHINES),
  levels = paste("Máquinas:", c(10, 15, 20, 25, 30))
)

# Definir paleta de cores fixa (padrão Okabe-Ito) [cite: 3]
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
# 2. GERAÇÃO DOS BOXPLOTS PARA TIMETOBEST
# ==============================================================================

# --- Configuração (i): Boxplot em Grid 1x5 ---
p_grid_1x5 <- ggplot(df, aes(x = PARAMETERS, y = TIMETOBEST, fill = PARAMETERS)) +
  geom_boxplot() +
  scale_fill_manual(values = paleta_cores) +
  facet_wrap(~ LABEL_MAQUINAS, nrow = 1, ncol = 5) +
  theme_bw() +
  theme(
    legend.position = "none",
    axis.text.x = element_text(angle = 90, vjust = 0.5, hjust = 1)
  ) +
  labs(x = "Combinação", y = "Time to Best (s)")

ggsave(filename = "boxplot_ttb_grid_1x5.png", plot = p_grid_1x5, width = 16, height = 5, dpi = 300)

# --- Configuração (ii): Boxplot em Grid 2x3 (Incluindo o painel geral) ---
df_geral <- df %>% mutate(LABEL_MAQUINAS = "Todas as Máquinas")
df_2x3 <- bind_rows(df, df_geral)

df_2x3$LABEL_MAQUINAS <- factor(
  df_2x3$LABEL_MAQUINAS,
  levels = c(paste("Máquinas:", c(10, 15, 20, 25, 30)), "Todas as Máquinas")
)

p_grid_2x3 <- ggplot(df_2x3, aes(x = PARAMETERS, y = TIMETOBEST, fill = PARAMETERS)) +
  geom_boxplot() +
  scale_fill_manual(values = paleta_cores) +
  facet_wrap(~ LABEL_MAQUINAS, nrow = 2, ncol = 3) +
  theme_bw() +
  theme(
    legend.position = "none",
    axis.text.x = element_text(angle = 90, vjust = 0.5, hjust = 1)
  ) +
  labs(x = "Combinação", y = "Time to Best (s)")

ggsave(filename = "boxplot_ttb_grid_2x3.png", plot = p_grid_2x3, width = 12, height = 8, dpi = 300)

# ==============================================================================
# 3. GERAÇÃO DOS INTERVALOS DE CONFIANÇA PARA TIMETOBEST (95%)
# ==============================================================================

df_resumo <- df %>%
  group_by(MACHINES, PARAMETERS) %>%
  summarise(
    n = n(),
    media = mean(TIMETOBEST, na.rm = TRUE),
    desvio = sd(TIMETOBEST, na.rm = TRUE),
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

p_ic_1x5 <- ggplot(df_resumo, aes(x = PARAMETERS, y = media, color = PARAMETERS)) +
  geom_pointrange(aes(ymin = limite_inferior, ymax = limite_superior), size = 0.6) +
  scale_color_manual(values = paleta_cores) +
  facet_wrap(~ LABEL_MAQUINAS, nrow = 1, ncol = 5) +
  theme_bw() +
  theme(
    legend.position = "none",
    axis.text.x = element_text(angle = 90, vjust = 0.5, hjust = 1)
  ) +
  labs(x = "Combinação", y = "Média Time to Best (IC 95%)")

ggsave(filename = "ic_media_ttb_grid_1x5.png", plot = p_ic_1x5, width = 16, height = 5, dpi = 300)

# ==============================================================================
# 4. ANÁLISE DE DIFERENÇA ESTATÍSTICA (TIMETOBEST) [cite: 3]
# ==============================================================================

grupos_maquinas <- c(10, 15, 20, 25, 30)

for (m in grupos_maquinas) {
  df_grupo <- df %>% 
    filter(MACHINES == m) %>%
    group_by(PARAMETERS) %>%
    mutate(block_id = row_number()) %>%
    ungroup() %>%
    arrange(PARAMETERS, block_id)
  
  cat("\n==============================================================================\n")
  cat("ANÁLISE ESTATÍSTICA (TIMETOBEST) - MÁQUINAS:", m, "\n")
  cat("==============================================================================\n")
  
  res_friedman <- friedman.test(TIMETOBEST ~ PARAMETERS | block_id, data = df_grupo)
  cat("Teste de Friedman: p-valor =", sprintf("%g", res_friedman$p.value), "\n")
  
  if (res_friedman$p.value < 0.05) {
    res_wilcox <- pairwise.wilcox.test(
      x = df_grupo$TIMETOBEST, 
      g = df_grupo$PARAMETERS, 
      p.adjust.method = "bonferroni", 
      paired = TRUE, 
      exact = FALSE
    )
    
    cat("\nPares significativos (p-ajustado < 0.05):\n")
    p_mat <- res_wilcox$p.value
    encontrou <- FALSE
    
    for (r in 1:nrow(p_mat)) {
      for (c in 1:ncol(p_mat)) {
        if (!is.na(p_mat[r, c]) && p_mat[r, c] < 0.05) {
          cat(sprintf("  %-10s vs %-10s | p = %g\n", 
                      rownames(p_mat)[r], colnames(p_mat)[c], p_mat[r, c]))
          encontrou <- TRUE
        }
      }
    }
    if (!encontrou) cat("  Nenhuma diferença significativa pós-ajuste.\n")
  }
}
