"""
Passo 1 (revisão PODES): gera o CSV de IC 95% (bootstrap) incluindo os modelos novos.

Coloque nesta pasta (junto com o script):
  - report-all-unified.dat      (RKO-*, BRKGA-*, MIP)
  - report-rko.dat              (RKO com CHEAPEST sem busca local)  -> modelo RKO-CHI-SLS
  - report-rko-eroglu.dat       (RKO com decoder Eroglu)            -> modelo RKO-EROGLU
  - sa-santos.dat               (SA do Santos et al.)               -> modelo SA-SANTOS
(os três últimos estão em exp/PODES Review/)

Saídas:
  - report_ic_resumido.csv           (JOBS;MACHINES;MODEL;IC_INFERIOR_95;IC_SUPERIOR_95)  -> mover para a pasta graficos/
  - report_comparacoes_pareadas.csv  (vitórias/empates/derrotas e diferença média por instância)
"""
import re
import numpy as np
import pandas as pd

SEED = 42                  # reprodutibilidade do bootstrap (use None para não fixar)
EROGLU_SO_DECODER_EROGLU = True   # report-rko-eroglu.dat tem 104 linhas com decoder=ECT; True = descarta essas linhas
DEDUP_BRKGA_ECT = True            # report-all-unified.dat tem 87 instâncias duplicadas em BRKGA-ECT; True = mantém a 1ª ocorrência

if SEED is not None:
    np.random.seed(SEED)

COLS = ['INSTANCE', 'JOBS', 'MACHINES', 'MODEL', 'OBJECTIVE', 'RUNTIME']

def le(path):
    d = pd.read_csv(path, sep='\t', decimal='.')
    d = d.rename(columns={'MACHINE': 'MACHINES'})               # PODES usa MACHINE
    d['INSTANCE'] = d['INSTANCE'].astype(str).str.split('/').str[-1]  # tira prefixo de pasta
    return d

# --- base unificada ---
base = le('report-all-unified.dat')
if DEDUP_BRKGA_ECT:
    antes = len(base)
    base = base.drop_duplicates(subset=['INSTANCE', 'MODEL'], keep='first')
    print(f"[INFO] Duplicatas removidas (INSTANCE+MODEL): {antes - len(base)}")

# --- modelos da revisão ---
chi_sls = le('report-rko.dat')
chi_sls['MODEL'] = 'RKO-CHI-SLS'

ero = le('report-rko-eroglu.dat')
ero['DEC'] = ero['PARAMETERS'].str.extract(r'decoder=(\w+)')[0]
print(f"[INFO] report-rko-eroglu.dat: {ero['DEC'].value_counts().to_dict()}")
if EROGLU_SO_DECODER_EROGLU:
    ero = ero[ero['DEC'] == 'EROGLU']
# instâncias do benchmark (as 600 do report-rko.dat) que NÃO têm resultado válido do Eroglu -> precisam ser reexecutadas
faltam = sorted(set(chi_sls['INSTANCE']) - set(ero['INSTANCE']))
open('instancias_eroglu_a_reexecutar.txt', 'w').write('\n'.join(faltam) + '\n')
print(f"[ATENÇÃO] {len(faltam)} instâncias sem resultado válido do Eroglu -> instancias_eroglu_a_reexecutar.txt")
ero['MODEL'] = 'RKO-EROGLU'

sa = le('sa-santos.dat')
sa['MODEL'] = 'SA-SANTOS'

df = pd.concat([base[COLS], chi_sls[COLS], ero[COLS], sa[COLS]], ignore_index=True)
print(df.groupby('MODEL').size())

# --- IC bootstrap (igual ao script original) ---
def bootstrap_ci(data, n=1000, conf=0.95):
    a = np.array(data)
    if len(a) < 2:
        return pd.Series([np.nan, np.nan], index=['IC_INFERIOR_95', 'IC_SUPERIOR_95'])
    means = [np.mean(np.random.choice(a, size=len(a), replace=True)) for _ in range(n)]
    al = (1 - conf) / 2
    return pd.Series([np.percentile(means, al * 100), np.percentile(means, (1 - al) * 100)],
                     index=['IC_INFERIOR_95', 'IC_SUPERIOR_95'])

ci = df.groupby(['JOBS', 'MACHINES', 'MODEL'])['OBJECTIVE'].apply(bootstrap_ci).unstack().reset_index()
ci.to_csv('report_ic_resumido.csv', sep=';', index=False, decimal='.')
print("[OK] report_ic_resumido.csv")

# --- comparações pareadas por instância (menor makespan = melhor) ---
PARES = [('RKO-CHI', 'RKO-CHI-SLS'),      # com busca local  vs  sem busca local
         ('RKO-CHI-SLS', 'RKO-EROGLU'),   # CHI sem busca local vs Eroglu
         ('RKO-CHI', 'RKO-EROGLU'),
         ('RKO-CHI', 'SA-SANTOS'),
         ('RKO-CHI-SLS', 'SA-SANTOS'),
         ('RKO-EROGLU', 'SA-SANTOS')]
piv = df.pivot_table(index='INSTANCE', columns='MODEL', values='OBJECTIVE', aggfunc='first')
linhas = []
for a, b in PARES:
    s = piv[[a, b]].dropna()
    diff = s[a] - s[b]
    linhas.append({'A': a, 'B': b, 'INSTANCIAS_COMUNS': len(s),
                   'A_MELHOR': int((diff < 0).sum()), 'EMPATE': int((diff == 0).sum()), 'B_MELHOR': int((diff > 0).sum()),
                   'MEDIA_A': round(s[a].mean(), 2), 'MEDIA_B': round(s[b].mean(), 2),
                   'DIF_REL_MEDIA_%': round(100 * (s[a].mean() - s[b].mean()) / s[b].mean(), 2)})
res = pd.DataFrame(linhas)
res.to_csv('report_comparacoes_pareadas.csv', sep=';', index=False)
print(res.to_string(index=False))
