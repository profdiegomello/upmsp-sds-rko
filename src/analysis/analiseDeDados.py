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

df = pd.read_table("instancias_simuladas.csv", sep=",")

modelos_validos = ['Gurobi', 'BRKGA', 'SA']
df = df[df['MODEL'].isin(modelos_validos)]

print("\nEstatísticas descritivas por modelo:")
print(df.groupby('MODEL')['GAP'].describe())

modelos = df['MODEL'].unique()

for modelo in modelos:
    gaps = df[df['MODEL'] == modelo]['GAP'].values

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
    plt.title(f'Histograma do GAP - {modelo}')
    plt.xlabel('GAP (%)')
    plt.ylabel('Frequência')
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(f"histograma_{modelo}.jpg")
    plt.show()

plt.figure(figsize=(8, 5))
sns.boxplot(x='MODEL', y='GAP', data=df, palette='Set2', hue='MODEL', legend=False)
plt.title('Comparação de GAP entre Gurobi e Metaheurísticas')
plt.ylabel('GAP (%)')
plt.grid(True, axis='y')
plt.tight_layout()
plt.savefig("boxplot.jpg")
plt.show()

print("\nTestes de comparação entre modelos (não-paramétricos):")
amostra1 = df[df['MODEL'] == 'Gurobi']['GAP']
amostra2 = df[df['MODEL'] == 'BRKGA']['GAP']
amostra3 = df[df['MODEL'] == 'SA']['GAP']

def Teste_Mann_Whitney(a, b, nome_a, nome_b):
    stat, p = stats.mannwhitneyu(a, b, alternative='two-sided')
    print(f"\nMann-Whitney U Test ({nome_a} vs {nome_b}):")
    print(f"U = {stat:.4f}, p = {p:.4f}")
    if p < 0.05:
        print("→ Diferença significativa entre as distribuições.")
    else:
        print("→ NÃO há diferença significativa entre as distribuições.")

if len(amostra1) >= 2 and len(amostra2) >= 2:
    Teste_Mann_Whitney(amostra1, amostra2, "Gurobi", "BRKGA")

if len(amostra1) >= 2 and len(amostra3) >= 2:
    Teste_Mann_Whitney(amostra1, amostra3, "Gurobi", "SA")

if len(amostra2) >= 2 and len(amostra3) >= 2:
    Teste_Mann_Whitney(amostra2, amostra3, "BRKGA", "SA")
