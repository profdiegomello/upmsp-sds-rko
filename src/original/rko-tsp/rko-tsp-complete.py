#!/usr/bin/env python3
"""
RKO-lite (mais fiel): TSP with BRKGA + SA + ILS + GRASP + GA + PSO + VNS + LNS sharing an elite pool, plus:
 - Shaking with 4 moves (Alg.1-style)
 - Blending with rho/mu (Alg.2-style)
 - RVND local search
 - Farey-like intensification for pool initialization
 - Threads with Pool lock
Only stdlib. Accepts optional TSPLIB path as argv[1]; otherwise generates synthetic 208-node instance.
"""

import sys, math, random, threading, time
import matplotlib.pyplot as plt
import argparse

# ---------------------------
# PARAMETERS (tuneable)
# ---------------------------
SEED = 42
#random.seed(SEED)

# Default RKO Global parameters
RKO_DEFAULTS = {
    'pool_max': 12,
    'timelimit': 60.0,
    'beta': 0.05,
    'rho': 0.7,
    'mu': 0.02,
}

# Default BRKGA parameters
BRKGA_DEFAULTS = {
    'pop_size': 80,
    'elite_frac': 0.2,
    'mutant_frac': 0.1,
}

# Default SA parameters
SA_DEFAULTS = {
    'betamin': 0.01,
    'betamax': 0.1,
    'samax': 20000,
    'alphasa': 0.9995,
    't0': 100.0,
}

# Default ILS parameters
ILS_DEFAULTS = {
    'k': 2,
    'max_no_improve': 500,
    'beta_shake': 0.05,
}

# Default GRASP parameters
GRASP_DEFAULTS = {
    'max_no_improve': 50,
    'alpha': 0.2,
}

# Default GA parameters
GA_DEFAULTS = {
    'pop_size': 100,
    'pc': 0.8,
    'pm': 0.05,
}

# Default PSO parameters
PSO_DEFAULTS = {
    'pop_size': 100,
    'w': 0.729,
    'c1': 1.49445,
    'c2': 1.49445,
}

# Default VNS parameters
VNS_DEFAULTS = {
    'k_max': 4,
    'max_no_improve': 200,
}

# Default LNS parameters
LNS_DEFAULTS = {
    'factor': 0.1,
    'max_no_improve': 100,
}

# Common parameters
RVND_MAX_NO_IMPROVE = 200
INITIAL_POOL_REFINES = 8
DIST = None
COORDS = []
INSTANCE_NAME = "Synthetic"

# ---------------------------
# TSPLIB utilities
# ---------------------------
def read_tsplib_coords(path):
    coords = []
    started = False
    is_euc_2d = False
    name = "unknown"
    with open(path, 'r') as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            if s.upper().startswith("NAME"):
                name = s.split(':')[1].strip()
            if s.upper().startswith("EDGE_WEIGHT_TYPE"):
                if "EUC_2D" in s.upper():
                    is_euc_2d = True
            if s.upper().startswith("NODE_COORD_SECTION"):
                started = True
                continue
            if not started:
                continue
            if s.upper().startswith("EOF"):
                break
            parts = s.split()
            if len(parts) >= 3:
                try:
                    x = float(parts[1]); y = float(parts[2])
                    coords.append((x,y))
                except:
                    continue
    if not is_euc_2d:
        raise ValueError(f"Instance type is not EUC_2D.")
    if not coords:
        raise ValueError("No coords found")
    return coords, name

def generate_random_coords(n, seed=SEED):
    random.seed(seed)
    return [(random.random() * 10000.0, random.random() * 10000.0) for _ in range(n)]

def euclid_dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])

def build_distance_matrix(coords):
    n = len(coords)
    D = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            d = euclid_dist(coords[i], coords[j])
            D[i][j] = D[j][i] = d
    return D

# ---------------------------
# Solution and Pool
# ---------------------------
class Solution:
    def __init__(self, N, keys=None):
        self.N = N
        if keys is None:
            self.keys = [random.random() for _ in range(self.N)]
        else:
            self.keys = list(keys)
        self.tour = []
        self.cost = float('inf')
        self.decode()

    def decode(self):
        order = list(range(self.N))
        order.sort(key=lambda c: self.keys[c])
        self.tour = order
        self.cost = 0.0
        for i in range(self.N):
            a = self.tour[i]
            b = self.tour[(i + 1) % self.N]
            self.cost += DIST[a][b]

    def clone(self):
        s = Solution(self.N, self.keys)
        s.tour = list(self.tour)
        s.cost = self.cost
        return s

    def sync_keys_from_tour(self):
        base = [0.0] * self.N
        for pos, city in enumerate(self.tour):
            base[city] = (pos / float(self.N)) + (random.random() * 1e-8)
        self.keys = base

class Pool:
    def __init__(self, max_size):
        self.max_size = max_size
        self.elites = []
        self.lock = threading.Lock()

    def add(self, sol):
        with self.lock:
            sig = tuple(sol.tour)
            for s in self.elites:
                if tuple(s.tour) == sig:
                    return False
            self.elites.append(sol.clone())
            self.elites.sort(key=lambda s: s.cost)
            if len(self.elites) > self.max_size:
                self.elites.pop()
            return True

    def best(self):
        with self.lock:
            if not self.elites:
                return None
            return self.elites[0].clone()

    def snapshot(self):
        with self.lock:
            return [s.clone() for s in self.elites]

# ---------------------------
# Shaking moves (Alg.1)
# ---------------------------
def recompute_cost_from_tour(tour):
    c = 0.0
    for k in range(len(tour)):
        a = tour[k]
        b = tour[(k + 1) % len(tour)]
        c += DIST[a][b]
    return c

def shake_random_shuffle_segment(sol):
    s = sol.clone()
    i, j = sorted(random.sample(range(s.N), 2))
    seg = s.tour[i:j + 1]
    random.shuffle(seg)
    s.tour[i:j + 1] = seg
    s.cost = recompute_cost_from_tour(s.tour)
    s.sync_keys_from_tour()
    return s

def shake_mirror_segment(sol):
    s = sol.clone()
    i, j = sorted(random.sample(range(s.N), 2))
    s.tour[i:j + 1] = list(reversed(s.tour[i:j + 1]))
    s.cost = recompute_cost_from_tour(s.tour)
    s.sync_keys_from_tour()
    return s

def shake_swap_any(sol):
    s = sol.clone()
    i, j = random.sample(range(s.N), 2)
    s.tour[i], s.tour[j] = s.tour[j], s.tour[i]
    s.cost = recompute_cost_from_tour(s.tour)
    s.sync_keys_from_tour()
    return s

def shake_swap_neighbor(sol):
    s = sol.clone()
    i = random.randrange(0, s.N)
    j = (i + 1) % s.N
    s.tour[i], s.tour[j] = s.tour[j], s.tour[i]
    s.cost = recompute_cost_from_tour(s.tour)
    s.sync_keys_from_tour()
    return s

SHAKING_MOVES = [shake_random_shuffle_segment, shake_mirror_segment, shake_swap_any, shake_swap_neighbor]

def shaking_composed(sol, beta):
    """
    Apply beta*N shaking operations chosen uniformly among the 4 moves.
    Returns shaken solution.
    """
    s = sol.clone()
    times = max(1, int(beta * s.N))
    for _ in range(times):
        move = random.choice(SHAKING_MOVES)
        s = move(s)
    return s

# ---------------------------
# Blending (Alg.2-type)
# ---------------------------
def blending(parent1, parent2, rho, mu):
    N = parent1.N
    child_keys = [0.0] * N
    for c in range(N):
        if random.random() < rho:
            child_keys[c] = parent1.keys[c]
        else:
            child_keys[c] = parent2.keys[c]
        # mutation
        if random.random() < mu:
            child_keys[c] = random.random()
    child = Solution(N, keys=child_keys)
    return child

# ---------------------------
# Neighborhoods for RVND
# ---------------------------
def neigh_swap(tour):
    i, j = random.sample(range(len(tour)), 2)
    new = list(tour)
    new[i], new[j] = new[j], new[i]
    return new

def neigh_2opt(tour):
    i, j = sorted(random.sample(range(len(tour)), 2))
    new = list(tour)
    new[i:j + 1] = list(reversed(new[i:j + 1]))
    return new

def neigh_reinsertion(tour):
    n = len(tour)
    i, j = sorted(random.sample(range(n), 2))
    new = list(tour)
    segment = new[i:j + 1]
    del new[i:j + 1]
    pos = random.randrange(0, len(new) + 1)
    new[pos:pos] = segment
    return new

RVND_NEIGHS = [neigh_swap, neigh_2opt, neigh_reinsertion]

def rvnd(sol, max_no_improve=RVND_MAX_NO_IMPROVE):
    best = sol.clone()
    no_imp = 0
    neighs = list(RVND_NEIGHS)
    while no_imp < max_no_improve:
        random.shuffle(neighs)
        improved = False
        for neigh in neighs:
            cand_tour = neigh(best.tour)
            cand_cost = recompute_cost_from_tour(cand_tour)
            if cand_cost + 1e-12 < best.cost:
                best.tour = cand_tour
                best.cost = cand_cost
                best.sync_keys_from_tour()
                improved = True
                break
        if improved:
            no_imp = 0
        else:
            no_imp += 1
    return best

# ---------------------------
# Farey-like intensification for initial pool
# ---------------------------
def farey_like_intensify(sol, attempts=100):
    best = rvnd(sol, max_no_improve=10)
    for _ in range(attempts):
        cand = shaking_composed(best, beta=0.02)
        cand = rvnd(cand, max_no_improve=5)
        if cand.cost + 1e-12 < best.cost:
            best = cand
    return best

# ---------------------------
# Local search wrapper (used by MH)
# ---------------------------
def local_improve(sol, intensify=False):
    if intensify:
        return farey_like_intensify(sol, attempts=20)
    else:
        return rvnd(sol, max_no_improve=20)

# ---------------------------
# GRASP utilities
# ---------------------------
def build_greedy_solution(N, alpha):
    tour = [random.randrange(N)]
    unvisited = set(range(N))
    unvisited.remove(tour[0])
    
    while unvisited:
        last = tour[-1]
        candidates = sorted(list(unvisited), key=lambda c: DIST[last][c])
        
        rcl_limit = DIST[last][candidates[0]] + alpha * (DIST[last][candidates[-1]] - DIST[last][candidates[0]])
        rcl = [c for c in candidates if DIST[last][c] <= rcl_limit]
        
        next_city = random.choice(rcl)
        tour.append(next_city)
        unvisited.remove(next_city)
        
    s = Solution(N)
    s.tour = tour
    s.cost = recompute_cost_from_tour(s.tour)
    s.sync_keys_from_tour()
    return s

# ---------------------------
# BRKGA thread
# ---------------------------
class BRKGA(threading.Thread):
    def __init__(self, pool, N, pop_size, elite_frac, mutant_frac, stop_time, rko_rho, rko_mu):
        super().__init__()
        self.pool = pool
        self.N = N
        self.pop_size = pop_size
        self.elite_frac = elite_frac
        self.mutant_frac = mutant_frac
        self.stop_time = stop_time
        self.rko_rho = rko_rho
        self.rko_mu = rko_mu
        self._stop_event = threading.Event()
        
        self.pop = [Solution(N) for _ in range(self.pop_size)]
        for s in self.pop:
            s.decode()
        self.pop.sort(key=lambda s: s.cost)

    def stop(self):
        self._stop_event.set()

    def run_one_generation(self):
        elites = self.pop[:int(self.elite_frac * self.pop_size)]
        new_pop = [e.clone() for e in elites]
        while len(new_pop) < self.pop_size - int(self.mutant_frac * self.pop_size):
            p1 = random.choice(elites)
            p2 = random.choice(self.pop)
            child = blending(p1, p2, rho=self.rko_rho, mu=self.rko_mu)
            child = local_improve(child, intensify=False)
            new_pop.append(child)
        for _ in range(int(self.mutant_frac * self.pop_size)):
            new_pop.append(Solution(self.N))
        self.pop = sorted(new_pop, key=lambda s: s.cost)
        self.pool.add(self.pop[0])

    def run(self):
        start = time.time()
        while time.time() - start < self.stop_time and not self._stop_event.is_set():
            self.run_one_generation()
            time.sleep(0.001)
        self.pool.add(self.pop[0])

# ---------------------------
# SA thread
# ---------------------------
class SA(threading.Thread):
    def __init__(self, pool, N, betamin, betamax, samax, alphasa, t0, stop_time, rko_beta):
        super().__init__()
        self.pool = pool
        self.N = N
        self.betamin = betamin
        self.betamax = betamax
        self.samax = samax
        self.alphasa = alphasa
        self.t0 = t0
        self.stop_time = stop_time
        self.rko_beta = rko_beta
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def run(self):
        current_sol = self.pool.best()
        if current_sol is None:
            current_sol = Solution(self.N)
        
        best_sol = current_sol.clone()
        temp = self.t0

        start_time = time.time()
        while time.time() - start_time < self.stop_time and not self._stop_event.is_set():
            for _ in range(self.samax):
                beta = random.uniform(self.betamin, self.betamax)
                neigh_sol = shaking_composed(current_sol, beta)
                neigh_sol = local_improve(neigh_sol, intensify=False)
                
                delta = neigh_sol.cost - current_sol.cost
                
                if delta < 0 or random.random() < math.exp(-delta / temp):
                    current_sol = neigh_sol
                    if current_sol.cost < best_sol.cost:
                        best_sol = current_sol.clone()
                        self.pool.add(best_sol)
                
                temp *= self.alphasa

                if self._stop_event.is_set():
                    break
            
            self.pool.add(best_sol)

# ---------------------------
# ILS thread
# ---------------------------
class ILS(threading.Thread):
    def __init__(self, pool, N, k_shake, max_no_improve, stop_time, rko_beta):
        super().__init__()
        self.pool = pool
        self.N = N
        self.k_shake = k_shake
        self.max_no_improve = max_no_improve
        self.stop_time = stop_time
        self.rko_beta = rko_beta
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def run(self):
        current_sol = self.pool.best()
        if current_sol is None:
            current_sol = Solution(self.N)
        
        best_sol = current_sol.clone()
        
        no_improve_count = 0
        start_time = time.time()
        while time.time() - start_time < self.stop_time and not self._stop_event.is_set():
            local_optimal = local_improve(current_sol, intensify=True)

            if local_optimal.cost < current_sol.cost:
                current_sol = local_optimal
                no_improve_count = 0
                if current_sol.cost < best_sol.cost:
                    best_sol = current_sol.clone()
                    self.pool.add(best_sol)
            else:
                no_improve_count += 1
            
            if no_improve_count >= self.max_no_improve:
                shaken_sol = shaking_composed(current_sol, self.k_shake * 0.1 / self.N)
                current_sol = shaken_sol
                no_improve_count = 0
            
            self.pool.add(best_sol)

# ---------------------------
# GRASP thread
# ---------------------------
class GRASP(threading.Thread):
    def __init__(self, pool, N, max_no_improve, alpha, stop_time):
        super().__init__()
        self.pool = pool
        self.N = N
        self.max_no_improve = max_no_improve
        self.alpha = alpha
        self.stop_time = stop_time
        self._stop_event = threading.Event()
        self.best_sol = None

    def stop(self):
        self._stop_event.set()

    def run(self):
        if self.best_sol is None:
            self.best_sol = self.pool.best()
        if self.best_sol is None:
            self.best_sol = Solution(self.N)
        
        no_improve_count = 0
        start_time = time.time()
        
        while time.time() - start_time < self.stop_time and not self._stop_event.is_set():
            candidate_sol = build_greedy_solution(self.N, self.alpha)
            local_optimal = local_improve(candidate_sol, intensify=True)

            if local_optimal.cost < self.best_sol.cost:
                self.best_sol = local_optimal.clone()
                no_improve_count = 0
                self.pool.add(self.best_sol)
            else:
                no_improve_count += 1

            if no_improve_count >= self.max_no_improve:
                break
            
            self.pool.add(self.best_sol)

# ---------------------------
# GA thread
# ---------------------------
class GA(threading.Thread):
    def __init__(self, pool, N, pop_size, pc, pm, stop_time, rko_rho, rko_mu):
        super().__init__()
        self.pool = pool
        self.N = N
        self.pop_size = pop_size
        self.pc = pc
        self.pm = pm
        self.stop_time = stop_time
        self.rko_rho = rko_rho
        self.rko_mu = rko_mu
        self._stop_event = threading.Event()
        self.pop = [Solution(N) for _ in range(self.pop_size)]
        for s in self.pop:
            s.decode()
        self.pop.sort(key=lambda s: s.cost)

    def stop(self):
        self._stop_event.set()

    def run_one_generation(self):
        parents = random.sample(self.pop, 2)
        p1 = parents[0]
        p2 = parents[1]

        child = None
        if random.random() < self.pc:
            child = blending(p1, p2, rho=0.5, mu=0.0)
        else:
            child = random.choice([p1, p2]).clone()
        
        if random.random() < self.pm:
            child = shake_swap_any(child)

        child = local_improve(child, intensify=False)
        
        weakest_idx = self.pop.index(max(self.pop, key=lambda s: s.cost))
        
        if child.cost < self.pop[weakest_idx].cost:
            self.pop[weakest_idx] = child

        self.pop.sort(key=lambda s: s.cost)
        self.pool.add(self.pop[0])

    def run(self):
        start = time.time()
        while time.time() - start < self.stop_time and not self._stop_event.is_set():
            self.run_one_generation()
            time.sleep(0.001)
        self.pool.add(self.pop[0])

# ---------------------------
# PSO thread
# ---------------------------
class PSO(threading.Thread):
    def __init__(self, pool, N, pop_size, w, c1, c2, stop_time):
        super().__init__()
        self.pool = pool
        self.N = N
        self.pop_size = pop_size
        self.w = w
        self.c1 = c1
        self.c2 = c2
        self.stop_time = stop_time
        self._stop_event = threading.Event()
        
        self.particles = []
        self.velocities = []
        self.pbest_solutions = []
        
        self.gbest_solution = None

        for _ in range(self.pop_size):
            p = Solution(self.N)
            self.particles.append(p)
            self.velocities.append([0.0] * self.N)
            self.pbest_solutions.append(p.clone())
            
    def stop(self):
        self._stop_event.set()

    def run(self):
        start_time = time.time()
        while time.time() - start_time < self.stop_time and not self._stop_event.is_set():
            current_gbest = min(self.particles, key=lambda p: p.cost)
            if self.gbest_solution is None or current_gbest.cost < self.gbest_solution.cost:
                self.gbest_solution = current_gbest.clone()

            for i in range(self.pop_size):
                if self.particles[i].cost < self.pbest_solutions[i].cost:
                    self.pbest_solutions[i] = self.particles[i].clone()
                
            self.pool.add(self.gbest_solution)

            for i in range(self.pop_size):
                r1 = random.uniform(0, 1)
                r2 = random.uniform(0, 1)
                
                new_velocities = []
                for j in range(self.N):
                    cognitive_component = self.c1 * r1 * (self.pbest_solutions[i].keys[j] - self.particles[i].keys[j])
                    social_component = self.c2 * r2 * (self.gbest_solution.keys[j] - self.particles[i].keys[j])
                    new_v = self.w * self.velocities[i][j] + cognitive_component + social_component
                    new_velocities.append(new_v)
                
                self.velocities[i] = new_velocities
                
                new_keys = []
                for j in range(self.N):
                    new_key = self.particles[i].keys[j] + self.velocities[i][j]
                    new_keys.append(new_key)
                
                self.particles[i] = Solution(self.N, keys=new_keys)

# ---------------------------
# VNS thread
# ---------------------------
class VNS(threading.Thread):
    def __init__(self, pool, N, k_max, max_no_improve, stop_time, rko_beta):
        super().__init__()
        self.pool = pool
        self.N = N
        self.k_max = k_max
        self.max_no_improve = max_no_improve
        self.stop_time = stop_time
        self.rko_beta = rko_beta
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def run(self):
        current_sol = self.pool.best()
        if current_sol is None:
            current_sol = Solution(self.N)
        
        best_sol = current_sol.clone()
        
        no_improve_count = 0
        start_time = time.time()
        
        while time.time() - start_time < self.stop_time and not self._stop_event.is_set():
            k = 1
            while k <= self.k_max and not self._stop_event.is_set():
                shaken_sol = shaking_composed(current_sol, k * self.rko_beta / self.N)
                local_optimal = rvnd(shaken_sol, max_no_improve=self.max_no_improve)

                if local_optimal.cost < current_sol.cost:
                    current_sol = local_optimal
                    k = 1
                    if current_sol.cost < best_sol.cost:
                        best_sol = current_sol.clone()
                        self.pool.add(best_sol)
                else:
                    k += 1

            self.pool.add(best_sol)
            
# ---------------------------
# LNS thread
# ---------------------------
class LNS(threading.Thread):
    def __init__(self, pool, N, factor, max_no_improve, stop_time):
        super().__init__()
        self.pool = pool
        self.N = N
        self.factor = factor
        self.max_no_improve = max_no_improve
        self.stop_time = stop_time
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()
    
    def destroy_and_repair(self, sol):
        # Destroy phase: randomly remove a number of cities
        num_removed = int(self.factor * self.N)
        removed_cities = random.sample(sol.tour, num_removed)
        current_tour = [c for c in sol.tour if c not in removed_cities]
        
        # Repair phase: greedily re-insert the removed cities
        random.shuffle(removed_cities)
        for city_to_insert in removed_cities:
            best_pos = -1
            min_cost_increase = float('inf')
            
            for pos in range(len(current_tour) + 1):
                temp_tour = list(current_tour)
                temp_tour.insert(pos, city_to_insert)
                
                cost_increase = 0.0
                if pos == 0:
                    prev_city = temp_tour[-1]
                    next_city = temp_tour[1]
                    cost_increase += DIST[prev_city][city_to_insert] + DIST[city_to_insert][next_city] - DIST[prev_city][next_city]
                elif pos == len(current_tour):
                    prev_city = temp_tour[-2]
                    next_city = temp_tour[0]
                    cost_increase += DIST[prev_city][city_to_insert] + DIST[city_to_insert][next_city] - DIST[prev_city][next_city]
                else:
                    prev_city = temp_tour[pos - 1]
                    next_city = temp_tour[pos + 1]
                    cost_increase += DIST[prev_city][city_to_insert] + DIST[city_to_insert][next_city] - DIST[prev_city][next_city]
                
                if cost_increase < min_cost_increase:
                    min_cost_increase = cost_increase
                    best_pos = pos

            current_tour.insert(best_pos, city_to_insert)
            
        new_sol = Solution(self.N)
        new_sol.tour = current_tour
        new_sol.cost = recompute_cost_from_tour(new_sol.tour)
        new_sol.sync_keys_from_tour()
        return new_sol

    def run(self):
        current_sol = self.pool.best()
        if current_sol is None:
            current_sol = Solution(self.N)

        best_sol = current_sol.clone()
        no_improve_count = 0
        start_time = time.time()

        while time.time() - start_time < self.stop_time and not self._stop_event.is_set():
            # Destruir e Reparar
            candidate_sol = self.destroy_and_repair(current_sol)
            
            # Melhoria com busca local
            local_optimal = rvnd(candidate_sol, max_no_improve=self.max_no_improve)
            
            if local_optimal.cost < current_sol.cost:
                current_sol = local_optimal
                no_improve_count = 0
                if current_sol.cost < best_sol.cost:
                    best_sol = current_sol.clone()
                    self.pool.add(best_sol)
            else:
                no_improve_count += 1
            
            if no_improve_count >= self.max_no_improve:
                break
            
            self.pool.add(best_sol)

# ---------------------------
# Instance loading / main
# ---------------------------
def load_instance(path):
    global INSTANCE_NAME
    try:
        if path:
            coords, name = read_tsplib_coords(path)
            INSTANCE_NAME = name
            print(f"Loaded {len(coords)} coords from {path}")
            return coords, name
        else:
            coords = generate_random_coords(208, seed=SEED + 1)
            name = "Synthetic"
            print("Synthetic instance with 208 nodes generated.")
            return coords, name
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"File {path} not found, generating synthetic 208-node instance.")
        coords = generate_random_coords(208, seed=SEED + 1)
        name = "Synthetic"
        print("Synthetic instance with 208 nodes generated.")
        return coords, name
    except Exception as e:
        print("Error reading file, generating synthetic:", e)
        coords = generate_random_coords(208, seed=SEED + 1)
        name = "Synthetic"
        print("Synthetic instance with 208 nodes generated.")
        return coords, name

def plot_solution(coords, tour, output_file, instance_name, best_cost, agents_to_run):
    x = [coords[i][0] for i in tour]
    y = [coords[i][1] for i in tour]

    plt.figure(figsize=(10, 8))
    plt.plot(x, y, 'o-', mfc='r', mec='k')
    
    x_last = coords[tour[-1]][0]
    y_last = coords[tour[-1]][1]
    x_first = coords[tour[0]][0]
    y_first = coords[tour[0]][1]
    plt.plot([x_last, x_first], [y_last, y_first], 'r-')
    
    agents_str = ', '.join(agents_to_run)
    title_str = f"{instance_name}, Custo: {best_cost:.3f}\n{agents_str}"
    
    plt.title(title_str)
    plt.xlabel("Coordenada X")
    plt.ylabel("Coordenada Y")
    plt.grid(True)
    plt.savefig(output_file)
    print(f"Solução plotada em '{output_file}'")

def print_parameters(args, agents_to_run):
    print("-" * 50)
    print("RKO Global Parameters:")
    print(f"  Run Time Limit: {args.rko_timelimit}s (change with --rko-timelimit)")
    print(f"  Elite Pool Max Size: {args.rko_pool_max} (change with --rko-pool-max)")
    print(f"  Shaking Factor (Beta): {args.rko_beta} (change with --rko-beta)")
    print(f"  Blending Rho: {args.rko_rho} (change with --rko-rho)")
    print(f"  Blending Mu: {args.rko_mu} (change with --rko-mu)")
    
    if 'BRKGA' in agents_to_run:
        print("\nBRKGA Parameters:")
        print(f"  Population Size: {args.brkga_pop_size} (change with --brkga-pop-size)")
        print(f"  Elite Fraction: {args.brkga_elite_frac} (change with --brkga-elite-frac)")
        print(f"  Mutant Fraction: {args.brkga_mutant_frac} (change with --brkga-mutant-frac)")
    
    if 'SA' in agents_to_run:
        print("\nSA Parameters:")
        print(f"  Beta Min: {args.sa_betamin} (change with --sa-betamin)")
        print(f"  Beta Max: {args.sa_betamax} (change with --sa-betamax)")
        print(f"  SA Max: {args.sa_samax} (change with --sa-samax)")
        print(f"  Alpha SA: {args.sa_alphasa} (change with --sa-alphasa)")
        print(f"  T0: {args.sa_t0} (change with --sa-t0)")
    
    if 'ILS' in agents_to_run:
        print("\nILS Parameters:")
        print(f"  K Shake: {args.ils_k} (change with --ils-k)")
        print(f"  Max No Improve: {args.ils_max_no_improve} (change with --ils-max-no-improve)")
        print(f"  Beta Shake: {args.ils_beta_shake} (change with --ils-beta-shake)")
    
    if 'GRASP' in agents_to_run:
        print("\nGRASP Parameters:")
        print(f"  Max No Improve: {args.grasp_max_no_improve} (change with --grasp-max-no-improve)")
        print(f"  Alpha: {args.grasp_alpha} (change with --grasp-alpha)")
    
    if 'GA' in agents_to_run:
        print("\nGA Parameters:")
        print(f"  Population Size: {args.ga_pop_size} (change with --ga-pop-size)")
        print(f"  Crossover Probability (Pc): {args.ga_pc} (change with --ga-pc)")
        print(f"  Mutation Probability (Pm): {args.ga_pm} (change with --ga-pm)")
    
    if 'PSO' in agents_to_run:
        print("\nPSO Parameters:")
        print(f"  Population Size: {args.pso_pop_size} (change with --pso-pop-size)")
        print(f"  Inertia (w): {args.pso_w} (change with --pso-w)")
        print(f"  Cognitive Weight (c1): {args.pso_c1} (change with --pso-c1)")
        print(f"  Social Weight (c2): {args.pso_c2} (change with --pso-c2)")
    
    if 'VNS' in agents_to_run:
        print("\nVNS Parameters:")
        print(f"  K Max: {args.vns_k_max} (change with --vns-k-max)")
        print(f"  Max No Improve: {args.vns_max_no_improve} (change with --vns-max-no-improve)")

    if 'LNS' in agents_to_run:
        print("\nLNS Parameters:")
        print(f"  Factor: {args.lns_factor} (change with --lns-factor)")
        print(f"  Max No Improve: {args.lns_max_no_improve} (change with --lns-max-no-improve)")
    
    print("-" * 50)

def main():
    global DIST, COORDS, INSTANCE_NAME
    
    parser = argparse.ArgumentParser(description="RKO-lite: A multi-agent metaheuristic for TSP.")
    parser.add_argument("instance_path", nargs="?", default=None, help="Path to the TSPLIB instance file.")
    parser.add_argument("--agents", type=str, default="all", help="Comma-separated list of agents to run (e.g., SA,GRASP). 'all' by default.")
    
    # RKO Global parameters
    parser.add_argument("--rko-timelimit", type=float, dest='rko_timelimit', default=RKO_DEFAULTS['timelimit'], help="Run time limit in seconds.")
    parser.add_argument("--rko-pool-max", type=int, dest='rko_pool_max', default=RKO_DEFAULTS['pool_max'], help="Max size of the elite pool.")
    parser.add_argument("--rko-beta", type=float, dest='rko_beta', default=RKO_DEFAULTS['beta'], help="Shaking factor.")
    parser.add_argument("--rko-rho", type=float, dest='rko_rho', default=RKO_DEFAULTS['rho'], help="Blending inheritance probability.")
    parser.add_argument("--rko-mu", type=float, dest='rko_mu', default=RKO_DEFAULTS['mu'], help="Blending mutation probability.")
    
    # BRKGA parameters
    parser.add_argument("--brkga-pop-size", type=int, dest='brkga_pop_size', default=BRKGA_DEFAULTS['pop_size'], help="BRKGA population size.")
    parser.add_argument("--brkga-elite-frac", type=float, dest='brkga_elite_frac', default=BRKGA_DEFAULTS['elite_frac'], help="BRKGA elite fraction.")
    parser.add_argument("--brkga-mutant-frac", type=float, dest='brkga_mutant_frac', default=BRKGA_DEFAULTS['mutant_frac'], help="BRKGA mutant fraction.")

    # SA parameters
    parser.add_argument("--sa-betamin", type=float, dest='sa_betamin', default=SA_DEFAULTS['betamin'], help="SA beta min.")
    parser.add_argument("--sa-betamax", type=float, dest='sa_betamax', default=SA_DEFAULTS['betamax'], help="SA beta max.")
    parser.add_argument("--sa-samax", type=int, dest='sa_samax', default=SA_DEFAULTS['samax'], help="SA max iterations.")
    parser.add_argument("--sa-alphasa", type=float, dest='sa_alphasa', default=SA_DEFAULTS['alphasa'], help="SA alpha.")
    parser.add_argument("--sa-t0", type=float, dest='sa_t0', default=SA_DEFAULTS['t0'], help="SA initial temperature.")
    
    # ILS parameters
    parser.add_argument("--ils-k", type=int, dest='ils_k', default=ILS_DEFAULTS['k'], help="ILS k-shake.")
    parser.add_argument("--ils-max-no-improve", type=int, dest='ils_max_no_improve', default=ILS_DEFAULTS['max_no_improve'], help="ILS max no improve iterations.")
    parser.add_argument("--ils-beta-shake", type=float, dest='ils_beta_shake', default=ILS_DEFAULTS['beta_shake'], help="ILS beta shake.")

    # GRASP parameters
    parser.add_argument("--grasp-max-no-improve", type=int, dest='grasp_max_no_improve', default=GRASP_DEFAULTS['max_no_improve'], help="GRASP max no improve iterations.")
    parser.add_argument("--grasp-alpha", type=float, dest='grasp_alpha', default=GRASP_DEFAULTS['alpha'], help="GRASP alpha.")

    # GA parameters
    parser.add_argument("--ga-pop-size", type=int, dest='ga_pop_size', default=GA_DEFAULTS['pop_size'], help="GA population size.")
    parser.add_argument("--ga-pc", type=float, dest='ga_pc', default=GA_DEFAULTS['pc'], help="GA crossover probability.")
    parser.add_argument("--ga-pm", type=float, dest='ga_pm', default=GA_DEFAULTS['pm'], help="GA mutation probability.")

    # PSO parameters
    parser.add_argument("--pso-pop-size", type=int, dest='pso_pop_size', default=PSO_DEFAULTS['pop_size'], help="PSO population size.")
    parser.add_argument("--pso-w", type=float, dest='pso_w', default=PSO_DEFAULTS['w'], help="PSO inertia.")
    parser.add_argument("--pso-c1", type=float, dest='pso_c1', default=PSO_DEFAULTS['c1'], help="PSO cognitive weight.")
    parser.add_argument("--pso-c2", type=float, dest='pso_c2', default=PSO_DEFAULTS['c2'], help="PSO social weight.")

    # VNS parameters
    parser.add_argument("--vns-k-max", type=int, dest='vns_k_max', default=VNS_DEFAULTS['k_max'], help="VNS k-max.")
    parser.add_argument("--vns-max-no-improve", type=int, dest='vns_max_no_improve', default=VNS_DEFAULTS['max_no_improve'], help="VNS max no improve iterations.")

    # LNS parameters
    parser.add_argument("--lns-factor", type=float, dest='lns_factor', default=LNS_DEFAULTS['factor'], help="LNS removal factor.")
    parser.add_argument("--lns-max-no-improve", type=int, dest='lns_max_no_improve', default=LNS_DEFAULTS['max_no_improve'], help="LNS max no improve iterations.")

    args = parser.parse_args()
    
    agents_to_run = [a.upper() for a in args.agents.split(',')]
    if 'ALL' in agents_to_run:
        agents_to_run = ['BRKGA', 'SA', 'ILS', 'GRASP', 'GA', 'PSO', 'VNS', 'LNS']

    if args.instance_path:
        COORDS, INSTANCE_NAME = load_instance(args.instance_path)
    else:
        COORDS, INSTANCE_NAME = load_instance(None)
    
    N = len(COORDS)
    DIST = build_distance_matrix(COORDS)
    
    print_parameters(args, agents_to_run)
    
    pool = Pool(max_size=args.rko_pool_max)

    print("Initializing pool with refined random solutions...")
    for _ in range(INITIAL_POOL_REFINES):
        s = Solution(N)
        s = farey_like_intensify(s, attempts=50)
        pool.add(s)
    print("Initial pool size:", len(pool.elites))
    
    threads = []
    if 'BRKGA' in agents_to_run:
        threads.append(BRKGA(pool, N=N, pop_size=args.brkga_pop_size, elite_frac=args.brkga_elite_frac, mutant_frac=args.brkga_mutant_frac, stop_time=args.rko_timelimit, rko_rho=args.rko_rho, rko_mu=args.rko_mu))
    if 'SA' in agents_to_run:
        threads.append(SA(pool, N=N, betamin=args.sa_betamin, betamax=args.sa_betamax, samax=args.sa_samax, alphasa=args.sa_alphasa, t0=args.sa_t0, stop_time=args.rko_timelimit, rko_beta=args.rko_beta))
    if 'ILS' in agents_to_run:
        threads.append(ILS(pool, N=N, k_shake=args.ils_k, max_no_improve=args.ils_max_no_improve, stop_time=args.rko_timelimit, rko_beta=args.rko_beta))
    if 'GRASP' in agents_to_run:
        threads.append(GRASP(pool, N=N, max_no_improve=args.grasp_max_no_improve, alpha=args.grasp_alpha, stop_time=args.rko_timelimit))
    if 'GA' in agents_to_run:
        threads.append(GA(pool, N=N, pop_size=args.ga_pop_size, pc=args.ga_pc, pm=args.ga_pm, stop_time=args.rko_timelimit, rko_rho=args.rko_rho, rko_mu=args.rko_mu))
    if 'PSO' in agents_to_run:
        threads.append(PSO(pool, N=N, pop_size=args.pso_pop_size, w=args.pso_w, c1=args.pso_c1, c2=args.pso_c2, stop_time=args.rko_timelimit))
    if 'VNS' in agents_to_run:
        threads.append(VNS(pool, N=N, k_max=args.vns_k_max, max_no_improve=args.vns_max_no_improve, stop_time=args.rko_timelimit, rko_beta=args.rko_beta))
    if 'LNS' in agents_to_run:
        threads.append(LNS(pool, N=N, factor=args.lns_factor, max_no_improve=args.lns_max_no_improve, stop_time=args.rko_timelimit))

    print(f"Running {', '.join(agents_to_run)} in parallel for {args.rko_timelimit} seconds...")
    
    start_time = time.time()
    threading.main_thread().start_time = start_time
    
    for t in threads:
        t.start()

    try:
        while threading.active_count() > 1:
            time.sleep(2.0)
            best = pool.best()
            if best:
                print(f"[{time.time() - threading.main_thread().start_time:6.1f}s] pool best = {best.cost:.3f}")
    except KeyboardInterrupt:
        print("Interrupted. Stopping threads...")
        for t in threads:
            t.stop()

    for t in threads:
        t.join()

    print("Final pool (top solutions):")
    for i, s in enumerate(pool.snapshot()):
        print(f"#{i+1:2d} cost={s.cost:.3f} (tour: {s.tour})")
    
    if pool.elites:
        best_solution = pool.elites[0]
        print("Best cost:", best_solution.cost)
        output_file = f"{INSTANCE_NAME}-solution.png"
        plot_solution(COORDS, best_solution.tour, output_file, INSTANCE_NAME, best_solution.cost, agents_to_run)

if __name__ == "__main__":
    main()
