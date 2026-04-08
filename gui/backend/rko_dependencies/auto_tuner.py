import os
import subprocess
import glob
import time

# =====================================================================
# CONFIGURAÇÕES DO EXPERIMENTO
# =====================================================================
PASTA_AMOSTRAGEM = "benchmark_2n_m3law"
PASTA_RESULTADOS = os.path.abspath(os.path.join(os.getcwd(), "resultados_experimentos", "tabelas_e_curvas"))
SCRIPT_SOLVER = "solver_core.py"
DECODERS = ["m3law", "2n"]
ARQUIVO_RELATORIO = os.path.abspath(os.path.join(os.getcwd(), "relatorio_lote_final.txt"))

TEMPO_BASELINE = 60
# --- NOVA REGRA DO MESTRE ---
LIMIAR_PARA_DOBRAR = 0.70  # Se 70% ou mais baterem no sensor, dobramos o tempo.

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

def rodar_lote():
    instancias = glob.glob(os.path.join(PASTA_AMOSTRAGEM, "*.txt"))
    if not instancias:
        print("Nenhuma instância encontrada.")
        return
        
    total_instancias = len(instancias)
    tempo_atual = TEMPO_BASELINE
    lote_estabilizado = False

    print(f"Iniciando Calibração por Lote. Regra: Dobrar tempo se >= {LIMIAR_PARA_DOBRAR*100}% pedirem mais tempo.")

    while not lote_estabilizado:
        contador_sensor = 0

        print(f"\nTESTANDO LOTE COM time limit ={tempo_atual}s")
        
        for caminho in instancias:
            nome = os.path.basename(caminho)
            print(f"  Instância: {nome}")
            bateu_no_sensor = False

            for dec in DECODERS:
                busca = os.path.join(PASTA_RESULTADOS, f"{nome}_run*_timeXmksp.txt")
                arquivos_antes = set(glob.glob(busca))
                
                cmd = ["python3", SCRIPT_SOLVER, "--instance", caminho, "--decoder", dec, 
                       "--time_limit", str(tempo_atual), "--brkga.workers", "1", "--sa.workers", "1",
                       "--ils.workers", "1", "--vns.workers", "1", "--pso.workers", "1",
                       "--ga.workers", "1", "--lns.workers", "1", "--irace"]
                
                subprocess.run(cmd, stdout=subprocess.DEVNULL)
                time.sleep(0.2)
                
                arquivos_novos = set(glob.glob(busca)) - arquivos_antes
                if arquivos_novos:
                    t_conv = obter_tempo_convergencia(list(arquivos_novos)[0])
                    # Sensor de 90% (Continua a melhorar perto do fim)
                    if t_conv > (tempo_atual * 0.90):
                        bateu_no_sensor = True
            
            # Se QUALQUER UM dos decoders bateu no sensor, esta instância pede mais tempo
            if bateu_no_sensor:
                contador_sensor += 1
                print(f"Precisa de mais tempo (bateu nos 90%).")

        porcentagem_pedindo_tempo = contador_sensor / total_instancias
        print(f"\nRESULTADO: {contador_sensor}/{total_instancias} instâncias ({porcentagem_pedindo_tempo*100:.1f}%) pediram mais tempo.")

        # --- A AVALIAÇÃO EXATA QUE VOCÊ PEDIU ---
        if porcentagem_pedindo_tempo >= LIMIAR_PARA_DOBRAR:
            print(f"REPROVADO: A maioria (>= 70%) pediu mais tempo. Dobrando de {tempo_atual}s para {tempo_atual * 2}s...\n")
            tempo_atual *= 2
        else:
            print(f"APROVADO: Menos de 70% pediram mais tempo. Lote finalizado.")
            lote_estabilizado = True
            
            with open(ARQUIVO_RELATORIO, "w") as f:
                f.write(f"TEMPO FINAL DEFINIDO PARA O LOTE: {tempo_atual} segundos\n")
                f.write(f"Instancias testadas: {total_instancias}\n")
                f.write(f"Instancias que ainda pediam mais tempo: {contador_sensor} ({porcentagem_pedindo_tempo*100:.1f}%)\n")
                f.write(f"Instancias estabilizadas: {total_instancias - contador_sensor} ({(1 - porcentagem_pedindo_tempo)*100:.1f}%)\n")

if __name__ == "__main__":
    rodar_lote()