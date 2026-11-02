import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

def intervalo_confianca(amostra, alpha=0.05):
    media = np.mean(amostra)
    s = np.std(amostra, ddof=1)
    n = len(amostra)
    
    if n < 30:
        t = stats.t.ppf(1 - alpha/2, df=n-1)
        erro = t * (s / np.sqrt(n))
    else:
        z = stats.norm.ppf(1 - alpha/2)
        erro = z * (s / np.sqrt(n))
    return (media - erro, media + erro)

def carrega(arquivo, decoder, nome):
    d = pd.read_table(arquivo, sep="\t")
    d['INSTANCE'] = d['INSTANCE'].str.extract(r'(I_[^/]+\.txt)')[0]
    d = d[d['PARAMETERS'].str.contains(f"decoder={decoder}$", regex=True)].copy()
    d['MODEL'] = nome
    return d[['INSTANCE', 'MODEL', 'OBJECTIVE']]

df = pd.concat([
    carrega("report-rko__1_.dat", "CHEAPEST", "CHI"),
    carrega("report-rko.dat", "CHEAPEST_NO_LS", "CHI-sem-LS"),
    carrega("report-rko-eroglu.dat", "EROGLU", "Eroglu"),
])

modelos_validos = ['CHI', 'CHI-sem-LS', 'Eroglu']
df = df[df['MODEL'].isin(modelos_validos)]

comuns = df.groupby('INSTANCE')['MODEL'].nunique()
df = df[df['INSTANCE'].isin(comuns[comuns == len(modelos_validos)].index)]
print(f"Instâncias comuns aos três modelos: {df['INSTANCE'].nunique()}")

print("\nEstatísticas descritivas por modelo:")
print(df.groupby('MODEL')['OBJECTIVE'].describe())

modelos = df['MODEL'].unique()

for modelo in modelos:
    gaps = df[df['MODEL'] == modelo]['OBJECTIVE'].values

    print(f"\nEstatísticas para o modelo: {modelo}")
    print(f"Média: {np.mean(gaps):.4f}")
    print(f"Mediana: {np.median(gaps):.4f}")
    print(f"Desvio padrão: {np.std(gaps, ddof=1):.4f}")
    print(f"Variância: {np.var(gaps, ddof=1):.4f}")
    print(f"Amplitude: {np.ptp(gaps)}")
    print(f"Coef. Variação: {np.std(gaps, ddof=1)/np.mean(gaps) * 100:.4f} %")
    print(f"Skewness: {stats.skew(gaps):.4f}")
    print(f"Curtose: {stats.kurtosis(gaps):.4f}")
    
    ic = intervalo_confianca(gaps)
    print(f"IC 95%: ({ic[0]:.4f}, {ic[1]:.4f})")

    print("\nTestes de Normalidade:")
    jb_stat, jb_p = stats.jarque_bera(gaps)
    print(f"Jarque-Bera: estatística = {jb_stat:.4f}, p = {jb_p:.4f}")
    
    ks_stat, ks_p = stats.kstest((gaps - np.mean(gaps)) / np.std(gaps, ddof=1), 'norm')
    print(f"Kolmogorov-Smirnov: estatística = {ks_stat:.4f}, p = {ks_p:.4f}")
    
    ad_result = stats.anderson(gaps, dist='norm')
    print(f"Anderson-Darling: estatística = {ad_result.statistic:.4f}")
    for cv, sig in zip(ad_result.critical_values, ad_result.significance_level):
        print(f"  - nível {sig}%: crítico = {cv:.4f}")

    plt.figure(figsize=(7, 4))
    sns.histplot(gaps, bins=15, kde=True, color='skyblue')
    plt.title(f'Histograma do Makespan - {modelo}')
    plt.xlabel('Makespan')
    plt.ylabel('Frequência')
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(f"histograma_{modelo}.jpg")
    plt.show()

plt.figure(figsize=(8, 5))
sns.boxplot(x='MODEL', y='OBJECTIVE', data=df, palette='Set2', hue='MODEL', legend=False)
plt.title('Comparação de Makespan entre CHI e Eroglu')
plt.ylabel('Makespan')
plt.grid(True, axis='y')
plt.tight_layout()
plt.savefig("boxplot.jpg")
plt.show()

print("\nTestes de comparação entre modelos (não-paramétricos, pareados por instância):")
piv = df.pivot(index='INSTANCE', columns='MODEL', values='OBJECTIVE')

def Teste_Wilcoxon(a, b, nome_a, nome_b):
    stat, p = stats.wilcoxon(piv[a], piv[b], alternative='two-sided')
    dif = ((piv[b] - piv[a]) / piv[a] * 100).mean()
    print(f"\nWilcoxon ({nome_a} vs {nome_b}):")
    print(f"W = {stat:.4f}, p = {p:.4g}")
    print(f"{nome_a} melhor: {(piv[a] < piv[b]).sum()} | {nome_b} melhor: {(piv[b] < piv[a]).sum()} | empates: {(piv[a] == piv[b]).sum()}")
    print(f"Diferença média relativa de {nome_b} sobre {nome_a}: {dif:.2f} %")
    if p < 0.05:
        print("→ Diferença significativa entre as distribuições.")
    else:
        print("→ NÃO há diferença significativa entre as distribuições.")

Teste_Wilcoxon('CHI', 'CHI-sem-LS', "CHI", "CHI-sem-LS")
Teste_Wilcoxon('CHI-sem-LS', 'Eroglu', "CHI-sem-LS", "Eroglu")
