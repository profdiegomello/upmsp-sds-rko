import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt

SORT_BY = 'JOBS'  # Opções: 'JOBS', 'MACHINES', 'RATIO'

try:
    # Carrega o arquivo CSV resumido
    df = pd.read_csv('report_ic_resumido.csv', sep=';')
except FileNotFoundError:
    print("Erro: O arquivo 'report_ic_resumido.csv' não foi encontrado.")
    exit()

# Calcula o ponto médio e o erro
df['PONTO_MEDIO'] = (df['IC_SUPERIOR_95'] + df['IC_INFERIOR_95']) / 2
df['ERRO'] = (df['IC_SUPERIOR_95'] - df['IC_INFERIOR_95']) / 2

# --- ALTERAÇÃO: Ordenação por Razão ---
# Cria uma coluna com a razão para ser usada como chave de ordenação
df['RATIO'] = df['JOBS'] / df['MACHINES']

# Ordena o DataFrame: primeiro pela razão, depois por JOBS e MACHINES para desempate
# df = df.sort_values(by=['RATIO', 'JOBS', 'MACHINES']).reset_index(drop=True)
df = df.sort_values(by=[SORT_BY, 'JOBS', 'MACHINES']).reset_index(drop=True)

# Cria os rótulos a partir dos dados já ordenados
unique_configs = df[['JOBS', 'MACHINES']].drop_duplicates()
configs = (unique_configs['JOBS'].astype(str) + 'j' + '/' + unique_configs['MACHINES'].astype(str) + 'm' ).tolist()

overlaps = []
decoder_list = ['CHI', 'M3LAW', 'ECT']
for decoder in decoder_list:

    rko_ic   = df[df['MODEL'] == f'RKO-{decoder}'  ][['IC_SUPERIOR_95', 'IC_INFERIOR_95']].to_records(index=False).tolist()
    brkga_ic = df[df['MODEL'] == f'BRKGA-{decoder}'][['IC_SUPERIOR_95', 'IC_INFERIOR_95']].to_records(index=False).tolist()

    # Calcular sobreposição entre intervalos BRKGA e RKO
    decoder_overlap = []
    for (brkga_high, brkga_low), (rko_high, rko_low) in zip(brkga_ic, rko_ic):
        overlap = max(0, min(brkga_high, rko_high) - max(brkga_low, rko_low)) # se tiver sobreposição o valor é positivo, se não tiver é negativo (por isso o max com 0)
        total_range = max(brkga_high, rko_high) - min(brkga_low, rko_low)
        overlap_ratio = overlap / total_range if total_range > 0 else 0
        decoder_overlap.append(overlap_ratio)

    overlaps.append(decoder_overlap)

# Criar matriz (1 linha, N colunas)
heatmap_data = np.array(overlaps)


# Plot
fig, ax = plt.subplots(figsize=(12,4))
sns.heatmap(
    heatmap_data, annot=True, fmt=".2f",
    cmap="RdBu_r", center=0, #RdBu_r #seismic #bwr #BuPu
    xticklabels=configs,
    yticklabels=["CHI:   (RKO ∩ BRKGA)", "M3LAW: (RKO ∩ BRKGA)", "ECT:   (RKO ∩ BRKGA)"],
    cbar=True
    # , robust=True
)

ax.set_title("Heatmap de Sobreposição dos ICs 95% do RKO e BRKGA: (A ∩ B)\n\n(valores de 0 a 1 indicam a fração de interseção entre os ICs)")

plt.tight_layout()

# Salva a imagem em um arquivo
plt.savefig(f'RKOvsBRKGA-IC_heatmap-overlap_oderby-{SORT_BY}.png', dpi=300)

# Exibe o gráfico
plt.show()

print(f"\nGráfico salvo como 'RKOvsBRKGA-IC_heatmap-overlap_oderby-{SORT_BY}.png'")