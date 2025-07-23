from pulp import LpMinimize, LpProblem, LpVariable, lpSum, value, PULP_CBC_CMD, GUROBI
import gurobipy
from itertools import product

#
# Gera docionarios X e C a partir da solucao do modelo
#
def extrair_solucao_mip(solucao_variaveis, M, N, N0):
    """
    Converte as variáveis de solução do PuLP em dicionários Python genéricos.
    """
    X_vars = solucao_variaveis["X"]
    C_vars = solucao_variaveis["C"]
    
    X_dict = {}
    C_dict = {}

    # Extrai os valores de X
    for i in M:
        for j in N0:
            for k in N:
                if j != k:
                    var = X_vars.get((i, j, k))
                    if var and var.varValue > 0.5: # Verifica se a variável existe e foi selecionada
                        X_dict[(i, j, k)] = 1
    
    # Extrai os valores de C
    for i in M:
        for j in N:
            var = C_vars.get((i, j))
            if var: # Apenas para jobs reais, não o dummy
                C_dict[(i, j)] = var.varValue

    return X_dict, C_dict
    
    
#
# Gera modelo MIP a partir do artigo de Vallada e Ruiz (2011):
# 'A genetic algorithm for the unrelated parallel machine scheduling problem
# with sequence dependent setup times'
#
def modelSolving(M, N, N0, p, S, log, time_limit=None):

    # Constante grande:
    V = 1000

    model = LpProblem(name="UPMSPST", sense=LpMinimize)

    # Variáveis de decisão:
    X = LpVariable.dicts("X", product(M, N0, N), cat='Binary')
    C = LpVariable.dicts("C", product(M, N0), lowBound=0, cat='Continuous')
    Cmax = LpVariable("Cmax", lowBound=0, cat='Continuous')

    # Função objetivo (1):
    model += Cmax

    # Restrições (2):
    for k in N:
        model += lpSum(X[i, j, k] for i in M for j in N0 if j != k) == 1

    # Restrições (3):
    for j in N:
        model += lpSum(X[i, j, k] for i in M for k in N if j != k) <= 1

    # Restrições (4):
    for i in M:
        model += lpSum(X[i, 0, k] for k in N) <= 1

    # Restrições (5):
    for j in N:
        for k in N:
            if j != k:
                for i in M:
                    model += lpSum(X[i, h, j] for h in N0 if h != k and h != j) >= X[i, j, k]

    # Restrições (6):
    for j in N0:
        for k in N:
            if j != k:
                for i in M:
                    model += C[i, k] + V * (1 - X[i, j, k]) >= C[i, j] + S.get((i, j, k), 0) + p.get((i, k), 0)

    # Restrições (7):
    for i in M:
        model += C[i, 0] == 0

    # Restrições (8):
    for i in M:
        for j in N:
            model += C[i, j] >= 0

    # Restrições (9):
    for j in N:
        for i in M:
            model += Cmax >= C[i, j]

    # Resolver o modelo
    if time_limit is not None:
        modelo = model.solve(GUROBI(msg=True, logPath=str(log).replace(".txt", ""), timeLimit=time_limit))
    else:
        modelo = model.solve(GUROBI(msg=True, logPath=str(log).replace(".txt", "")))

    # Extrair valores das variáveis, separando por tipo:
    bin_vars = {}
    int_vars = {}
    cont_vars = {}

    for var in model.variables():
        # 'var' é um objeto LpVariable
        if var.cat == 'Binary':
            bin_vars[var.name] = var.varValue
        elif var.cat == 'Integer':
            int_vars[var.name] = var.varValue
        elif var.cat == 'Continuous':
            cont_vars[var.name] = var.varValue

    solucao_gurobi = {"X": X, "C": C}

    # Também extrair o valor do Cmax (que é contínuo, mas já está no dicionário cont_vars)
    Cmax_val = Cmax.varValue
    
    # Extrair dicionários a partir das variaveis de decisao
    X_dict, C_dict = extrair_solucao_mip(solucao_gurobi, M, N, N0)

    return {
        "objetivo": value(model.objective), "runtime": model.solutionTime,
        "lowerbound": model.solverModel.ObjBound, "gap": model.solverModel.MIPGap,
        "status_code": model.solverModel.Status, "solucao": solucao_gurobi,
        "constraints": len(model.constraints), "variables": len(model.variables()),
        "binarias": len(bin_vars), "inteiras": len(int_vars), "continuas": len(cont_vars),
        "X_dict": X_dict,
        "C_dict": C_dict
    }

