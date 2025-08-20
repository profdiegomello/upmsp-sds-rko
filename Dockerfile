# 1) Baixa a imagem base do Python
FROM python:3.13-slim

# 2) Instala git
RUN apt-get update && apt-get install -y git

# 3) Cria diretório de trabalho
WORKDIR /app

# 4) Instala as dependências (quando congelar o projeto, gere o requirements.txt)
RUN pip install --no-cache-dir numpy matplotlib pulp gurobipy argparse kaggle

# 5) Copia o repositório local (DICA: tudo que for mutável coloque mais abaixo no Dockerfile)
COPY ./ /app/

## Quando o projeto estiver pronto, substituiremos os comandos (4) e (5) acima pelos abaixo: 
# # 4) Clona o repositório remoto
# ARG GIT_TOKEN
# ARG GIT_USER
# RUN git clone https://${GIT_USER}:${GIT_TOKEN}@github.com/profdiegomello/upmsp-sds-rko.git /app
# # 5) Instala as dependências listadas no requirements.txt
# # DICA: dentro de um venv, exporte as dependências via: pip freeze > requirements.txt
# RUN cd /app && pip install --no-cache-dir -r requirements.txt

# 6) Comando padrão para rodar o código se nenhum outro executável for indicado
# CMD ["python", "solver.py"]
CMD ["bash"]


########################################
## 1) crie um token (classic) pra API do https://github.com/settings/tokens ()
# firefox https://github.com/settings/tokens

## 2) construa a imagem do container
# docker build --tag upmsp-sds-rko --build-arg GIT_TOKEN=SUBSTITUIR_POR_SEU_TOKEN_DO_GIT --build-arg GIT_USER=SUBSTITUIR_POR_SEU_USER_NO_GIT -f Dockerfile ./

## 3) crie o novo container a partir da imagem e execute (ATENCAO: só escreva na pasta output, senão perderá os resultados)
# docker run -dit --name rko --volume ./output:/app/output upmsp-sds-rko bash

## 4) com o container já rodando, pode-se executar programas dentro do container
# docker start rko
# docker exec -it rko bash
