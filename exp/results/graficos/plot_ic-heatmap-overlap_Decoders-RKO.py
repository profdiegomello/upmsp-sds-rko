import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt

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

# Cria os rótulos a partir dos dados já ordenados
unique_configs = df[['JOBS', 'MACHINES']].drop_duplicates()
# configs = (unique_configs['JOBS'].astype(str) + 'j' + '/' + unique_configs['MACHINES'].astype(str) + 'm' ).tolist()
configs = ('(' + unique_configs['JOBS'].astype(str) + ' , ' + unique_configs['MACHINES'].astype(str) + ')' ).tolist()

overlaps = []
decoder_list = ['CHI', 'M3LAW', 'ECT', 'INC', 'KSTS']
decoder_combinations = [ 
    ['CHI', 'M3LAW'] , ['CHI', 'ECT'] #, ['CHI', 'INC'] , ['CHI', 'KSTS'] 
    , ['M3LAW', 'ECT'] #, ['M3LAW', 'INC'], ['M3LAW', 'KSTS']
    # , ['ECT', 'INC'], ['ECT', 'KSTS']
    # , ['INC', 'KSTS']
]
for decoder_pair in decoder_combinations:

    rko_decoder0_ic = df[df['MODEL'] == f'RKO-{decoder_pair[0]}'  ][['IC_SUPERIOR_95', 'IC_INFERIOR_95']].to_records(index=False).tolist()
    rko_decoder1_ic = df[df['MODEL'] == f'RKO-{decoder_pair[1]}'][['IC_SUPERIOR_95', 'IC_INFERIOR_95']].to_records(index=False).tolist()

    # Calcular sobreposição entre intervalos BRKGA e RKO
    decoder_overlap = []
    for (brkga_high, brkga_low), (rko_high, rko_low) in zip(rko_decoder1_ic, rko_decoder0_ic):
        overlap = max(0, min(brkga_high, rko_high) - max(brkga_low, rko_low)) # se tiver sobreposição o valor é positivo, se não tiver é negativo (por isso o max com 0)
        total_range = max(brkga_high, rko_high) - min(brkga_low, rko_low)
        overlap_ratio = 100*(overlap / total_range) if total_range > 0 else 0
        decoder_overlap.append(overlap_ratio)

    # print(f"Decoder Pair {decoder_pair}: Overlap = {decoder_overlap}\n\n")
    overlaps.append(decoder_overlap)

# Criar matriz (1 linha, N colunas)
heatmap_data = np.array(overlaps)


# Plot
fig, ax = plt.subplots(figsize=(12,4))
sns.heatmap(
    heatmap_data, annot=True, fmt=".1f"
    , center=0
    # , cmap="viridis_r"    # 100% seguro para daltonicos, recomendado por revistas
    # , cmap="cividis_r"    # 100% seguro para daltonicos, recomendado por revistas
    
    , cmap="PuOr_r"       # seguro para daltonicos
    # , cmap="plasma_r"     # moderadamente seguro para daltonicos
    # , cmap="inferno_r"     # moderadamente seguro para daltonicos
    # , cmap="coolwarm_r"   # moderadamente seguro para daltonicos

    # , cmap="PiYG"   # ruim para daltônicos, revistas recomendasm viridis, cividis ou plasma
    # , cmap="RdYlGn" # ruim para daltônicos, revistas recomendasm viridis, cividis ou plasma
    # , cmap="RdBu_r" # ruim para daltônicos, revistas recomendasm viridis, cividis ou plasma
    , xticklabels=configs
    , yticklabels=[f"RKO: ({pair[0]} ∩ {pair[1]})" for pair in decoder_combinations]
    , cbar=True
    # , robust=True
)

import matplotlib.ticker as mticker
cbar = ax.collections[0].colorbar
cbar.ax.yaxis.set_major_formatter(mticker.PercentFormatter())

fig.supxlabel('Configuração (Jobs, Machines)', fontsize=10, y=0.02)

fig.suptitle(f'Heatmap de Sobreposição dos ICs 95% entre decoders no RKO', fontsize=12)
ax.set_title("(A ∩ B) como percentual de interseção entre os dos ICs 95% do Makespan", fontsize=8)
# ax.set_title("Heatmap de Sobreposição dos ICs 95% entre decoders no RKO: (A ∩ B)\n\n(valores de 0 a 1 indicam a fração de interseção entre os ICs)")

plt.tight_layout()

# Salva a imagem em um arquivo
plt.savefig(f'Decoders-RKO-IC_heatmap-overlap.png', dpi=300)

# Exibe o gráfico
plt.show()

print(f"\nGráfico salvo como 'Decoders-RKO-IC_heatmap-overlap.png'")