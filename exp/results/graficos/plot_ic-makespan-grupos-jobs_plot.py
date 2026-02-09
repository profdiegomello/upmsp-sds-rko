import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import math

OFFSET_IC_MODELOS = True
SET_SAME_Y_SCALE_FOR_GROUPS = False

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

# Agrupa pela quantidade de jobs (parece divergir mais o RKO e BRKGA do que em relação à Razão N/M).
df['GROUP'] = df['JOBS']

# Ordena os dados pelo grupo, e depois por JOBS e MACHINES
df = df.sort_values(by=['GROUP', 'JOBS', 'MACHINES']).reset_index(drop=True)

# Identifica os grupos únicos para criar os subplots
groups = sorted(df['GROUP'].unique())
n_groups = len(groups)

# --- 2. Configuração das Subfiguras ---

# Determina o layout da grade de subplots
n_cols = 3
# n_cols = 1
n_rows = math.ceil(n_groups / n_cols)

# Cria a figura e os eixos dos subplots
fig, axes = plt.subplots(
    nrows=n_rows,
    ncols=n_cols,
    # figsize=(n_cols * 3, n_rows * 5), 
    # figsize=(n_cols * 6, n_rows * 3),
    figsize=(8,5),
    sharex=False,
    sharey=False
)
axes = axes.flatten()

# --- 3. Plotagem Iterativa em cada Subfigura ---

# Define as cores e o offset para cada modelo

## APENAS os RKO-Decoders 
# model_colors =  {'RKO-CHI': 'blue',   'RKO-M3LAW': 'green',    'RKO-ECT': 'olive',   'RKO-INC': 'coral',  'RKO-KSTS': 'red'}
# model_offsets = {'RKO-CHI': -0.2, 'RKO-M3LAW': -0.1, 'RKO-ECT': 0, 'RKO-INC': 0.1, 'RKO-KSTS': 0.2}
# models = ['RKO-CHI', 'RKO-M3LAW', 'RKO-ECT', 'RKO-INC', 'RKO-KSTS']

## MIP, SA, BRKGA e RKO-Decoders
# model_colors =  {'SA': 'magenta', 'BRKGA': 'blue', 'RKO-CHI': 'green',   'RKO-M3LAW': 'olive',    'RKO-ECT': 'darkseagreen',   'RKO-INC': 'yellowgreen' }#,  'RKO-KSTS': 'coral' , 'MIP': 'red'}
# model_offsets = {'SA': -0.4, 'BRKGA': -0.3, 'RKO-CHI': -0.2, 'RKO-M3LAW': -0.1, 'RKO-ECT': 0, 'RKO-INC': 0.1 }#, 'RKO-KSTS': 0.2 , 'MIP': 0.3}
# models = ['SA', 'BRKGA', 'RKO-CHI', 'RKO-M3LAW', 'RKO-ECT', 'RKO-INC'] #, 'RKO-KSTS' , 'MIP']

## MIP, SA, RKO-Decoders e BRKGA-Decoders
model_colors =  {   #  'RKO-CHI': 'green',   'RKO-M3LAW': 'olive',    'RKO-ECT': 'darkseagreen',   'RKO-INC': 'yellowgreen' ,  'RKO-KSTS': 'lime' 
                       'RKO-CHI': 'blue',   'RKO-M3LAW': 'cornflowerblue',    'RKO-ECT': 'deepskyblue',   'RKO-INC': 'lightskyblue' ,  'RKO-KSTS': 'steelblue'
                    ,  'SA': 'magenta' 
                    #, 'BRKGA-CHI': 'blue',   'BRKGA-M3LAW': 'cornflowerblue',    'BRKGA-ECT': 'deepskyblue',   'BRKGA-INC': 'lightskyblue' ,  'BRKGA-KSTS': 'cyan'
                    , 'BRKGA-CHI': 'red',   'BRKGA-M3LAW': 'indianred',    'BRKGA-ECT': 'coral',   'BRKGA-INC': 'firebrick' ,  'BRKGA-KSTS': 'darkred'
                    , 'MIP': 'gray'
                }
model_offsets = {     'RKO-CHI': 0.0, 'RKO-M3LAW': 0.2, 'RKO-ECT': 0.4, 'RKO-INC': 0.6 , 'RKO-KSTS': 0.8 
                    , 'MIP': 0.0 #, 'MIP': 0.8
                    , 'BRKGA-CHI': 0.0, 'BRKGA-M3LAW': 0.2, 'BRKGA-ECT': 0.4, 'BRKGA-INC': 0.6 , 'BRKGA-KSTS': 0.8
                    , 'SA': 0.8
                }
models = [    #'MIP', 
        
        #    'RKO-CHI'      , 'BRKGA-CHI'
        #  , 'RKO-M3LAW'    , 'BRKGA-M3LAW'
        #  , 'RKO-ECT'      , 'BRKGA-ECT'
        #  , 'RKO-INC'      , 'BRKGA-INC'
        #   , 'RKO-KSTS'     , 'BRKGA-KSTS' 
        
        'RKO-CHI', 'RKO-M3LAW', 'RKO-ECT'#, 'RKO-INC'
        #, 'BRKGA-CHI', 'BRKGA-M3LAW', 'BRKGA-ECT'#, 'BRKGA-INC'
        
        #   , 'SA'
         ]


for i, group_val in enumerate(groups):
    ax = axes[i]
    group_df = df[df['GROUP'] == group_val]
    unique_configs = group_df[['JOBS', 'MACHINES']].drop_duplicates()

    if SET_SAME_Y_SCALE_FOR_GROUPS:
        # --- Valores máximos da escala Y para os grupos ficarem na mesma escala ---
        jobs_val = unique_configs['JOBS'].iloc[0]
        # ymax_por_jobs = {100: 350, 150: 550, 200: 750} # RKO
        # ymax_por_jobs = {100: 400, 150: 650, 200: 900} # BRKGA
        # ymax_por_jobs = {100: 700, 150: 550, 200: 750} # MIP

        #TODO migrar o cálculo automático do ymax_por_jobs para os demais scripts de plotagem
        # verificar o valor máximo de IC_SUPERIOR_95 para o grupo atual filtrando MODEL pelos models para cada valor de JOBS, montar um dicionário JOBS -> max_objective
        max_objective_dict = {}
        for jobs in unique_configs['JOBS'].unique():
            max_objective = df[(df['MODEL'].isin(models)) & (df['JOBS'] == jobs)]['IC_SUPERIOR_95'].max()
            max_objective_dict[jobs] = max_objective * 1.1 # adicionar uma margem de 10%
        ymax_por_jobs = max_objective_dict 

        if jobs_val in ymax_por_jobs:
            ax.set_ylim(0, ymax_por_jobs[jobs_val])

    # --------------------------------

    # x_labels = [f'({row.JOBS}, {row.MACHINES})' for _, row in unique_configs.iterrows()]
    x_labels = [f'{row.MACHINES}' for _, row in unique_configs.iterrows()]
    x_ticks = np.arange(len(x_labels))
    ax.set_xlabel("Quantidade de Máquinas", fontsize=8)

    for model in models:
        model_df = group_df[group_df['MODEL'] == model].reset_index()
        if not model_df.empty:
            # x_positions = [x_labels.index(f"({row['JOBS']}, {row['MACHINES']})") for _, row in model_df.iterrows()]
            x_positions = [x_labels.index(f"{row['MACHINES']}") for _, row in model_df.iterrows()]

            if OFFSET_IC_MODELOS: 
                x_plot = [pos + model_offsets[model] for pos in x_positions]
            else:
                x_plot = x_positions

            ax.errorbar(
                x=x_plot, y=model_df['PONTO_MEDIO'], yerr=model_df['ERRO'],
                fmt='o', color=model_colors[model], label=model,
                # capsize=5, linestyle='None', elinewidth=1.5, markersize=5
                capsize=5, elinewidth=1.0, markersize=2, linestyle=':', linewidth=0.5
            )

    ax.set_title(f'Quantidade de Tarefas = {group_val}', fontsize=9)
    ax.set_xticks(x_ticks)
    ax.set_xticklabels(x_labels, rotation=0, ha='center', fontsize=8)
    ax.grid(True, which='both', linestyle='--', linewidth=0.5)

# --- 4. Customização e Finalização da Figura ---

for i in range(n_groups, len(axes)):
    axes[i].axis('off')

# handles, labels = ax.get_legend_handles_labels()
handles, labels = axes[0].get_legend_handles_labels()

# fig.legend(handles, labels, loc='upper center', bbox_to_anchor=(0.5, 0.98), ncol=3, title='Política', fontsize=12)
# fig.legend(handles, labels, loc='lower right', bbox_to_anchor=(1, 0), ncol=3, title='Política', fontsize=8)
fig.legend(handles, labels, loc='right', bbox_to_anchor=(.98, 0.65), ncol=1, title='Política', fontsize=8)

# fig.suptitle(f'Desempenho do RKO vs BRKGA (mesmas políticas de sequenciamento) para métrica Makespan', fontsize=12)
fig.suptitle(f'Desempenho das políticas de sequenciamento no RKO para métrica Makespan', fontsize=12)
# fig.suptitle(f'Desempenho das políticas de sequenciamento no BRKGA para métrica Makespan', fontsize=12)


# fig.supxlabel('Instâncias agrupadas por quantidade de máquinas', fontsize=14, y=0.02)
fig.supylabel('IC 95% do Makespan', fontsize=14, x=0.04)

fig.tight_layout(rect=[0.05, 0.05, 1, 0.94])

plt.savefig('grafico_agrupado_por_jobs.png', dpi=300)
plt.show()

print("\nGráfico com nova estratégia de agrupamento salvo como 'grafico_agrupado_por_jobs.png'")