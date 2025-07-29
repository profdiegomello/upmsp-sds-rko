# Script para baixar arquivos de um dataset do Kaggle usando a API do Kaggle.
#     ## Requisitos:
#         Faça login no Kaggle e obtenha o arquivo kaggle.json com suas credenciais.
#     ## Instruções:  
#         Acesse https://www.kaggle.com/settings vá em API, clique em "Create New Token" e baixe o arquivo kaggle.json.
#         Certifique-se de que o arquivo kaggle.json está no diretório ~/.kaggle/ (Linux/Mac) ou C:\Users\<username>\.kaggle\ (Windows).  


import kaggle
import os

def download_file_from_kaggle(dataset_id='everthonvalado/rsdstruiz-upmsp-sds', file_path_in_dataset='bench/rsdst/small/I_10_2_S_1-124_1.txt', output_path='./bench'):
    """
        Baixa um arquivo específico de um dataset do Kaggle.
        Parâmetros:
            - dataset_id: ID do dataset no Kaggle (ex: 'everthonvalado/rsdstruiz-upmsp-sds').
            - file_path_in_dataset: Caminho do arquivo dentro do dataset (ex: 'bench/rsdst/small/I_10_2_S_1-124_1.txt').
            - output_path: Caminho local onde o arquivo será salvo (ex: './bench/rsdst/small' ou '/tmp' ou onde quiser salvar o arquivo).
    """

    try:
        # Autentica com a API do Kaggle (requer o arquivo kaggle.json)
        try:
            kaggle.api.authenticate()
            print("Autenticação com a API do Kaggle realizada com sucesso.")
        except Exception as e:
            print(f"Erro na autenticação: {e}")
            print("Certifique-se de que seu arquivo 'kaggle.json' está no local correto (ex: ~/.kaggle/kaggle.json)")
            exit()

        print(f"Dataset: {dataset_id}\n")
        print(f"Iniciando o download do arquivo: {file_path_in_dataset}")

        kaggle.api.dataset_download_file(
            dataset=dataset_id,
            file_name=file_path_in_dataset,
            path=output_path,
            quiet=False # Define como False para ver o progresso do download
        )

        # O nome do arquivo baixado será o nome original
        downloaded_file_name = os.path.basename(file_path_in_dataset)

        print(f"\nDownload concluído com sucesso!")
        print(f"O arquivo '{downloaded_file_name}' foi salvo em: {os.path.abspath(output_path)}")

    except Exception as e:
        print(f"\nOcorreu um erro durante o download: {e}")
        print("Verifique se o nome do dataset e o caminho do arquivo estão corretos.")

def list_files_in_kaggle_dataset(dataset_id='everthonvalado/rsdstruiz-upmsp-sds', target_folder='bench/rsdst/large/'):
    """
    Lista os arquivos de um dataset do Kaggle que estão dentro de uma pasta específica.
        Parâmetros:
            - dataset_id: ID do dataset no Kaggle (ex: 'everthonvalado/rsdstruiz-upmsp-sds').
            - target_folder: Caminho da pasta dentro do dataset (ex: 'bench/rsdst/large/').
        Retorna:    
            - Uma lista de arquivos encontrados na pasta especificada.
    """

    try:
        # 1. Autenticação com a API do Kaggle
        # Autentica com a API do Kaggle (requer o arquivo kaggle.json)
        try:
            kaggle.api.authenticate()
            print("Autenticação com a API do Kaggle realizada com sucesso.")
        except Exception as e:
            print(f"Erro na autenticação: {e}")
            print("Certifique-se de que seu arquivo 'kaggle.json' está no local correto (ex: ~/.kaggle/kaggle.json)")
            exit()

        # 2. Obter a lista de TODOS os arquivos do dataset
        all_files = kaggle.api.dataset_list_files(dataset_id).files

        # 3. Filtrar a lista para manter apenas os arquivos da pasta alvo
        filtered_files = [
            file.name for file in all_files 
            if str(file.name).startswith(target_folder)
        ]

        # 4. Exibir os resultados
        if filtered_files:
            print(f"Arquivos encontrados na pasta '{target_folder}':")
            for file_path in filtered_files:
                print(f"{file_path}")

            return filtered_files
        else:
            print(f"Nenhum arquivo encontrado na pasta '{target_folder}'. Verifique se o caminho está correto.")
            return []

    except Exception as e:
        print(f"Ocorreu um erro: {e}")


from collections import defaultdict
def build_tree(paths):
    """Constrói uma estrutura de árvore aninhada a partir de uma lista de caminhos."""
    tree = lambda: defaultdict(tree)
    root = tree()
    for path in paths:
        parts = path.split('/')
        node = root
        for part in parts:
            node = node[part]
    return root

def print_tree(node, indent="", last=True):
    """Imprime a árvore de diretórios de forma recursiva."""
    prefix = indent + ("└── " if last else "├── ")
    children = list(node.keys())
    for i, child in enumerate(children):
        is_last_child = (i == len(children) - 1)
        print(f"{prefix}{child}")
        print_tree(node[child], indent + ("    " if last else "│   "), is_last_child)


def list_directory_structure_of_kaggle_dataset(dataset_id = 'everthonvalado/rsdstruiz-upmsp-sds'):
    """
        Lista a estrutura de diretórios de um dataset do Kaggle.
        Parâmetros:
            - dataset_id: ID do dataset no Kaggle (ex: 'everthonvalado/rsdstruiz-upmsp-sds').
    """

    try:
        # 1. Autenticação com a API
        # Autentica com a API do Kaggle (requer o arquivo kaggle.json)
        try:
            kaggle.api.authenticate()
            print("Autenticação com a API do Kaggle realizada com sucesso.")
        except Exception as e:
            print(f"Erro na autenticação: {e}")
            print("Certifique-se de que seu arquivo 'kaggle.json' está no local correto (ex: ~/.kaggle/kaggle.json)")
            exit()

        # 2. Definição do dataset
        print(f"Analisando a estrutura do dataset: {dataset_id}\n")

        # 3. Obtenção da lista de arquivos
        file_references = kaggle.api.dataset_list_files(dataset_id).files
        paths = [str(f.name) for f in file_references] # Converte para lista de strings

        # 4. Construção e impressão da árvore
        if paths:
            directory_tree = build_tree(paths)
            # Imprime a partir do primeiro nível
            for i, key in enumerate(directory_tree.keys()):
                is_last = (i == len(directory_tree.keys()) - 1)
                print(f"{key}") # Imprime o diretório base
                print_tree(directory_tree[key], "", is_last)
        else:
            print("Nenhum arquivo encontrado no dataset.")

    except Exception as e:
        print(f"Ocorreu um erro: {e}")


# list_directory_structure_of_kaggle_dataset()

# list_files_in_kaggle_dataset(target_folder='bench/rsdst/large/')

## OBS.: mudei o repositório do dataset de private para public, então pode demorar algumas horas até que o Kaggle termine de indexar os arquivos e gerar as URLs corretas.
# download_file_from_kaggle(file_path_in_dataset='bench/rsdst/large/I_100_10_S_1-124_4.txt', output_path='/tmp/') 
download_file_from_kaggle(dataset_id='himanshunakrani/iris-dataset', file_path_in_dataset='iris.csv', output_path='/tmp/')