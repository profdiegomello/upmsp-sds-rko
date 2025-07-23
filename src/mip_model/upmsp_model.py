from pulp import LpMinimize, LpProblem, LpVariable, lpSum, value, PULP_CBC_CMD, GUROBI
import gurobipy
from itertools import product

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

    return {
        "objetivo": value(model.objective), "runtime": model.solutionTime,
        "lowerbound": model.solverModel.ObjBound, "gap": model.solverModel.MIPGap,
        "status_code": model.solverModel.Status, "solucao": solucao_gurobi,
        "constraints": len(model.constraints), "variables": len(model.variables()),
        "binarias": len(bin_vars), "inteiras": len(int_vars), "continuas": len(cont_vars)
    }

