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
# configs = (unique_configs['JOBS'].astype(str) + 'j' + '/' + unique_configs['MACHINES'].astype(str) + 'm' ).tolist()
configs = ('(' + unique_configs['JOBS'].astype(str) + ' , ' + unique_configs['MACHINES'].astype(str) + ')').tolist()


# models = [  'RKO-CHI' , 'BRKGA-CHI'
#           , 'RKO-M3LAW'    , 'BRKGA-M3LAW'
#           , 'RKO-ECT'      , 'BRKGA-ECT'
#          ]

# Dados extraídos do arquivo (IC 95% bootstrap)

rko_chi   = df[df['MODEL'] == 'RKO-CHI'  ][['IC_SUPERIOR_95', 'IC_INFERIOR_95']].to_records(index=False).tolist()
brkga_chi = df[df['MODEL'] == 'BRKGA-CHI'][['IC_SUPERIOR_95', 'IC_INFERIOR_95']].to_records(index=False).tolist()

rko_m3law   = df[df['MODEL'] == 'RKO-M3LAW'  ][['IC_SUPERIOR_95', 'IC_INFERIOR_95']].to_records(index=False).tolist()
brkga_m3law = df[df['MODEL'] == 'BRKGA-M3LAW'][['IC_SUPERIOR_95', 'IC_INFERIOR_95']].to_records(index=False).tolist()

rko_ect   = df[df['MODEL'] == 'RKO-ECT'  ][['IC_SUPERIOR_95', 'IC_INFERIOR_95']].to_records(index=False).tolist()
brkga_ect = df[df['MODEL'] == 'BRKGA-ECT'][['IC_SUPERIOR_95', 'IC_INFERIOR_95']].to_records(index=False).tolist()

rko_inc   = df[df['MODEL'] == 'RKO-INC'  ][['IC_SUPERIOR_95', 'IC_INFERIOR_95']].to_records(index=False).tolist()
brkga_inc = df[df['MODEL'] == 'BRKGA-INC'][['IC_SUPERIOR_95', 'IC_INFERIOR_95']].to_records(index=False).tolist()

# Médios dos ICs já calculados
rko_chi_mean   = [(low+high)/2 for (low,high) in rko_chi  ]
brkga_chi_mean = [(low+high)/2 for (low,high) in brkga_chi]

rko_m3law_mean   = [(low+high)/2 for (low,high) in rko_m3law  ]
brkga_m3law_mean = [(low+high)/2 for (low,high) in brkga_m3law]

rko_ect_mean   = [(low+high)/2 for (low,high) in rko_ect  ]
brkga_ect_mean = [(low+high)/2 for (low,high) in brkga_ect]

rko_inc_mean   = [(low+high)/2 for (low,high) in rko_inc  ]
brkga_inc_mean = [(low+high)/2 for (low,high) in brkga_inc]

# Diferenças dos pontos médios dos ICs
gains = [
    [((b - a)/a)*100 for a, b in zip(rko_chi_mean, brkga_chi_mean)],      
    [((b - a)/a)*100 for a, b in zip(rko_m3law_mean, brkga_m3law_mean)],  
    [((b - a)/a)*100 for a, b in zip(rko_ect_mean, brkga_ect_mean)]#, 
    # [((b - a)/a)*100 for a, b in zip(rko_inc_mean, brkga_inc_mean)]
]

# Criar matriz para heatmap
heatmap_data = np.array(gains)

# Plot
fig, ax = plt.subplots(figsize=(12,4))
sns.heatmap(
    heatmap_data, annot=True, fmt=".1f"
    , center=0
    
    # , cmap="viridis_r"    # 100% seguro para daltonicos, recomendado por revistas
    # , cmap="cividis_r"    # 100% seguro para daltonicos, recomendado por revistas
    
    # , cmap="PuOr"       # seguro para daltonicos
    # , cmap="PuOr_r"     # seguro para daltonicos
    # , cmap="plasma_r"   # moderadamente seguro para daltonicos
    , cmap="coolwarm_r"   # moderadamente seguro para daltonicos

    # , cmap="PiYG"   # ruim para daltônicos, revistas recomendasm viridis, cividis ou plasma
    # , cmap="RdYlGn" # ruim para daltônicos, revistas recomendasm viridis, cividis ou plasma
    # , cmap="RdBu_r" # ruim para daltônicos, revistas recomendasm viridis, cividis ou plasma

    , xticklabels=configs
    # , yticklabels=["CHI:   (BRKGA-RKO)/RKO", "M3LAW: (BRKGA-RKO)/RKO", "ECT:   (BRKGA-RKO)/RKO"]
    , yticklabels=["CHI:   (RKO vs BRKGA)", "M3LAW: (RKO vs BRKGA)", "ECT:   (RKO vs BRKGA)"] #, "INC:   (RKO vs BRKGA)"]
    , cbar=True
    # , robust=True
)

import matplotlib.ticker as mticker
cbar = ax.collections[0].colorbar
cbar.ax.yaxis.set_major_formatter(mticker.PercentFormatter())

fig.supxlabel('Grupo de Instâncias: (Tarefas, Máquinas)', fontsize=10, y=0.02)

fig.suptitle(f'Heatmap da % de Ganho Relativo do RKO vs BRKGA', fontsize=12)
ax.set_title("(B - A)/A do Ponto Médio dos ICs 95%\n\nOBS.: valor positivo: RKO é melhor, valor negativo: BRKGA é melhor", fontsize=8)
plt.tight_layout()

# Salva a imagem em um arquivo
plt.savefig(f'RKOvsBRKGA-IC_heatmap-gain_oderby-{SORT_BY}.png', dpi=300)

# Exibe o gráfico
plt.show()

print(f"\nGráfico salvo como 'RKOvsBRKGA-IC_heatmap-gain_oderby-{SORT_BY}.png'")