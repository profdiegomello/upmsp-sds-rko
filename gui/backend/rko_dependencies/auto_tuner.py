import os
import subprocess
import glob
import time

# =====================================================================
# CONFIGURAÇÕES DO EXPERIMENTO
# =====================================================================
PASTA_AMOSTRAGEM = "/home/user2041/Documentos/upmsp-sds-rko/bench/rsdst/t/"  
PASTA_RESULTADOS = os.path.abspath(os.path.join(os.getcwd(), "resultados_experimentos", "tabelas_e_curvas"))
SCRIPT_SOLVER = "solver_core.py"
DECODERS = ["m3law", "2n"]

TEMPO_BASELINE = 60

def obter_tempo_convergencia(arquivo_txt):
    ultimo_tempo = 0.0
    melhor_mksp = float('inf')
    if not os.path.exists(arquivo_txt): return -1.0
        
    with open(arquivo_txt, 'r') as f:
        linhas = f.readlines()[1:]
        for linha in linhas:
            partes = linha.strip().split()
            if len(partes) >= 2:
                t, m = float(partes[0]), float(partes[1])
                if m < melhor_mksp:
                    melhor_mksp = m
                    ultimo_tempo = t
    return ultimo_tempo

def rodar_experimento():
    instancias = glob.glob(os.path.join(PASTA_AMOSTRAGEM, "*.txt"))
    if not instancias:
        print("Nenhuma instância encontrada na pasta!")
        return

    print(f"Iniciando calibração infinita (Baseline 60s -> Dobrando) para {len(instancias)} instâncias...\n")
    relatorio_final = {}

    for caminho_instancia in instancias:
        nome_instancia = os.path.basename(caminho_instancia)
        print(f"\n[{nome_instancia}] Analisando...")
        
        # 1. Começamos SEMPRE no Baseline de 60s
        tempo_limite_atual = TEMPO_BASELINE 
        precisa_aumentar = True
        
        while precisa_aumentar:
            tempos_decoders = []
            
            for dec in DECODERS:
                print(f"  -> Rodando {dec.upper()} por {tempo_limite_atual}s...")
                
                busca = os.path.join(PASTA_RESULTADOS, f"{nome_instancia}_run*_timeXmksp.txt")
                arquivos_antes = set(glob.glob(busca))
                
                cmd = [
                    "python3", SCRIPT_SOLVER, 
                    "--instance", caminho_instancia, 
                    "--decoder", dec, 
                    "--time_limit", str(tempo_limite_atual),
                    "--brkga.workers", "1",
                    "--sa.workers", "1",
                    "--ils.workers", "1",
                    "--vns.workers", "1",
                    "--pso.workers", "1",
                    "--ga.workers", "1",
                    "--lns.workers", "1",
                    "--irace" 
                ]
                subprocess.run(cmd, stdout=subprocess.DEVNULL)
                time.sleep(0.5) 
                
                arquivos_depois = set(glob.glob(busca))
                arquivos_novos = arquivos_depois - arquivos_antes
                
                if arquivos_novos:
                    arq_novo = list(arquivos_novos)[0]
                    tempo_conv = obter_tempo_convergencia(arq_novo)
                    tempos_decoders.append(tempo_conv)
                    print(f"     Platô atingido em: {tempo_conv:.2f}s")
                else:
                    print("     Erro: Nenhum arquivo novo de curva foi gerado.")
                    tempos_decoders.append(0.0)

            # Pega o maior tempo entre M3LAW e 2N
            tempo_maximo_instancia = max(tempos_decoders)
            
            # Verificação de Teto (Agora é 90% do tempo atual)
            if tempo_maximo_instancia > (tempo_limite_atual * 0.90):
                # O limite agora dobra ao infinito sempre que bater no teto dos 90%
                tempo_limite_atual *= 2
                print(f"  [!] Algoritmo bateu no teto de 90%. Dobrando limite para {tempo_limite_atual}s...\n")
            else:
                precisa_aumentar = False
                # Removemos os 10% de margem. O tempo recomendado é exatamente o que ele achou (mínimo 60s).
                tempo_recomendado = max(60.0, tempo_maximo_instancia)
                relatorio_final[nome_instancia] = tempo_recomendado
                print(f"  [OK] Tempo cravado para {nome_instancia}: {tempo_recomendado:.0f} segundos.")

    print("\n" + "="*50)
    print(" RELATÓRIO DE TEMPOS (FAIR PLAY - EXACT TIMING)")
    print("="*50)
    for inst, t in relatorio_final.items():
        print(f"{inst}: \t{t:.0f} segundos")
    print("="*50)

if __name__ == "__main__":
    rodar_experimento()