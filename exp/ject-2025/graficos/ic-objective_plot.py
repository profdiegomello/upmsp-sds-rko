import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# --- 1. Carregamento e Preparação dos Dados ---

try:
    # Carrega o arquivo CSV resumido gerado anteriormente
    df = pd.read_csv('report_ic_resumido.csv', sep=';')
except FileNotFoundError:
    print("Erro: O arquivo 'report_ic_resumido.csv' não foi encontrado.")
    print("Por favor, execute o script anterior primeiro para gerar este arquivo.")
    exit()

# Calcula o ponto médio do IC e o tamanho do erro para as barras
df['PONTO_MEDIO'] = (df['IC_SUPERIOR_95'] + df['IC_INFERIOR_95']) / 2
df['ERRO'] = (df['IC_SUPERIOR_95'] - df['IC_INFERIOR_95']) / 2

# Ordena os dados para que o eixo X fique em ordem crescente de JOBS e depois MACHINES
df = df.sort_values(by=['JOBS', 'MACHINES']).reset_index(drop=True)

# Cria os rótulos para o eixo X (ex: '(6, 2)', '(6, 3)', etc.)
# Usamos .drop_duplicates() para ter uma lista única de configurações na ordem correta
unique_configs = df[['JOBS', 'MACHINES']].drop_duplicates()
x_labels = [f'({row.JOBS}, {row.MACHINES})' for index, row in unique_configs.iterrows()]
x_ticks = np.arange(len(x_labels)) # Posições numéricas para os rótulos (0, 1, 2, ...)

# --- 2. Configuração do Gráfico ---

# Define as cores e o offset para cada modelo
model_colors = {'MIP': 'red', 'SA': 'blue', 'BRKGA': 'green'}
model_offsets = {'MIP': -0.2, 'SA': 0, 'BRKGA': 0.2} # Offset para evitar sobreposição
models = ['MIP', 'SA', 'BRKGA']

# Cria a figura e os eixos do gráfico com um tamanho adequado
fig, ax = plt.subplots(figsize=(16, 9))

# --- 3. Plotagem dos Dados ---

# Itera sobre cada modelo para plotá-lo com sua cor e offset
for model in models:
    # Filtra o DataFrame para o modelo atual
    model_df = df[df['MODEL'] == model].reset_index()

    # Mapeia cada configuração (JOBS, MACHINES) para sua posição no eixo X
    # Isso garante que mesmo que uma configuração não tenha dados para um modelo,
    # os outros modelos ainda sejam plotados no lugar certo.
    x_positions = []
    for i, row in model_df.iterrows():
        # Encontra o índice da configuração atual na lista de rótulos
        config_label = f"({row['JOBS']}, {row['MACHINES']})"
        if config_label in x_labels:
            x_positions.append(x_labels.index(config_label))

    # Aplica o offset horizontal à posição de cada ponto
    x_plot = [pos + model_offsets[model] for pos in x_positions]

    # Plota a barra de erro (que representa o IC)
    ax.errorbar(
        x=x_plot,
        y=model_df['PONTO_MEDIO'],
        yerr=model_df['ERRO'],
        fmt='o',  # 'o' para mostrar o ponto médio
        color=model_colors[model],
        label=model,
        capsize=5, # Tamanho do traço nas extremidades do IC
        linestyle='None', # Não ligar os pontos com uma linha
        elinewidth=1.5, # Espessura da linha do IC
        markersize=5 # Tamanho do marcador do ponto médio
    )

# --- 4. Customização e Exibição ---

# Melhora a aparência do gráfico
ax.set_title('Intervalo de Confiança 95% para Objective por Configuração', fontsize=18, pad=20)
ax.set_ylabel('IC 95%: Objective', fontsize=14)
ax.set_xlabel('Configuração (Jobs, Machines)', fontsize=14)

# Define os rótulos do eixo X e rotaciona para evitar sobreposição
ax.set_xticks(x_ticks)
ax.set_xticklabels(x_labels, rotation=45, ha='right')

ax.legend(title='Modelo', fontsize=12) # Adiciona a legenda
ax.grid(True, which='both', linestyle='--', linewidth=0.5) # Adiciona um grid
fig.tight_layout() # Ajusta o layout para que nada seja cortado

# Salva a imagem em um arquivo
plt.savefig('grafico_intervalos_confianca.png', dpi=300)

# Exibe o gráfico
plt.show()

print("\nGráfico gerado e salvo como 'grafico_intervalos_confianca.png'")