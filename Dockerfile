# 1) Baixa a imagem base do Python
FROM python:3.13-slim

# 2) Instala git
RUN apt-get update && apt-get install -y git

# 3) Cria diretório de trabalho
WORKDIR /app

# 4.1) Instala as dependências (quando congelar o projeto, gere o requirements.txt)
RUN pip install --no-cache-dir numpy matplotlib pulp gurobipy argparse kaggle
# 4.2) Copia arquivo de dependências Python e as instala (caso haja alguma a mais no requirements.txt)
COPY requirements.txt /app/
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

# 5) Copia o repositório local (DICA: tudo que for mutável coloque abaixo dos comandos de install, isso evita [re]build demorado)
COPY ./ /app/

## Quando o projeto estiver pronto, substituiremos os comandos (4) e (5) acima pelos abaixo: 
# # 4) Clona o repositório remoto
# ARG GIT_TOKEN
# ARG GIT_USER
# RUN git clone https://${GIT_USER}:${GIT_TOKEN}@github.com/profdiegomello/upmsp-sds-rko.git /app
# # 5) Instala as dependências listadas no requirements.txt
# # DICA: dentro de um venv, exporte as dependências via: pip freeze > requirements.txt
# RUN cd /app && pip install --no-cache-dir -r requirements.txt

# 6) Configura o token da API do Kaggle
RUN mkdir -p /root/.config/kaggle && echo '{"username":"everthonvalado","key":"2eb29fb3d6d624834ac906b93bd70650"}' > /root/.config/kaggle/kaggle.json && chmod 600 /root/.config/kaggle/kaggle.json

# 7) Configura a variavel de ambiente apontando pra licenca do gurobi
COPY ./gurobi.lic /app/gurobi.lic
RUN export GRB_LICENCE_FILE="/app/gurobi.lic"

# 7) Comando padrão para rodar o código se nenhum outro executável for indicado
# CMD ["python", "solver.py"]
CMD ["bash"]


########################################
## 1) crie um token (classic) pra API do https://github.com/settings/tokens ()
# firefox https://github.com/settings/tokens

## 2) construa a imagem do container
# docker build --tag upmsp -f Dockerfile ./
#        OBS.: se não for copiar da pasta local mas quiser baixar do github, inclua no comando acima: 
#              --build-arg GIT_TOKEN=SEU_TOKEN_DO_GIT --build-arg GIT_USER=SEU_USER_NO_GIT

## 3) crie o novo container a partir da imagem e execute-o
# docker run -dit --name exp --volume ./:/app/ upmsp 

## 4) com o container já rodando, pode-se executar programas dentro do container
# docker start exp
# docker exec -it exp bash
