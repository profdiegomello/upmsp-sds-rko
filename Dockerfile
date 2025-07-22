FROM python:3.13-slim

# Instala git
RUN apt-get update && apt-get install -y git

# Cria diretório de trabalho
WORKDIR /app

ARG GIT_TOKEN
ARG GIT_USER

# Clona o repositório
RUN git clone https://${GIT_USER}:${GIT_TOKEN}@github.com/profdiegomello/upmsp-sds-rko.git /app

# Instala as dependências listadas no requirements.txt
# DICA: dentro de um venv, exporte as dependências via: pip freeze > requirements.txt
RUN cd /app && pip install --no-cache-dir -r requirements.txt


# Comando padrão para rodar o código se nenhum outro executável for indicado
# CMD ["python", "solver.py"]
CMD ["bash"]


########################################
## 1) crie um token (classic) pra API do https://github.com/settings/tokens ()
# firefox https://github.com/settings/tokens

## 2) construa a imagem do container
# docker build --tag upmsp-sds-rko --build-arg GIT_TOKEN=SUBSTITUIR_POR_SEU_TOKEN_DO_GIT --build-arg GIT_USER=SUBSTITUIR_POR_SEU_USER_NO_GIT .

## 3) crie o novo container a partir da imagem
# docker run -it --volume $(pwd)/output:/app/output upmsp-sds-rko bash

## 4) com o container já rodando, pode-se executar programas dentro do container
# docker exec -it upmsp-sds-rko python3 solver.py
