import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# --- 1. Carregamento e Preparação dos Dados ---

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
df = df.sort_values(by=['RATIO', 'JOBS', 'MACHINES']).reset_index(drop=True)

# --- 2. Configuração do Gráfico Único ---

# Cria os rótulos para o eixo X a partir dos dados já ordenados
unique_configs = df[['JOBS', 'MACHINES']].drop_duplicates()
x_labels = [f'({row.JOBS}, {row.MACHINES})' for index, row in unique_configs.iterrows()]
x_ticks = np.arange(len(x_labels))

# Define as cores e o offset para cada modelo
model_colors =  {'SA': 'blue',   'RKO': 'green',    'BRKGA': 'olive',   'RKGA': 'coral',  'MIP': 'red'}
model_offsets = {'SA': -0.2,     'RKO': -0.1,           'BRKGA': 0,       'RKGA': 0.1,       'MIP': 0.2}
models = ['SA', 'RKO', 'BRKGA', 'RKGA', 'MIP']

# Cria a figura e os eixos do gráfico (agora apenas um)
# Aumentamos bastante a largura para acomodar todos os pontos
fig, ax = plt.subplots(figsize=(14, 8))

# --- 3. Plotagem dos Dados na Figura Única ---

# Itera sobre cada modelo para plotá-lo com sua cor e offset
for model in models:
    # Filtra o DataFrame (já ordenado) para o modelo atual
    model_df = df[df['MODEL'] == model]

    # Mapeia cada configuração (JOBS, MACHINES) para sua posição no eixo X
    x_positions = [x_labels.index(f"({row['JOBS']}, {row['MACHINES']})") for _, row in model_df.iterrows()]
    
    # Aplica o offset horizontal
    x_plot = [pos + model_offsets[model] for pos in x_positions]

    # Plota a barra de erro
    ax.errorbar(
        x=x_plot,
        y=model_df['PONTO_MEDIO'],
        yerr=model_df['ERRO'],
        fmt='o',  # 'o' para mostrar o ponto médio
        color=model_colors[model],
        label=model,
        capsize=5,
        linestyle='None',
        elinewidth=1.5,
        markersize=5
    )

# --- 4. Customização e Exibição ---

ax.set_title('Desempenho de {SA,RKO,BRKGA,RKGA,MIP} para métrica Makespan', fontsize=18, pad=20)
ax.set_ylabel('IC 95% do Makespan (em escala logarítmica)', fontsize=14)
ax.set_xlabel('Grupo de Instâncias (Tarefas, Máquinas)\n\nOBS.: ordenadas pela razão Tarefas/Máquinas', fontsize=14)

# --- Definir a escala do eixo Y para logarítmica ---
ax.set_yscale('log')
# --- Formatar os rótulos do eixo Y ---
# Força os rótulos a serem números normais (ex: 500) em vez de notação científica (5x10²)
# Isso melhora muito a legibilidade do eixo logarítmico.
# from matplotlib.ticker import ScalarFormatter
# ax.yaxis.set_major_formatter(ScalarFormatter())
# Opcional: Se o matplotlib ainda escolher ticks ruins, você pode forçá-los manualmente.
# y_ticks_manual = [50, 75, 100, 150, 200, 300, 500, 700]
# ax.set_yticks(y_ticks_manual)

# Define os rótulos do eixo X e rotaciona para evitar sobreposição
ax.set_xticks(x_ticks)
ax.set_xticklabels(x_labels, rotation=45, ha='right')

ax.legend(title='Política', fontsize=12)
ax.grid(True, which='both', linestyle='--', linewidth=0.5)
fig.tight_layout()

# Salva a imagem em um arquivo
plt.savefig('grafico_ordenado_por_razaoJobMachine.png', dpi=300)

# Exibe o gráfico
plt.show()

print("\nGráfico único ordenado por razão salvo como 'grafico_ordenado_por_razaoJobMachine.png'")