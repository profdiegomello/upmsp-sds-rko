import pandas as pd
import numpy as np

# --- Carregamento dos Dados ---
# Lê o arquivo DAT original. O delimitador é tabulação

# FILENAME = 'report-rko.dat'
FILENAME = 'report-all-unified.dat'

try:
    df = pd.read_csv(FILENAME, sep='\t', decimal='.', header=0)

    # a coluna INSTANCE contém uma string no formato: "I_{JOBS}_{MACHINES}_S_{SETUPTIME}_{REPETITION}.txt" , quero extrair SETUPTIME e REPETITION como novas colunas do df
    def extract_setuptime_repetition(instance_str):
        parts = instance_str.split('_')
        setuptime = parts[4].replace('1-', '')  # índice 4 corresponde a SETUPTIME
        repetition = parts[5].split('.')[0]  # índice 5 corresponde a REPETITION, removendo a extensão .txt
        return pd.Series([setuptime, repetition])
    df[['SETUPTIME', 'REPETITION']] = df['INSTANCE'].apply(extract_setuptime_repetition)
    df['SETUPTIME'] = df['SETUPTIME'].astype(int)
    df['REPETITION'] = df['REPETITION'].astype(int)

    # print("\n[DEBUG] Amostra de dados após extração de SETUPTIME e REPETITION:")
    # print(df.head())    

    # keep only columns of interest: JOBS, MACHINES, MODEL, OBJECTIVE, RUNTIME
    df = df[['JOBS', 'MACHINES', 'SETUPTIME', 'REPETITION', 'MODEL', 'OBJECTIVE']]

    # ordenenar numericamente por 'JOBS', 'MACHINES', 'SETUPTIME', 'MODEL', 'REPETITION', 'OBJECTIVE'
    df = df.sort_values(by=['JOBS', 'MACHINES', 'SETUPTIME', 'MODEL', 'REPETITION', 'OBJECTIVE']).reset_index()
    print(f"\n[DEBUG] Amostra de dados do arquivo {FILENAME} processado:")
    print(df.head(10))    

    #count how many times each combination of JOBS, MACHINES, MODEL appears
    counts = df.groupby(['SETUPTIME', 'MODEL']).size()
    # print("\n[DEBUG] Contagem de ocorrências por combinação de JOBS, MACHINES, SETUPTIME e MODEL:")
    # print(counts)
    # exit(1)

    # para cada grupo de ['JOBS', 'MACHINES', 'SETUPTIME'], ordene por ['OBJECTIVE','MODEL'] e mantenha apenas a linha com o menor OBJECTIVE (melhor solução)
    df_best = df.sort_values(by=['OBJECTIVE', 'MODEL']).groupby(['JOBS', 'MACHINES', 'SETUPTIME']).first()
    df_best = df_best.reset_index()
    df_best = df_best[['JOBS', 'MACHINES', 'SETUPTIME', 'REPETITION', 'MODEL', 'OBJECTIVE']]
    print(f"\n[DEBUG] Amostra de dados após manter apenas a melhor solução por grupo de JOBS, MACHINES e SETUPTIME:")
    print(df_best)

except FileNotFoundError:
    print(f"Erro: O arquivo '{FILENAME}' não foi encontrado.")
    exit()

# --- Função para Bootstrap do Intervalo de Confiança (sem alterações) ---
def bootstrap_ci(data, n_bootstrap_samples=1000, confidence_level=0.95):
    """
    Calcula o intervalo de confiança da média para uma amostra de dados usando bootstrap.
    """
    data_array = np.array(data)
    if len(data_array) < 2:
        return pd.Series([np.nan, np.nan], index=['IC_INFERIOR_95', 'IC_SUPERIOR_95'])

    bootstrap_means = []
    for _ in range(n_bootstrap_samples):
        sample = np.random.choice(data_array, size=len(data_array), replace=True)
        bootstrap_means.append(np.mean(sample))

    alpha = (1 - confidence_level) / 2.0
    lower_bound = np.percentile(bootstrap_means, alpha * 100)
    upper_bound = np.percentile(bootstrap_means, (1 - alpha) * 100)

    return pd.Series([lower_bound, upper_bound], index=['IC_INFERIOR_95', 'IC_SUPERIOR_95'])

# --- Processamento e Criação do Resumo ---
print("Calculando o intervalo de confiança para cada grupo...")

# 1. Agrupa os dados e aplica a função de bootstrap
# O resultado é uma série com um MultiIndex (JOBS, MACHINES, MODEL, SETUPTIME).
# O .unstack() transforma o resultado em um DataFrame.
ci_results = df.groupby(['JOBS', 'MACHINES', 'SETUPTIME', 'MODEL'])['OBJECTIVE'].apply(bootstrap_ci).unstack()

# 2. Converte o índice em colunas
# O método .reset_index() transforma os níveis do índice (JOBS, MACHINES, MODEL, SETUPTIME)
# em colunas, criando o formato de DataFrame resumido desejado.
df_resumido = ci_results.reset_index()

# --- Exportação do Resultado ---
# Salva o DataFrame resumido em um novo arquivo CSV.
output_filename = 'report_ic_setuptimes.csv'
df_resumido.to_csv(output_filename, sep=';', index=False, decimal='.')
print(f"Análise concluída. Relatório IC bootstrap exportado para '{output_filename}'.")

# Exibe as primeiras linhas do DataFrame final para verificação
print("\nAmostra do resultado final IC bootstrap:")
print(df_resumido)