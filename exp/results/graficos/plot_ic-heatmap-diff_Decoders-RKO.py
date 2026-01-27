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
configs = (unique_configs['JOBS'].astype(str) + 'j' + '/' + unique_configs['MACHINES'].astype(str) + 'm' ).tolist()


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

# Médios dos ICs já calculados
rko_chi_mean   = [(low+high)/2 for (low,high) in rko_chi  ]
brkga_chi_mean = [(low+high)/2 for (low,high) in brkga_chi]

rko_m3law_mean   = [(low+high)/2 for (low,high) in rko_m3law  ]
brkga_m3law_mean = [(low+high)/2 for (low,high) in brkga_m3law]

rko_ect_mean   = [(low+high)/2 for (low,high) in rko_ect  ]
brkga_ect_mean = [(low+high)/2 for (low,high) in brkga_ect]

rko_inc_mean   = [(low+high)/2 for (low,high) in rko_inc  ]

# Diferenças dos pontos médios dos ICs
diffs = [
    [a - b for a, b in zip(rko_chi_mean, rko_m3law_mean)], 
    [a - b for a, b in zip(rko_chi_mean, rko_ect_mean)], 
    # [a - b for a, b in zip(rko_chi_mean, rko_inc_mean)], 
    [a - b for a, b in zip(rko_m3law_mean, rko_ect_mean)], 
    # [a - b for a, b in zip(rko_m3law_mean, rko_inc_mean)], 
    # [a - b for a, b in zip(rko_ect_mean, rko_inc_mean)]    
]

# Criar matriz para heatmap
heatmap_data = np.array(diffs)

# Plot
fig, ax = plt.subplots(figsize=(12,4))
sns.heatmap(
    heatmap_data, annot=True, fmt=".1f",
    cmap="RdBu_r", center=0,
    xticklabels=configs,
    yticklabels=["RKO: (CHI - M3LAW)", 
                 "RKO: (CHI - ECT)", 
                 # "RKO: (CHI - INC)", 
                 "RKO: (M3LAW - ECT)" 
                 #, "RKO: (M3LAW - INC)", 
                 # "RKO: (ECT - INC)" 
                 ],
    cbar=True
    # , robust=True
)

ax.set_title("Heatmap das Diferenças dos Pontos Médios dos ICs 95% entre decoders no RKO: (A - B)\n\ncores frias (valor negativo): decoder A é melhor, cores quentes (valor positivo): decoder B é melhor.")
plt.tight_layout()

# Salva a imagem em um arquivo
plt.savefig('Decoders-RKO-IC_heatmap-diff.png', dpi=300)

# Exibe o gráfico
plt.show()

print("\nGráfico salvo como 'Decoders-RKO-IC_heatmap-diff.png'")