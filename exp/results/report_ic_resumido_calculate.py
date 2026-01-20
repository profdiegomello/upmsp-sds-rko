import pandas as pd
import numpy as np

# --- Carregamento dos Dados ---
# Lê o arquivo DAT original. O delimitador é tabulação
try:
    # df = pd.read_csv('../ject-2025/graficos/report-small.csv', sep=';', decimal='.', header=0)
    # df = pd.read_csv('report-rko-unified.dat', sep='\t', decimal='.', header=0)
    df = pd.read_csv('report-all-unified.dat', sep='\t', decimal='.', header=0)

    # keep only columns of interest: JOBS, MACHINES, MODEL, OBJECTIVE, RUNTIME
    df = df[['JOBS', 'MACHINES', 'MODEL', 'OBJECTIVE', 'RUNTIME']]
    print("\n[DEBUG] Amostra de dados do arquivo 'report-brkga-rko-unified.dat':")
    print(df)

    #count how many times each combination of JOBS, MACHINES, MODEL appears
    counts = df.groupby(['JOBS', 'MACHINES', 'MODEL']).size()
    print("\n[DEBUG] Contagem de ocorrências por combinação de JOBS, MACHINES e MODEL:")
    print(counts)

except FileNotFoundError:
    print("Erro: O arquivo 'report-rko-unified.dat' não foi encontrado.")
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
# O resultado é uma série com um MultiIndex (JOBS, MACHINES, MODEL).
# O .unstack() transforma o resultado em um DataFrame.
ci_results = df.groupby(['JOBS', 'MACHINES', 'MODEL'])['OBJECTIVE'].apply(bootstrap_ci).unstack()

# 2. Converte o índice em colunas
# O método .reset_index() transforma os níveis do índice (JOBS, MACHINES, MODEL)
# em colunas, criando o formato de DataFrame resumido desejado.
df_resumido = ci_results.reset_index()

# --- Exportação do Resultado ---
# Salva o DataFrame resumido em um novo arquivo CSV.
output_filename = 'report_ic_resumido.csv'
df_resumido.to_csv(output_filename, sep=';', index=False, decimal='.')
print(f"Análise concluída. Relatório IC bootstrap exportado para '{output_filename}'.")

# Exibe as primeiras linhas do DataFrame final para verificação
print("\nAmostra do resultado final IC bootstrap:")
print(df_resumido)