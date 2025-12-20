# Script para baixar arquivos de um dataset do Kaggle usando a API do Kaggle.
#     ## Requisitos:
#         Faça login no Kaggle e obtenha o arquivo kaggle.json com suas credenciais.
#     ## Instruções:  
#         Acesse https://www.kaggle.com/settings vá em API, clique em "Create New Token" e baixe o arquivo kaggle.json.
#         Certifique-se de que o arquivo kaggle.json está no diretório ~/.kaggle/ (Linux/Mac) ou C:\Users\<username>\.kaggle\ (Windows).  

import kaggle
import os
import zipfile

def download_files(arquivos_desejados=['large/I_50_10_S_1-9_1.txt' , 'small/I_10_2_S_1-49_6.txt'], extract_folder = 'bench/rsdst/'):
    """
        Baixa e extrai arquivos específicos de um dataset do Kaggle.
        Parâmetros:
            - arquivos_desejados: Lista de caminhos dos arquivos desejados dentro do dataset (ex: ['small/I_10_2_S_1-49_6.txt', 'large/I_50_10_S_1-9_1.txt']).
            - extract_folder: Caminho local onde os arquivos serão extraídos (ex: 'bench/rsdst/').
        Observação:
            - O diretório de extração será criado se não existir.
            - Os arquivos serão extraídos apenas se não existirem no diretório de extração. 
    """


    zip_filename = "bench/rsdstruiz-upmsp-sds.zip"

    # Baixar apenas se o zip ainda não existir
    if not os.path.exists(zip_filename):
        #print("Arquivo ZIP não encontrado. Baixando...")
        kaggle.api.dataset_download_files("everthonvalado/rsdstruiz-upmsp-sds", path="bench/", unzip=False)

    # Cria o diretório de extração, se necessário
    os.makedirs(extract_folder, exist_ok=True)

    # Prefixo da estrutura dentro do zip
    prefixo_zip = "RSDST/bench/rsdst/"

    # Extrai apenas os arquivos que ainda não existem no destino
    with zipfile.ZipFile(zip_filename, 'r') as zip_ref:
        for caminho_arquivo in arquivos_desejados:
            caminho_arquivo = caminho_arquivo.removeprefix("bench/rsdst/") #HACK caso o usuário passe o caminho completo desnecessariamente
            caminho_arquivo = caminho_arquivo.removeprefix("/app/bench/rsdst/") #FIXED o irace incluía o nome da pasta raiz do Docker
            caminho_zip = prefixo_zip + caminho_arquivo
            destino = os.path.join(extract_folder, caminho_arquivo)

            if os.path.exists(destino):
                #print(f"Arquivo já existe: {destino} — pulando.")
                continue

            if caminho_zip in zip_ref.namelist():
                #print(f"Extraindo: {caminho_zip} → {destino}")
                with zip_ref.open(caminho_zip) as origem, open(destino, "wb") as destino_arquivo:
                    destino_arquivo.write(origem.read())
            # else:
            #     print(f"Arquivo não encontrado no zip: {caminho_zip}")

def download_file(arquivo_desejado='large/I_50_10_S_1-9_1.txt', extract_folder = 'bench/rsdst/'):
    """
        Baixa e extrai arquivo específico de um dataset do Kaggle.
        Parâmetros:
            - arquivo_desejado: Caminho do arquivo desejado dentro do dataset (ex: 'large/I_50_10_S_1-9_1.txt' ).
            - extract_folder: Caminho local onde os arquivos serão extraídos (ex: 'bench/rsdst/').
        Observação:
            - O diretório de extração será criado se não existir.
            - O arquivo será extraído apenas se não existir no diretório de extração. 
    """
    download_files([arquivo_desejado], extract_folder) 


# download_files( 
#     arquivos_desejados = [
#           'small/I_6_2_S_1-9_1.txt'
#         , 'small/I_6_2_S_1-9_2.txt'
#         , 'small/I_6_2_S_1-9_3.txt'
#         , 'small/I_6_2_S_1-9_4.txt'
#         , 'small/I_6_2_S_1-9_5.txt'
#     ]
# )



# def download_via_kaggle_API(dataset_id='everthonvalado/rsdstruiz-upmsp-sds', file_path_in_dataset='bench/rsdst/small/I_10_2_S_1-124_1.txt', output_path='./bench'):
#     """
#         Baixa um arquivo específico de um dataset do Kaggle.
#         Parâmetros:
#             - dataset_id: ID do dataset no Kaggle (ex: 'everthonvalado/rsdstruiz-upmsp-sds').
#             - file_path_in_dataset: Caminho do arquivo dentro do dataset (ex: 'bench/rsdst/small/I_10_2_S_1-124_1.txt').
#             - output_path: Caminho local onde o arquivo será salvo (ex: './bench/rsdst/small' ou '/tmp' ou onde quiser salvar o arquivo).
#     """

#     try:
#         # Autentica com a API do Kaggle (requer o arquivo kaggle.json)
#         try:
#             kaggle.api.authenticate()
#             print("Autenticação com a API do Kaggle realizada com sucesso.")
#         except Exception as e:
#             print(f"Erro na autenticação: {e}")
#             print("Certifique-se de que seu arquivo 'kaggle.json' está no local correto (ex: ~/.kaggle/kaggle.json)")
#             exit()

#         print(f"Dataset: {dataset_id}\n")
#         print(f"Iniciando o download do arquivo: {file_path_in_dataset}")

#         kaggle.api.dataset_download_file(
#             dataset=dataset_id,
#             file_name=file_path_in_dataset,
#             path=output_path,
#             quiet=False # Define como False para ver o progresso do download
#         )

#         # O nome do arquivo baixado será o nome original
#         downloaded_file_name = os.path.basename(file_path_in_dataset)

#         print(f"\nDownload concluído com sucesso!")
#         print(f"O arquivo '{downloaded_file_name}' foi salvo em: {os.path.abspath(output_path)}")

#     except Exception as e:
#         print(f"\nOcorreu um erro durante o download: {e}")
#         print("Verifique se o nome do dataset e o caminho do arquivo estão corretos.")

# # if not os.path.exists('bench/FILENAMES.txt'):
# #         download_file_from_kaggle(dataset_id='everthonvalado/rsdstruiz-upmsp-sds', file_path_in_dataset='FILENAMES.txt', output_path='bench/') 
# #         # download_file_from_kaggle(dataset_id='everthonvalado/rsdstruiz-upmsp-sds', file_path_in_dataset='RSDST/bench/rsdst/small/I_10_2_S_1-124_1.txt', output_path='/tmp/') 
