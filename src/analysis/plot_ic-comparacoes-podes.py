"""
Passo 2 (revisão PODES): plots de IC 95% do makespan por grupo de jobs (x = nº de máquinas).
Rode dentro da pasta graficos/, com o report_ic_resumido.csv do passo 1.

Escolha a comparação em COMPARACAO (ou comente/descomente), ou use 'todas' para gerar as três.
"""
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

COMPARACAO = 'todas'   # 'chi_com_vs_sem_ls' | 'chi_sem_ls_vs_eroglu' | 'chi_vs_sa_santos' | 'quatro_alternativas' | 'todas'

PRESETS = {
    # 1) CHI com busca local  x  CHI sem busca local
    'chi_com_vs_sem_ls':    ['RKO-CHI', 'RKO-CHI-SLS'],
    # 2) CHI sem busca local  x  Eroglu
    'chi_sem_ls_vs_eroglu': ['RKO-CHI-SLS', 'RKO-EROGLU'],
    # 3) SA do Santos et al.  x  CHI (com e sem busca local)
    'chi_vs_sa_santos':     ['RKO-CHI', 'RKO-CHI-SLS', 'SA-SANTOS'],
    # Experimento IV (as 4 alternativas): CHI, CHI sem busca local, Eroglu e Santos
    'quatro_alternativas':  ['RKO-CHI', 'RKO-CHI-SLS', 'RKO-EROGLU', 'SA-SANTOS'],
}
CORES = {'RKO-CHI': 'blue', 'RKO-CHI-SLS': 'deepskyblue', 'RKO-EROGLU': 'green', 'SA-SANTOS': 'magenta'}
ROTULOS = {'RKO-CHI': 'RKO-CHI (com busca local)', 'RKO-CHI-SLS': 'RKO-CHI (sem busca local)',
           'RKO-EROGLU': 'RKO-Eroglu', 'SA-SANTOS': 'SA (Santos et al.)'}

df = pd.read_csv('report_ic_resumido.csv', sep=';')
df['PONTO_MEDIO'] = (df['IC_SUPERIOR_95'] + df['IC_INFERIOR_95']) / 2
df['ERRO'] = (df['IC_SUPERIOR_95'] - df['IC_INFERIOR_95']) / 2

def plota(nome, models):
    groups = sorted(df['JOBS'].unique())
    fig, axes = plt.subplots(1, len(groups), figsize=(3.4 * len(groups) + 1.5, 4), sharey=False)
    axes = np.atleast_1d(axes)
    passo = 0.8 / max(len(models), 1)
    for ax, jobs in zip(axes, groups):
        g = df[df['JOBS'] == jobs]
        maqs = sorted(g['MACHINES'].unique())
        for k, m in enumerate(models):
            d = g[g['MODEL'] == m].sort_values('MACHINES')
            if d.empty:
                continue
            x = [maqs.index(v) + k * passo for v in d['MACHINES']]
            ax.errorbar(x, d['PONTO_MEDIO'], yerr=d['ERRO'], fmt='o', color=CORES[m], label=ROTULOS[m],
                        capsize=5, elinewidth=1.0, markersize=2, linestyle=':', linewidth=0.5)
        ax.set_xticks(np.arange(len(maqs)) + passo * (len(models) - 1) / 2)
        ax.set_xticklabels(maqs, fontsize=8)
        ax.set_xlabel('Quantidade de Máquinas', fontsize=8)
        ax.set_title(f'Quantidade de Tarefas = {jobs}', fontsize=9)
        ax.grid(True, linestyle='--', linewidth=0.5)
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc='lower center', ncol=len(models), fontsize=8)
    fig.supylabel('IC 95% do Makespan', fontsize=11)
    fig.tight_layout(rect=[0.02, 0.1, 1, 1])
    out = f'comparacao_{nome}.png'
    fig.savefig(out, dpi=300)
    plt.close(fig)
    print(f"[OK] {out}")

for nome, models in PRESETS.items():
    if COMPARACAO in ('todas', nome):
        plota(nome, models)
