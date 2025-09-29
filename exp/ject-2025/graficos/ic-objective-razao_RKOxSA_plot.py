import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# --- 1. Carregamento e Preparação dos Dados ---

try:
    df = pd.read_csv('report_ic_resumido.csv', sep=';')
except FileNotFoundError:
    print("Erro: O arquivo 'report_ic_resumido.csv' não foi encontrado.")
    exit()

# --- CORREÇÃO ADICIONADA ---
# Garante que as colunas-chave sejam do tipo inteiro para evitar inconsistências.
# Esta é a correção principal para o problema do DataFrame vazio.
df['JOBS'] = df['JOBS'].astype(int)
df['MACHINES'] = df['MACHINES'].astype(int)

# Calcula o ponto médio do IC e o erro
df['PONTO_MEDIO'] = (df['IC_SUPERIOR_95'] + df['IC_INFERIOR_95']) / 2
df['ERRO'] = (df['IC_SUPERIOR_95'] - df['IC_INFERIOR_95']) / 2

# --- 2. Lógica de Ordenação (sem alterações) ---

# Passo A: Isolar os dados de SA e RKO
df_sa = df[df['MODEL'] == 'SA']
df_RKO = df[df['MODEL'] == 'RKO']

# Passo B: Juntar os dados para ter SA e RKO lado a lado
df_ratios = pd.merge(
    df_sa[['JOBS', 'MACHINES', 'PONTO_MEDIO']],
    df_RKO[['JOBS', 'MACHINES', 'PONTO_MEDIO']],
    on=['JOBS', 'MACHINES'],
    how='inner',
    suffixes=('_SA', '_RKO')
)

# Passo C: Calcular a razão de desempenho
epsilon = 1e-9
df_ratios['SORT_RATIO'] = df_ratios['PONTO_MEDIO_RKO'] / (df_ratios['PONTO_MEDIO_SA'] + epsilon)

# Passo D: Ordenar as configurações pela razão
configs_sorted = df_ratios.sort_values(by='SORT_RATIO', ascending=True)

# --- 3. Aplicação da Nova Ordem ---

# Passo E: Criar a lista de rótulos do eixo X na ordem correta
ordered_x_labels = [f'({int(row.JOBS)}, {int(row.MACHINES)})' for _, row in configs_sorted.iterrows()]
if not ordered_x_labels:
    print("Nenhuma configuração em comum entre SA e RKO foi encontrada. Não é possível gerar o gráfico.")
    exit()

# Passo F: Filtrar o DataFrame original (agora deve funcionar corretamente)
df['CONFIG_LABEL'] = [f'({row.JOBS}, {row.MACHINES})' for _, row in df.iterrows()]
df_filtered = df[df['CONFIG_LABEL'].isin(ordered_x_labels)].copy()

# Passo G: Aplicar a ordem ao DataFrame filtrado
df_filtered['CONFIG_LABEL'] = pd.Categorical(df_filtered['CONFIG_LABEL'], categories=ordered_x_labels, ordered=True)
df_final_sorted = df_filtered.sort_values('CONFIG_LABEL')


# --- 4. Geração do Gráfico ---

model_colors = {'MIP': 'red', 'RKO': 'green',   'SA': 'blue'}
model_offsets = {'MIP': -0.2, 'RKO': 0,       'SA': 0.2}
models = ['MIP', 'RKO', 'SA']

fig, ax = plt.subplots(figsize=(14, 8))
x_ticks = np.arange(len(ordered_x_labels))

for model in models:
    model_df = df_final_sorted[df_final_sorted['MODEL'] == model]
    
    x_positions = [ordered_x_labels.index(label) for label in model_df['CONFIG_LABEL']]
    x_plot = [pos + model_offsets[model] for pos in x_positions]

    ax.errorbar(
        x=x_plot, y=model_df['PONTO_MEDIO'], yerr=model_df['ERRO'],
        fmt='o', color=model_colors[model], label=model,
        capsize=5, linestyle='None', elinewidth=1.5, markersize=5
    )

# --- 5. Customização e Exibição ---

ax.set_title('Desempenho Relativo do RKO, SA e MIP para métrica Makespan', fontsize=18, pad=20)
ax.set_ylabel('IC 95% do Makespan (em escala logarítmica)', fontsize=14)
ax.set_xlabel('Grupo de Instâncias (Tarefas, Máquinas)\n\nOBS.: ordenadas pela razão (RKO/SA) dos Pontos Médios do IC', fontsize=14)

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

ax.set_xticks(x_ticks)
ax.set_xticklabels(ordered_x_labels, rotation=45, ha='right')

crossover_point = (configs_sorted['SORT_RATIO'] >= 1).sum() - 0.5
if crossover_point < len(ordered_x_labels) - 1:
    ax.axvline(x=crossover_point, color='grey', linestyle='--', linewidth=2, label='Razão (RKO/SA) = 1')

ax.legend(title='Modelo', fontsize=12)
ax.grid(True, which='both', linestyle='--', linewidth=0.5)
fig.tight_layout()

plt.savefig('grafico_ordenado_por_desempenho_relativo_RKO-SA.png', dpi=300)
plt.show()

print("\nGráfico de desempenho relativo (versão final) salvo como 'grafico_ordenado_por_desempenho_relativo_RKO-SA.png'")