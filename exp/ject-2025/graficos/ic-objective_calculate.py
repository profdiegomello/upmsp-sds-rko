import pandas as pd
import numpy as np

# --- Carregamento dos Dados ---
# Lê o arquivo CSV original. O delimitador é ponto e vírgula.
try:
    df = pd.read_csv('report.csv', sep=';')
except FileNotFoundError:
    print("Erro: O arquivo 'report.csv' não foi encontrado.")
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
print(f"Análise concluída. Relatório resumido exportado para '{output_filename}'.")

# Exibe as primeiras linhas do DataFrame final para verificação
print("\nAmostra do resultado final resumido:")
print(df_resumido.head(9))