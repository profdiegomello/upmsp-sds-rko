import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import math

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

# --- ALTERAÇÃO: Nova Estratégia de Agrupamento ---
# Agrupa arredondando a razão para o 0.5 mais próximo.
df['RATIO_GROUP'] = (df['JOBS'] / df['MACHINES'] * 2).round() / 2

df['RATIO_GROUP'] = df['RATIO_GROUP'].clip(upper=6) ## arredonda tudo acima de 6 para 6

# Ordena os dados pelo grupo, e depois por JOBS e MACHINES
df = df.sort_values(by=['RATIO_GROUP', 'JOBS', 'MACHINES']).reset_index(drop=True)

# Identifica os grupos únicos para criar os subplots
ratio_groups = sorted(df['RATIO_GROUP'].unique())
n_groups = len(ratio_groups)

# --- 2. Configuração das Subfiguras ---

# Determina o layout da grade de subplots
n_cols = 3 
n_rows = math.ceil(n_groups / n_cols)

# Cria a figura e os eixos dos subplots
fig, axes = plt.subplots(
    nrows=n_rows,
    ncols=n_cols,
    figsize=(n_cols * 6, n_rows * 2.5), # Aumenta um pouco a altura
    sharex=False,
    sharey=False
)
axes = axes.flatten()

# --- 3. Plotagem Iterativa em cada Subfigura ---

# Define as cores e o offset para cada modelo
model_colors =  {'SA': 'blue',   'RKO': 'green',    'BRKGA': 'olive',   'RKGA': 'coral',  'MIP': 'red'}
model_offsets = {'SA': -0.2,     'RKO': -0.1,           'BRKGA': 0,       'RKGA': 0.1,       'MIP': 0.2}
# models = ['SA', 'RKO', 'BRKGA', 'RKGA', 'MIP']
models = ['SA', 'RKO', 'BRKGA', 'RKGA']

for i, group_val in enumerate(ratio_groups):
    ax = axes[i]
    group_df = df[df['RATIO_GROUP'] == group_val]
    unique_configs = group_df[['JOBS', 'MACHINES']].drop_duplicates()
    x_labels = [f'({row.JOBS}, {row.MACHINES})' for _, row in unique_configs.iterrows()]
    x_ticks = np.arange(len(x_labels))

    for model in models:
        model_df = group_df[group_df['MODEL'] == model].reset_index()
        if not model_df.empty:
            x_positions = [x_labels.index(f"({row['JOBS']}, {row['MACHINES']})") for _, row in model_df.iterrows()]
            x_plot = [pos + model_offsets[model] for pos in x_positions]

            ax.errorbar(
                x=x_plot, y=model_df['PONTO_MEDIO'], yerr=model_df['ERRO'],
                fmt='o', color=model_colors[model], label=model,
                capsize=5, linestyle='None', elinewidth=1.5, markersize=5
            )

    # --- ALTERAÇÃO: Formato do Título do Subplot ---
    # Garante que o título mostre o valor com uma casa decimal (ex: 2.0, 2.5)
    ax.set_title(f'Razão N/M ≈ {group_val:.1f}', fontsize=10)
    ax.set_xticks(x_ticks)
    ax.set_xticklabels(x_labels, rotation=0, ha='right')
    ax.grid(True, which='both', linestyle='--', linewidth=0.5)

# --- 4. Customização e Finalização da Figura ---

for i in range(n_groups, len(axes)):
    axes[i].axis('off')

handles, labels = ax.get_legend_handles_labels()
# fig.legend(handles, labels, loc='upper center', bbox_to_anchor=(0.5, 0.98), ncol=3, title='Política', fontsize=12)
fig.legend(handles, labels, loc='lower right', bbox_to_anchor=(1, 0), ncol=3, title='Política', fontsize=12)

fig.suptitle('Desempenho de {SA,RKO,BRKGA,RKGA,MIP} para métrica Makespan', fontsize=18)

fig.supxlabel('Grupo de Instâncias: (Tarefas, Máquinas)', fontsize=14, y=0.02)
fig.supylabel('IC 95%: Objective', fontsize=14, x=0.04)

fig.tight_layout(rect=[0.05, 0.05, 1, 0.94])

plt.savefig('grafico_subplots_por_razao_0.5.png', dpi=300)
plt.show()

print("\nGráfico com nova estratégia de agrupamento salvo como 'grafico_subplots_por_razao_0.5.png'")