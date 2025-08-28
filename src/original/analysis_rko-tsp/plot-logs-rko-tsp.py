import pandas as pd
import matplotlib.pyplot as plt
import re
import os 

# Lista de arquivos e nomes de séries
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import argparse

# define argumentos
parser = argparse.ArgumentParser(description="Filtra arquivos .log pelo prefixo")
parser.add_argument("pasta", help="Caminho da pasta onde estão os arquivos", default="./eil51")
parser.add_argument("instancia", help="Prefixo dos arquivos, ex: eil51", default="eil51")
args = parser.parse_args()

# lista arquivos que começam com prefixo e terminam com .log
arquivos = [f for f in os.listdir(args.pasta) if f.startswith(f"{args.instancia}_") and f.endswith(".log")]

# separa em dois grupos
com_virgula = [f for f in arquivos if "," in f]
sem_virgula = [f for f in arquivos if "," not in f]

print("Arquivos com vírgula:", com_virgula)
print("Arquivos sem vírgula:", sem_virgula)

# # arquivos_single = ["eil51_brkga.log", "eil51_ga.log", "eil51_grasp.log", "eil51_ils.log", "eil51_lns.log", "eil51_pso.log", "eil51_sa.log", "eil51_vns.log"]
# arquivos_single = ["eil51_brkga.log", "eil51_ga.log", "eil51_ils.log", "eil51_lns.log", "eil51_sa.log", "eil51_vns.log"]

# arquivos_mix = ["eil51_brkga,ga,grasp,ils,lns,vns.log", "eil51_ga,ils,lns,vns.log", "eil51_grasp,pso,brkga,sa.log", "eil51_ils,lns,vns.log"]
# # arquivos_mix = ["eil51_brkga,ga,grasp,ils,lns,vns.log", "eil51_ga,ils,lns,vns.log", "eil51_ils,lns,vns.log"]
# # arquivos_mix = ["eil51_grasp,pso,brkga,sa.log"]

arquivos = []
arquivos = sem_virgula + com_virgula

dados_todos = []

for arquivo in arquivos:
    serie_nome = arquivo.split(".")[0] # remove extensão
    serie_nome = serie_nome.split("_")[1]  # remove prefixo da instância
    serie_nome = "rko_" + serie_nome if "," in serie_nome else serie_nome

    with open(f"{args.pasta}/{arquivo}", "r") as f:
        for linha in f:
            if "pool best" in linha:
                # Extrair tempo e valor usando regex
                m = re.search(r"\[\s*([\d.]+)s\]\s*pool best\s*=\s*([\d.]+)", linha)
                if m:
                    tempo = float(m.group(1))
                    valor = float(m.group(2))
                    dados_todos.append({"X": tempo, "Y": valor, "Z": serie_nome})

# Transformar em DataFrame
df = pd.DataFrame(dados_todos)

# Plotar

# # largura x altura em pixels desejados
# width_px = 1280
# height_px = 720
# dpi = 200  
# # converte para figsize em polegadas
# figsize = (width_px / dpi, height_px / dpi)
# plt.figure(figsize=figsize, dpi=dpi)

# plt.figure(figsize=(8,5))
plt.figure(figsize=(9,5), dpi=150)

for serie, grupo in df.groupby("Z"):
    plt.plot(grupo["X"], grupo["Y"], label=serie, marker="o")

plt.xlabel("Time (s)")
plt.ylabel("Cost")
plt.title(f"Evolution of RKO (elite pool best solution) instance: {args.instancia}")

plt.legend(title="Series")
# legenda menor e fora do gráfico
plt.legend(fontsize=6, loc='upper right')  # ajusta tamanho da fonte
# loc='upper right', 'lower left', 'best' etc
# você também pode usar bbox_to_anchor para posicionar fora do gráfico:
# plt.legend(fontsize=10, loc='upper left', bbox_to_anchor=(1,1))


plt.grid(True)

plt.xlim(0, 60)  # limita o eixo X de 0 a 60 segundos

plt.savefig(f"rko-evolution_{args.instancia}.png", dpi=300)
plt.show()
