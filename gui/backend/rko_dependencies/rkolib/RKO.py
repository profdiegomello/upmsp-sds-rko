import os
import numpy as np
import pandas as pd
import time
import random
import copy
import math
import datetime
import bisect
import itertools
import sys
from multiprocessing import Manager, Process, Queue

# UTILITARIOS DE IO
class QueueWriter:
    """Redireciona sys.stdout para uma multiprocessing.Queue"""
    def __init__(self, queue):
        self.queue = queue

    def write(self, text):
        if text:
            self.queue.put(str(text))

    def flush(self):
        pass

class SolutionPool:
    def __init__(self, size, pool, best_pair, lock=None, print_flag=False, Best=None, env=None):
        self.size = size
        self.pool = pool
        self.best_pair = best_pair
        self.lock = lock
        self.start_time = time.time()
        self.print_flag = print_flag 
        self.best_possible = Best
        self.env = env

    def insert(self, entry_tuple, metaheuristic_name, tag):
        fitness = entry_tuple[0]
        keys = entry_tuple[1]

        with self.lock:
            if fitness < self.best_pair[0]:
                self.best_pair[0] = fitness
                self.best_pair[1] = list(keys)
                self.best_pair[2] = round(self.start_time - time.time(), 2)

                if self.print_flag:
                    tempo = abs(round(self.start_time - time.time(), 2))
                    if self.best_possible is not None:
                        print(f"[{metaheuristic_name}] NEW BEST: {fitness:.4f} (Target: {self.best_possible}) - Time: {tempo}s")
                    else:
                        print(f"[{metaheuristic_name}] NEW BEST: {fitness:.4f} - Time: {tempo}s")

            bisect.insort(self.pool, entry_tuple)
            if len(self.pool) > self.size:
                self.pool.pop()

# =============================================================================
# CLASSE RKO (CORE)
# =============================================================================

class RKO:
    def __init__(self, env, print_best=False, save_directory=None, log_queue=None):
        self.env = env
        self.__MAX_KEYS = self.env.tam_solution
        self.LS_type = self.env.LS_type
        self.start_time = time.time()
        self.max_time = self.env.max_time
        self.rate = 1
        self.print_best = print_best
        self.save_directory = save_directory
        self.q_managers = {}
        self.log_queue = log_queue 

    def _setup_parameters(self, metaheuristic_name, params_config):
        is_online = any(len(v) > 1 for v in params_config.values())

        if is_online:
            if metaheuristic_name not in self.q_managers:
                self.q_managers[metaheuristic_name] = QLearningManager(
                    parameters_config=params_config,
                    max_time=self.max_time,
                    metaheuristic_name=metaheuristic_name,
                    save_report=self.env.save_q_learning_report
                )
            q_manager = self.q_managers[metaheuristic_name]
            initial_params = q_manager.get_current_parameters()
            return q_manager, initial_params
        else:
            static_params = {k: v[0] for k, v in params_config.items()}
            return None, static_params

    def random_keys(self):
        return np.random.random(self.__MAX_KEYS)

    def shaking(self, keys, beta_min, beta_max):
        beta = random.uniform(beta_min, beta_max)
        new_keys = copy.deepcopy(keys)
        num_perturbations = max(1, int(self.__MAX_KEYS * beta))

        for _ in range(num_perturbations):
            move_type = random.choice(['Swap', 'SwapN', 'Invert', 'Random'])
            if move_type == 'Swap':
                idx1, idx2 = random.sample(range(self.__MAX_KEYS), 2)
                new_keys[idx1], new_keys[idx2] = new_keys[idx2], new_keys[idx1]
            elif move_type == 'SwapN':
                idx = random.randint(0, self.__MAX_KEYS - 1)
                idx2 = idx + 1 if idx == 0 else (idx - 1 if idx == self.__MAX_KEYS - 1 else random.choice([idx - 1, idx + 1]))
                new_keys[idx], new_keys[idx2] = new_keys[idx2], new_keys[idx]
            elif move_type == 'Invert':
                idx = random.randint(0, self.__MAX_KEYS - 1)
                new_keys[idx] = 1 - new_keys[idx]
            elif move_type == 'Random':
                idx = random.randint(0, self.__MAX_KEYS - 1)
                new_keys[idx] = random.random()
        return new_keys

    def Blending(self, keys1, keys2, factor):
        new_keys = np.zeros(self.__MAX_KEYS)
        for i in range(self.__MAX_KEYS):
            if random.random() < 0.02:
                new_keys[i] = random.random()
            else:
                if random.random() < 0.5:
                    new_keys[i] = keys1[i]
                else:
                    if factor == -1:
                        new_keys[i] = max(0.0, min(1.0 - keys2[i], 0.9999999))
                    else:
                        new_keys[i] = keys2[i]
        return new_keys

    def SwapLS(self, keys, metaheuristic_name="SwapLS"):
        if self.LS_type == 'Best':
            swap_order = [i for i in range(int(self.rate * self.__MAX_KEYS))]
            random.shuffle(swap_order)
            best_keys = copy.deepcopy(keys)
            best_cost = self.env.cost(self.env.decoder(best_keys))

            for idx1 in swap_order:
                for idx2 in reversed(swap_order):
                    if self.stop_condition(best_cost, metaheuristic_name, -1): return best_keys
                    new_keys = copy.deepcopy(best_keys)
                    new_keys[idx1], new_keys[idx2] = new_keys[idx2], new_keys[idx1]
                    new_cost = self.env.cost(self.env.decoder(new_keys))
                    if new_cost < best_cost:
                        best_keys, best_cost = new_keys, new_cost
            return best_keys
        elif self.LS_type == 'First':
            swap_order = [i for i in range(int(self.rate * self.__MAX_KEYS))]
            random.shuffle(swap_order)
            best_keys = copy.deepcopy(keys)
            best_cost = self.env.cost(self.env.decoder(best_keys))
            for idx1 in swap_order:
                for idx2 in reversed(swap_order):
                    if self.stop_condition(best_cost, metaheuristic_name, -1): return best_keys
                    new_keys = copy.deepcopy(best_keys)
                    new_keys[idx1], new_keys[idx2] = new_keys[idx2], new_keys[idx1]
                    new_cost = self.env.cost(self.env.decoder(new_keys))
                    if new_cost < best_cost: return new_keys
            return best_keys
        return keys

    def FareyLS(self, keys, metaheuristic_name="FareyLS"):
        Farey_Sequence = [0.00, 0.142857, 0.166667, 0.20, 0.25, 0.285714, 0.333333, 0.40, 0.428571, 0.50,
                             0.571429, 0.60, 0.666667, 0.714286, 0.75, 0.80, 0.833333, 0.857143, 1.0]
        swap_order = [i for i in range(int(self.rate * self.__MAX_KEYS))]
        random.shuffle(swap_order)
        best_keys = copy.deepcopy(keys)
        best_cost = self.env.cost(self.env.decoder(best_keys))

        for idx in swap_order:
             for i in range(len(Farey_Sequence) - 1):
                if self.stop_condition(best_cost, metaheuristic_name, -1): return best_keys
                new_keys = copy.deepcopy(best_keys)
                new_keys[idx] = random.uniform(Farey_Sequence[i], Farey_Sequence[i+1])
                new_cost = self.env.cost(self.env.decoder(new_keys))
                if new_cost < best_cost:
                    best_keys, best_cost = new_keys, new_cost
                    if self.LS_type == 'First': return new_keys
        return best_keys

    def InvertLS(self, keys, metaheuristic_name="InvertLS"):
        swap_order = [i for i in range(int(self.__MAX_KEYS))]
        random.shuffle(swap_order)
        best_keys = copy.deepcopy(keys)
        best_cost = self.env.cost(self.env.decoder(best_keys))

        if self.LS_type == 'Best':
            blocks = []
            while swap_order:
                block = swap_order[:int(self.rate * self.__MAX_KEYS)]
                swap_order = swap_order[int(self.rate * self.__MAX_KEYS):]
                blocks.append(block)
            for block in blocks:
                if self.stop_condition(best_cost, metaheuristic_name, -1): return best_keys
                new_keys = copy.deepcopy(best_keys)
                for idx in block: new_keys[idx] = 1 - new_keys[idx]
                new_cost = self.env.cost(self.env.decoder(new_keys))
                if new_cost < best_cost: best_keys, best_cost = new_keys, new_cost
        elif self.LS_type == 'First':
             for idx in range(int(self.rate * self.__MAX_KEYS)):
                if self.stop_condition(best_cost, metaheuristic_name, -1): return best_keys
                new_keys = copy.deepcopy(best_keys)
                new_keys[idx] = 1 - new_keys[idx]
                new_cost = self.env.cost(self.env.decoder(new_keys))
                if new_cost < best_cost: return new_keys
        return best_keys

    def NelderMeadSearch(self, keys, pool=None, metaheuristic_name="NelderMeadSearch"):
        improved, improvedX1 = 0, 0
        keys_origem = copy.deepcopy(keys)
        x1 = copy.deepcopy(keys)
        
        if pool is None or len(pool.pool) == 0:
            x2, x3 = self.random_keys(), self.random_keys()
        else:
            x2 = random.choice(list(pool.pool))[1]
            x3 = random.choice(list(pool.pool))[1]
            while x2 == x3 and len(pool.pool) > 1: x2 = random.choice(list(pool.pool))[1]

        fit1 = self.env.cost(self.env.decoder(x1))
        fit2 = self.env.cost(self.env.decoder(x2))
        fit3 = self.env.cost(self.env.decoder(x3))

        if fit1 > fit2: x1, x2, fit1, fit2 = x2, x1, fit2, fit1
        if fit1 > fit3: x1, x3, fit1, fit3 = x3, x1, fit3, fit1
        if fit2 > fit3: x2, x3, fit2, fit3 = x3, x2, fit3, fit2

        xBest, fitBest = copy.deepcopy(x1), fit1
        x0 = self.Blending(x1, x2, 1)
        fit0 = self.env.cost(self.env.decoder(x0))
        if fit0 < fitBest: xBest, fitBest, improved = copy.deepcopy(x0), fit0, 1

        iter_count = 1
        max_iter = int(self.__MAX_KEYS * math.exp(-2))

        while iter_count <= (max_iter * self.rate):
            if self.stop_condition(fitBest, metaheuristic_name, -1): return xBest
            shrink = 0
            x_r = self.Blending(x0, x3, -1)
            fit_r = self.env.cost(self.env.decoder(x_r))
            
            if fit_r < fitBest: xBest, fitBest, improved, improvedX1 = copy.deepcopy(x_r), fit_r, 1, 1

            if fit_r < fit1:
                x_e = self.Blending(x_r, x0, -1)
                fit_e = self.env.cost(self.env.decoder(x_e))
                if fit_e < fitBest: xBest, fitBest, improved, improvedX1 = copy.deepcopy(x_e), fit_e, 1, 1
                if fit_e < fit_r: x3, fit3 = copy.deepcopy(x_e), fit_e
                else: x3, fit3 = copy.deepcopy(x_r), fit_r
            elif fit_r < fit2:
                x3, fit3 = copy.deepcopy(x_r), fit_r
            else:
                if fit_r < fit3:
                    x_c = self.Blending(x_r, x0, 1)
                    fit_c = self.env.cost(self.env.decoder(x_c))
                    if fit_c < fitBest: xBest, fitBest, improved, improvedX1 = copy.deepcopy(x_c), fit_c, 1, 1
                    if fit_c < fit_r: x3, fit3 = copy.deepcopy(x_c), fit_c
                    else: shrink = 1
                else:
                    x_c = self.Blending(x0, x3, 1)
                    fit_c = self.env.cost(self.env.decoder(x_c))
                    if fit_c < fitBest: xBest, fitBest, improved, improvedX1 = copy.deepcopy(x_c), fit_c, 1, 1
                    if fit_c < fit3: x3, fit3 = copy.deepcopy(x_c), fit_c
                    else: shrink = 1

            if shrink:
                x2 = self.Blending(x1, x2, 1)
                fit2 = self.env.cost(self.env.decoder(x2))
                if fit2 < fitBest: xBest, fitBest, improved, improvedX1 = copy.deepcopy(x2), fit2, 1, 1
                x3 = self.Blending(x1, x3, 1)
                fit3 = self.env.cost(self.env.decoder(x3))
                if fit3 < fitBest: xBest, fitBest, improved, improvedX1 = copy.deepcopy(x3), fit3, 1, 1

            if fit1 > fit2: x1, x2, fit1, fit2 = x2, x1, fit2, fit1
            if fit1 > fit3: x1, x3, fit1, fit3 = x3, x1, fit3, fit1
            if fit2 > fit3: x2, x3, fit2, fit3 = x3, x2, fit3, fit2

            x0 = self.Blending(x1, x2, 1)
            fit0 = self.env.cost(self.env.decoder(x0))
            if fit0 < fitBest: xBest, fitBest, improved, improvedX1 = copy.deepcopy(x0), fit0, 1, 1

            if improved == 1: improved, iter_count = 0, 0
            else: iter_count += 1

        return xBest if improvedX1 == 1 else keys_origem

    def RVND(self, keys, pool=None, metaheuristic_name="RVND"):
        best_keys = copy.deepcopy(keys)
        best_cost = self.env.cost(self.env.decoder(best_keys))
        neighborhoods = ['SwapLS', 'NelderMeadSearch', 'FareyLS', 'InvertLS']
        not_used_nb = copy.deepcopy(neighborhoods)

        while not_used_nb:
            current = random.choice(not_used_nb)
            if current == 'SwapLS': new_keys = self.SwapLS(best_keys, metaheuristic_name)
            elif current == 'NelderMeadSearch': new_keys = self.NelderMeadSearch(best_keys, pool, metaheuristic_name)
            elif current == 'FareyLS': new_keys = self.FareyLS(best_keys, metaheuristic_name)
            elif current == 'InvertLS': new_keys = self.InvertLS(best_keys, metaheuristic_name)

            new_cost = self.env.cost(self.env.decoder(new_keys))
            if new_cost < best_cost:
                best_keys, best_cost = new_keys, new_cost
                not_used_nb = copy.deepcopy(neighborhoods)
                if pool: pool.insert((best_cost, list(best_keys)), metaheuristic_name, -1)
            else:
                not_used_nb.remove(current)
            
            if self.stop_condition(best_cost, metaheuristic_name, -1): return best_keys
        return best_keys

    def MultiStart(self, tag, pool):
        metaheuristic_name = f"MS {tag}"
        start_time, tempo_max = time.time(), self.max_time
        keys = self.random_keys()
        best_keys, best_cost = keys, self.env.cost(self.env.decoder(keys))
        
        pool.insert((best_cost, list(best_keys)), metaheuristic_name, tag)
        if self.stop_condition(best_cost, metaheuristic_name, tag, pool=pool): return [], best_keys, best_cost

        while time.time() - start_time < tempo_max:
            k1 = random.choice(list(pool.pool))[1] if len(pool.pool) > 0 else self.random_keys()
            new_keys = self.RVND(metaheuristic_name=metaheuristic_name, pool=pool, keys=self.shaking(k1, 0.1, 0.3))
            new_cost = self.env.cost(self.env.decoder(new_keys))

            if new_cost < best_cost:
                best_keys, best_cost = new_keys, new_cost
                pool.insert((best_cost, list(best_keys)), metaheuristic_name, tag)
            if self.stop_condition(best_cost, metaheuristic_name, tag, pool=pool): return [], best_keys, best_cost
        return [], best_keys, best_cost

    def SimulatedAnnealing(self, tag, pool):
        metaheuristic_name = f"SA {tag}"
        q_manager, params = self._setup_parameters(metaheuristic_name, self.env.SA_parameters)
        SAmax, T0, alpha, beta_min, beta_max = params['SAmax'], params['T0'], params['alphaSA'], params['betaMin'], params['betaMax']
        
        start_time, keys = time.time(), self.random_keys()
        s, best_keys = keys, keys
        s_cost = best_cost = self.env.cost(self.env.decoder(s))
        
        pool.insert((best_cost, list(best_keys)), metaheuristic_name, tag)
        if self.stop_condition(best_cost, metaheuristic_name, tag, pool=pool): return [], best_keys, best_cost

        while time.time() - start_time < self.max_time:
            if q_manager:
                new_params = q_manager.select_action(time.time() - self.start_time)
                SAmax, T0, alpha, beta_min, beta_max = new_params['SAmax'], new_params['T0'], new_params['alphaSA'], new_params['betaMin'], new_params['betaMax']

            T, improvement_flag, best_cost_in_cycle = T0, 0, best_cost
            while T > 0.0001 and (time.time() - start_time < self.max_time):
                iter_at_temp, best_ofv_in_temp = 0, float('inf')
                while iter_at_temp < SAmax:
                    iter_at_temp += 1
                    new_keys = self.shaking(s, beta_min, beta_max)
                    new_cost = self.env.cost(self.env.decoder(new_keys))
                    if new_cost < best_ofv_in_temp: best_ofv_in_temp = new_cost
                    
                    delta = new_cost - s_cost
                    if delta < 0 or random.random() < math.exp(-delta / T):
                        s, s_cost = new_keys, new_cost
                        if s_cost < best_cost:
                            best_cost, best_keys, improvement_flag = s_cost, s, 1
                            pool.insert((best_cost, list(best_keys)), metaheuristic_name, tag)
                            if self.stop_condition(best_cost, metaheuristic_name, tag, pool=pool): return [], best_keys, best_cost
                T *= alpha

            if q_manager:
                reward = 1.0 if improvement_flag else (best_cost_in_cycle - best_ofv_in_temp) / best_cost_in_cycle if best_cost_in_cycle > 0 else 0
                q_manager.update_q_value(reward, time.time() - self.start_time)
        return [], best_keys, best_cost

    def VNS(self, limit_time, tag, pool):
        metaheuristic_name = f"VNS {tag}"
        q_manager, params = self._setup_parameters(metaheuristic_name, self.env.VNS_parameters)
        k_max, beta_min = params['kMax'], params['betaMin']
        
        start_time, keys = time.time(), self.random_keys()
        best_keys = current_s = self.RVND(metaheuristic_name=metaheuristic_name, pool=pool, keys=keys)
        best_cost = current_cost = self.env.cost(self.env.decoder(best_keys))

        pool.insert((best_cost, list(best_keys)), metaheuristic_name, tag)
        if self.stop_condition(best_cost, metaheuristic_name, tag, pool=pool): return [], best_keys, best_cost

        while time.time() - start_time < limit_time:
            if q_manager:
                new_params = q_manager.select_action(time.time() - start_time)
                k_max, beta_min = new_params['kMax'], new_params['betaMin']
            
            k, improvement_flag, cost_before = 1, 0, current_cost
            while k <= k_max:
                if self.stop_condition(best_cost, metaheuristic_name, tag, pool=pool): return [], best_keys, best_cost
                s2 = self.RVND(metaheuristic_name=metaheuristic_name, pool=pool, keys=self.shaking(current_s, k * beta_min, (k + 1) * beta_min))
                cost = self.env.cost(self.env.decoder(s2))

                if cost < current_cost:
                    current_s, current_cost, k = s2, cost, 1
                    if cost < best_cost:
                        best_cost, best_keys, improvement_flag = cost, s2, 1
                        pool.insert((best_cost, list(best_keys)), metaheuristic_name, tag)
                else: k += 1
            
            if q_manager:
                reward = 1.0 if improvement_flag else (cost_before - current_cost) / cost_before if cost_before > 0 else 0
                q_manager.update_q_value(reward, time.time() - start_time)
        return [], best_keys, best_cost

    def LNS(self, limit_time, tag, pool):
        metaheuristic_name = f"LNS {tag}"
        q_manager, params = self._setup_parameters(metaheuristic_name, self.env.LNS_parameters)
        beta_min, beta_max, T0, alphaLNS = params['betaMin'], params['betaMax'], params['TO'], params['alphaLNS']
        
        Farey_Sequence = [0.00, 0.142857, 0.166667, 0.20, 0.25, 0.285714, 0.333333, 0.40, 0.428571, 0.50,
                             0.571429, 0.60, 0.666667, 0.714286, 0.75, 0.80, 0.833333, 0.857143, 1.0]
        start_time, s = time.time(), self.random_keys()
        best_keys, s_cost = s, self.env.cost(self.env.decoder(s))
        best_cost = s_cost

        pool.insert((best_cost, list(best_keys)), metaheuristic_name, tag)
        if self.stop_condition(best_cost, metaheuristic_name, tag, pool=pool): return [], best_keys, best_cost
        
        reanneling = False
        while time.time() - start_time < limit_time:
            if q_manager:
                new_params = q_manager.select_action(time.time() - start_time)
                beta_min, beta_max, T0, alphaLNS = new_params['betaMin'], new_params['betaMax'], new_params['TO'], new_params['alphaLNS']
            
            improvement_flag, cost_before = 0, best_cost
            T = T0 * 0.3 if reanneling else T0
            
            while T > 0.01 and (time.time() - start_time < limit_time):
                s_line = copy.deepcopy(s)
                intensity = int(random.uniform(beta_min * self.__MAX_KEYS, beta_max * self.__MAX_KEYS))
                RKorder = random.sample(range(self.__MAX_KEYS), len(range(self.__MAX_KEYS)))

                for k in range(intensity):
                    pos = RKorder[k]
                    best_rk_val, rkBestCost = s_line[pos], float('inf')
                    for val in Farey_Sequence[:-1]: 
                        if self.stop_condition(best_cost, metaheuristic_name, tag, pool=pool): return [], best_keys, best_cost
                        s_line[pos] = random.uniform(val, Farey_Sequence[Farey_Sequence.index(val)+1])
                        new_cost = self.env.cost(self.env.decoder(s_line))
                        if new_cost < rkBestCost: rkBestCost, best_rk_val = new_cost, s_line[pos]
                    s_line[pos] = best_rk_val
                
                s_best_line = self.NelderMeadSearch(keys=s_line, pool=pool)
                best_cost_s1 = self.env.cost(self.env.decoder(s_best_line))
                
                delta = best_cost_s1 - s_cost
                if delta <= 0:
                    s, s_cost = s_best_line, best_cost_s1
                    if s_cost < best_cost:
                        best_cost, best_keys, improvement_flag = s_cost, s, 1
                        pool.insert((best_cost, list(best_keys)), metaheuristic_name, tag)
                elif random.random() < math.exp(-delta / T):
                    s, s_cost = s_best_line, best_cost_s1
                T *= alphaLNS

            reanneling = True
            if q_manager:
                reward = 1.0 if improvement_flag else (cost_before - best_cost) / cost_before if cost_before > 0 else 0
                q_manager.update_q_value(reward, time.time() - start_time)
        return [], best_keys, best_cost

    def PSO(self, tag, pool):
        metaheuristic_name = f"PSO {tag}"
        q_manager, params = self._setup_parameters(metaheuristic_name, self.env.PSO_parameters)
        Psize, c1, c2, w = params['PSize'], params['c1'], params['c2'], params['w']

        start_time = time.time()
        X = [self.random_keys() for _ in range(Psize)]
        V = [np.random.random(self.__MAX_KEYS) for _ in range(Psize)]
        Pbest = [(self.env.cost(self.env.decoder(x)), x) for x in X]
        Gbest_cost, Gbest_keys = min(Pbest, key=lambda x: x[0])

        pool.insert((Gbest_cost, list(Gbest_keys)), metaheuristic_name, tag)
        if self.stop_condition(Gbest_cost, metaheuristic_name, tag, pool=pool): return [], Gbest_keys, Gbest_cost
        
        while time.time() - start_time < self.max_time:
            if q_manager:
                new_params = q_manager.select_action(time.time() - self.start_time)
                new_Psize, c1, c2, w = new_params['PSize'], new_params['c1'], new_params['c2'], new_params['w']
                if new_Psize != Psize:
                    if new_Psize < Psize:
                         Pbest.sort(key=lambda x: x[0])
                         X, Pbest, V = [x for _, x in Pbest[:new_Psize]], Pbest[:new_Psize], V[:new_Psize]
                    else:
                         for _ in range(new_Psize - Psize):
                             nk = self.random_keys()
                             nc = self.env.cost(self.env.decoder(nk))
                             X.append(nk); Pbest.append((nc, nk)); V.append(np.random.random(self.__MAX_KEYS))
                             if nc < Gbest_cost: Gbest_cost, Gbest_keys = nc, nk
                    Psize = new_Psize

            improvement_flag, best_gen = 0, float('inf')
            for i in range(Psize):
                if self.stop_condition(Gbest_cost, metaheuristic_name, tag, pool=pool): return [], Gbest_keys, Gbest_cost
                r1, r2 = random.random(), random.random()
                V[i] = w * V[i] + c1 * r1 * (Pbest[i][1] - X[i]) + c2 * r2 * (Gbest_keys - X[i])
                old_keys = X[i]
                X[i] = X[i] + V[i]
                for j in range(self.__MAX_KEYS):
                    if not (0.0 <= X[i][j] < 1.0): X[i][j], V[i][j] = old_keys[j], 0.0

                cost_x = self.env.cost(self.env.decoder(X[i]))
                if cost_x < Pbest[i][0]: Pbest[i] = (cost_x, X[i])
                if cost_x < Gbest_cost:
                    Gbest_cost, Gbest_keys, improvement_flag = cost_x, X[i], 1
                    pool.insert((Gbest_cost, list(Gbest_keys)), metaheuristic_name, tag)
                if cost_x < best_gen: best_gen = cost_x

            if Psize > 0:
                imp_k = self.NelderMeadSearch(keys=Pbest[random.randint(0, Psize - 1)][1], pool=pool)
                imp_c = self.env.cost(self.env.decoder(imp_k))
                if imp_c < best_gen: best_gen = imp_c
                if imp_c < Gbest_cost:
                    Gbest_keys, Gbest_cost, improvement_flag = imp_k, imp_c, 1
                    pool.insert((Gbest_cost, list(Gbest_keys)), metaheuristic_name, tag)

            if q_manager:
                reward = 1.0 if improvement_flag else (Gbest_cost - best_gen) / Gbest_cost if Gbest_cost > 0 else 0
                q_manager.update_q_value(reward, time.time() - start_time)
        return [], Gbest_keys, Gbest_cost

    def BRKGA(self, tag, pool):
        metaheuristic_name = f"BRKGA {tag}"
        q_manager, params = self._setup_parameters(metaheuristic_name, self.env.BRKGA_parameters)
        pop_size, elite_pop, chance_elite = params['p'], params['pe'], params['rhoe']
        tam_elite = max(1, int(pop_size * elite_pop))

        population = [self.random_keys() for _ in range(pop_size)]
        best_keys_overall, best_fitness_overall = None, float('inf')
        
        start_time, generation, half_time_restart_done = time.time(), 0, False

        while time.time() - start_time < self.max_time:
            resize_pending = None
            if q_manager:
                new_params = q_manager.select_action(time.time() - start_time)
                elite_pop, chance_elite = new_params.get('pe', elite_pop), new_params.get('rhoe', chance_elite)
                tam_elite = max(1, int(pop_size * elite_pop)) if elite_pop > 0 else 0
                new_pop_size = new_params.get('p', pop_size)
                if new_pop_size != pop_size: resize_pending = new_pop_size

            if not half_time_restart_done and (time.time() - start_time) > (self.max_time / 2):
                population, half_time_restart_done = [self.random_keys() for _ in range(pop_size)], True
            generation += 1
            
            evaluated_population, best_gen, improvement_flag = [], float('inf'), 0
            for key in population:
                fitness = self.env.cost(self.env.decoder(key))
                evaluated_population.append((key, fitness))
                if fitness < best_gen: best_gen = fitness
                if fitness < best_fitness_overall:
                    best_fitness_overall, best_keys_overall, improvement_flag = fitness, key, 1
                    pool.insert((best_fitness_overall, list(best_keys_overall)), metaheuristic_name, tag)
                if self.stop_condition(best_fitness_overall, metaheuristic_name, tag): return [], best_keys_overall, fitness

            if resize_pending is not None:
                evaluated_population.sort(key=lambda x: x[1])
                population = [ind[0] for ind in evaluated_population[:resize_pending]] if resize_pending < pop_size else population + [self.random_keys() for _ in range(resize_pending - pop_size)]
                pop_size, resize_pending = resize_pending, None
                tam_elite = max(1, int(pop_size * elite_pop)) if elite_pop > 0 else 0

            evaluated_population.sort(key=lambda x: x[1])
            elite_keys = [item[0] for item in evaluated_population[:tam_elite]]
            new_population = elite_keys[:1] if elite_keys else []

            while len(new_population) < pop_size:
                p1 = random.choice(list(pool.pool))[1] if pool.pool and random.random() < 0.5 else random.choice(population)
                p2 = random.choice(elite_keys) if elite_keys else random.choice(population)
                child = np.zeros(self.__MAX_KEYS)
                for i in range(len(child)): child[i] = p2[i] if random.random() < chance_elite else p1[i]
                for idx in range(len(child)):
                    if random.random() < 0.05: child[idx] = random.random()
                new_population.append(child)
            population = new_population[:pop_size]

            if q_manager:
                reward = (1.0 + (1.0 / pop_size)) if improvement_flag else ((best_fitness_overall - best_gen) / best_fitness_overall if best_fitness_overall not in [0, float('inf')] else 0.0)
                q_manager.update_q_value(reward, time.time() - start_time)

        final_cost = self.env.cost(self.env.decoder(best_keys_overall))
        return [], best_keys_overall, best_fitness_overall

    def ILS(self, limit_time, tag, pool):
        metaheuristic_name = f"ILS {tag}"
        q_manager, params = self._setup_parameters(metaheuristic_name, self.env.ILS_parameters)
        beta_min, beta_max = params['betaMin'], params['betaMax']
        
        start_time, keys = time.time(), self.random_keys()
        best_keys = self.RVND(metaheuristic_name=metaheuristic_name, pool=pool, keys=keys)
        best_cost = self.env.cost(self.env.decoder(best_keys))
        
        pool.insert((best_cost, list(best_keys)), metaheuristic_name, tag)
        if self.stop_condition(best_cost, metaheuristic_name, tag, pool=pool): return [], best_keys, best_cost

        while time.time() - start_time < limit_time:
            if q_manager:
                new_params = q_manager.select_action(time.time() - start_time)
                beta_min, beta_max = new_params['betaMin'], new_params['betaMax']
            
            cost_before, improvement_flag = best_cost, 0
            s2 = self.RVND(metaheuristic_name=metaheuristic_name, pool=pool, keys=self.shaking(best_keys, beta_min, beta_max))
            cost = self.env.cost(self.env.decoder(s2))

            if cost < best_cost: improvement_flag = 1
            if cost <= best_cost:
                best_cost, best_keys = cost, s2
                pool.insert((best_cost, list(best_keys)), metaheuristic_name, tag)
                if self.stop_condition(best_cost, metaheuristic_name, tag, pool=pool): return [], best_keys, best_cost
            
            if q_manager:
                reward = 1.0 if improvement_flag else (cost_before - cost) / cost_before if cost_before > 0 else 0
                q_manager.update_q_value(reward, time.time() - start_time)
        return [], best_keys, best_cost

    def GA(self, tag, pool):
        metaheuristic_name = f"GA {tag}"
        q_manager, params = self._setup_parameters(metaheuristic_name, self.env.GA_parameters)
        pop_size, prob_cros, prob_mut = params['sizePop'], params['probCros'], params['probMut']

        population, best_keys_overall, best_fitness_overall = [], None, float('inf')
        for _ in range(pop_size):
            keys = self.random_keys()
            cost = self.env.cost(self.env.decoder(keys))
            population.append({'keys': keys, 'cost': cost})
            if cost < best_fitness_overall: best_fitness_overall, best_keys_overall = cost, keys

        pool.insert((best_fitness_overall, list(best_keys_overall)), metaheuristic_name, tag)
        if self.stop_condition(best_fitness_overall, metaheuristic_name, tag, pool=pool): return [], best_keys_overall, best_fitness_overall
        
        start_time = time.time()
        while time.time() - start_time < self.max_time:
            if q_manager:
                new_params = q_manager.select_action(time.time() - start_time)
                pop_size, prob_cros, prob_mut = new_params['sizePop'], new_params['probCros'], new_params['probMut']
                if len(population) != pop_size:
                     population.sort(key=lambda p: p['cost'])
                     population = population[:pop_size] if len(population) > pop_size else population + [{'keys': self.random_keys(), 'cost': 0} for _ in range(pop_size - len(population))]

            parents = [min(random.sample(population, 3), key=lambda p: p['cost']) for _ in range(pop_size)]
            new_population_data, best_gen, improvement_flag = [], float('inf'), 0

            for i in range(0, pop_size, 2):
                if i+1 >= len(parents): new_population_data.append(parents[i]); continue
                c1, c2 = copy.deepcopy(parents[i]['keys']), copy.deepcopy(parents[i+1]['keys'])
                if random.random() < prob_cros:
                    for j in range(self.__MAX_KEYS):
                        if random.random() < 0.5: c1[j], c2[j] = c2[j], c1[j]
                    for j in range(self.__MAX_KEYS):
                        if random.random() <= prob_mut: c1[j] = random.random()
                        if random.random() <= prob_mut: c2[j] = random.random()
                
                cost1, cost2 = self.env.cost(self.env.decoder(c1)), self.env.cost(self.env.decoder(c2))
                new_population_data.extend([{'keys': c1, 'cost': cost1}, {'keys': c2, 'cost': cost2}])
                if cost1 < best_gen: best_gen = cost1
                if cost2 < best_gen: best_gen = cost2

            if new_population_data:
                new_population_data.sort(key=lambda p: p['cost'])
                imp_k = self.RVND(keys=new_population_data[0]['keys'], pool=pool, metaheuristic_name=metaheuristic_name)
                imp_c = self.env.cost(self.env.decoder(imp_k))
                if imp_c < new_population_data[0]['cost']:
                    new_population_data[0] = {'keys': imp_k, 'cost': imp_c}
                    if imp_c < best_gen: best_gen = imp_c
            
            population.sort(key=lambda p: p['cost'])
            if new_population_data and population[0]['cost'] < new_population_data[0]['cost']: new_population_data[-1] = population[0]
            population = new_population_data
            
            current_best = min(population, key=lambda p: p['cost'])
            if current_best['cost'] < best_fitness_overall:
                best_fitness_overall, best_keys_overall, improvement_flag = current_best['cost'], current_best['keys'], 1
                pool.insert((best_fitness_overall, list(best_keys_overall)), metaheuristic_name, tag)
                if self.stop_condition(best_fitness_overall, metaheuristic_name, tag, pool=pool): return [], best_keys_overall, best_fitness_overall

            if q_manager:
                reward = 1.0 if improvement_flag else (best_fitness_overall - best_gen) / best_fitness_overall if best_fitness_overall > 0 else 0
                q_manager.update_q_value(reward, time.time() - start_time)
        return [], best_keys_overall, best_fitness_overall

    def stop_condition(self, best_cost, metaheuristic_name, tag, pool=None):
        if time.time() - self.start_time > self.max_time:
            if self.print_best and tag != -1: print(f"[{metaheuristic_name}] FINISHED")
            return True
        if pool and self.env.dict_best and self.env.instance_name in self.env.dict_best:
             if pool.best_pair[0] <= self.env.dict_best[self.env.instance_name]: return True
        if self.env.dict_best and self.env.instance_name in self.env.dict_best:
            if best_cost <= self.env.dict_best[self.env.instance_name]: return True
        return False

    def solve(self, time_total, brkga=0, ms=0, sa=0, vns=0, ils=0, lns=0, pso=0, ga=0, restart=1, runs=1):
        solutions, times, costs = [], [], []
        for i in range(runs):
            print(f'Instance: {self.env.instance_name}, Run: {i+1}/{runs}')
            limit_time = time_total * restart
            restarts = int(1 / restart)
            self.max_time = limit_time

            manager = Manager()
            shared = manager.Namespace()
            shared.best_pair = manager.list([float('inf'), None, None])
            shared.best_pool = manager.list()
            shared.pool = SolutionPool(20, shared.best_pool, shared.best_pair, lock=manager.Lock(), print_flag=self.print_best, Best=self.env.dict_best.get(self.env.instance_name), env=self.env)
            
            for _ in range(20):
                keys = self.random_keys()
                cost = self.env.cost(self.env.decoder(keys))
                shared.pool.insert((cost, list(keys)), 'pool', -1)

            processes = []
            for k in range(restarts):
                tag = 0
                self.start_time = time.time()
                if self.stop_condition(shared.pool.best_pair[0], 'RKO', tag, pool=shared.pool): break

                shared.pool.pool = manager.list()
                tasks = [
                    (brkga, _brkga_worker), (ms, _MS_worker), (sa, _SA_worker),
                    (vns, _VNS_worker), (ils, _ILS_worker), (lns, _LNS_worker),
                    (pso, _PSO_worker), (ga, _GA_worker)
                ]

                for count, worker_func in tasks:
                    for _ in range(count):
                        args = (self.env, self.max_time, shared.pool, tag, self.print_best, self.save_directory, self.log_queue)
                        p = Process(target=worker_func, args=args)
                        p.daemon = True
                        tag += 1
                        processes.append(p)
                        p.start()

                for p in processes: p.join(timeout=self.max_time)
                for p in processes: 
                    if p.is_alive(): p.terminate()

            cost, solution, time_elapsed = shared.pool.best_pair[0], shared.pool.best_pair[1], shared.pool.best_pair[2]
            solutions.append(solution); costs.append(round(cost, 2)); times.append(round(-1 * time_elapsed, 2))
            
        if self.save_directory:
            directory = os.path.dirname(self.save_directory)
            if directory: os.makedirs(directory, exist_ok=True)
            with open(self.save_directory, 'a', newline='') as f:
                f.write(f'{time_total}, {self.env.instance_name}, {round(sum(costs)/len(costs),2)}, {costs}, {round(sum(times)/len(times),2)}, {times}\n')

        return cost, solution, time_elapsed

# WORKERS 
def _setup_worker_env(env, log_queue):
    """
    Configura o ambiente do processo filho:
    1. Redireciona prints para a Queue.
    2. Reconecta o callback do env para usar a mesma Queue (Isso conserta o Gantt).
    """
    if log_queue is not None:
        # 1. Arruma o print (Texto)
        sys.stdout = QueueWriter(log_queue)
        
        # 2. Arruma o Callback (Gráfico)
        # Criamos uma função local que sabe enviar para a fila deste processo
        def callback_processo_filho(dados):
            try:
                log_queue.put(dados)
            except Exception:
                pass # Evita travar o cálculo se a fila encher
        
        # Substitui o callback quebrado pelo novo
        env.ui_callback = callback_processo_filho

def _injetar_parametros_gui(env, agente_nome):
    if not hasattr(env, 'agent_config'): return
    config_gui = env.agent_config.get(agente_nome, {})
    if not config_gui: return

    nome_dict_alvo = f"{agente_nome}_parameters"
    if not hasattr(env, nome_dict_alvo): return
    dict_alvo = getattr(env, nome_dict_alvo)
    
    mapa_traducao = {
        'SA': {'Initial Temperature': 'T0', 'alphaSA': 'alphaSA', 'Iterations': 'SAmax', 'betaMin': 'betaMin', 'betaMax': 'betaMax'},
        'GA': {'Population': 'sizePop', 'CrosProb': 'probCros', 'MutProb': 'probMut'},
        'BRKGA': {'Population': 'p', 'Elite set %': 'pe', 'Inheritance Prob': 'rhoe'},
        'PSO': {'PSize': 'PSize', 'c1': 'c1', 'c2': 'c2', 'w': 'w'},
        'VNS': {'kMax': 'kMax', 'betaMin': 'betaMin'},
        'ILS': {'betaMin': 'betaMin', 'betaMax': 'betaMax'},
        'LNS': {'betaMin': 'betaMin', 'betaMax': 'betaMax', 'T0': 'TO', 'alphaLNS': 'alphaLNS'}
    }
    mapa_especifico = mapa_traducao.get(agente_nome, {})
    
    for chave_gui, valor in config_gui.items():
        chave_rko = mapa_especifico.get(chave_gui)
        if chave_rko and chave_rko in dict_alvo:
            try:
                val_float = float(valor)
                val_final = int(val_float) if val_float.is_integer() else val_float
                dict_alvo[chave_rko] = [val_final]
            except: pass

def _brkga_worker(env, limit_time, pool, tag, print_best, save_directory, log_queue):
    _setup_worker_env(env, log_queue) # <--- AQUI ESTÁ A CORREÇÃO
    _injetar_parametros_gui(env, 'BRKGA')
    runner = RKO(env, print_best, save_directory)
    runner.max_time = limit_time
    runner.BRKGA(tag, pool)
    
def _MS_worker(env, limit_time, pool, tag, print_best, save_directory, log_queue):
    _setup_worker_env(env, log_queue) # <--- AQUI ESTÁ A CORREÇÃO
    runner = RKO(env, print_best, save_directory)
    runner.max_time = limit_time
    runner.MultiStart(tag, pool)
    
def _VNS_worker(env, limit_time, pool, tag, print_best, save_directory, log_queue):
    _setup_worker_env(env, log_queue) # <--- AQUI ESTÁ A CORREÇÃO
    _injetar_parametros_gui(env, 'VNS')
    runner = RKO(env, print_best, save_directory)
    runner.max_time = limit_time 
    runner.VNS(limit_time, tag, pool)
    
def _ILS_worker(env, limit_time, pool, tag, print_best, save_directory, log_queue):
    _setup_worker_env(env, log_queue) # <--- AQUI ESTÁ A CORREÇÃO
    _injetar_parametros_gui(env, 'ILS')
    runner = RKO(env, print_best, save_directory)
    runner.max_time = limit_time
    runner.ILS(limit_time, tag, pool)
    
def _SA_worker(env, limit_time, pool, tag, print_best, save_directory, log_queue):
    _setup_worker_env(env, log_queue) # <--- AQUI ESTÁ A CORREÇÃO
    _injetar_parametros_gui(env, 'SA')
    runner = RKO(env, print_best, save_directory)
    runner.max_time = limit_time
    runner.SimulatedAnnealing(tag=tag, pool=pool)
    
def _LNS_worker(env, limit_time, pool, tag, print_best, save_directory, log_queue):
    _setup_worker_env(env, log_queue) # <--- AQUI ESTÁ A CORREÇÃO
    _injetar_parametros_gui(env, 'LNS')
    runner = RKO(env, print_best, save_directory)
    runner.max_time = limit_time
    runner.LNS(limit_time=limit_time, tag=tag, pool=pool)
    
def _PSO_worker(env, limit_time, pool, tag, print_best, save_directory, log_queue):
    _setup_worker_env(env, log_queue) # <--- AQUI ESTÁ A CORREÇÃO
    _injetar_parametros_gui(env, 'PSO')
    runner = RKO(env, print_best, save_directory)
    runner.max_time = limit_time
    runner.PSO(tag=tag, pool=pool)
    
def _GA_worker(env, limit_time, pool, tag, print_best, save_directory, log_queue):
    _setup_worker_env(env, log_queue) # <--- AQUI ESTÁ A CORREÇÃO
    _injetar_parametros_gui(env, 'GA')
    runner = RKO(env, print_best, save_directory)
    runner.max_time = limit_time
    runner.GA(tag=tag, pool=pool)

# Q-LEARNING MANAGER
class QLearningManager:
    def __init__(self, parameters_config, max_time, metaheuristic_name, save_report=True, epsilon_min=0.1, df=0.8):
        self.param_keys = list(parameters_config.keys())
        self.max_time = max_time if max_time > 0 else 1.0
        self.epsilon_min = epsilon_min
        self.df = df
        self.metaheuristic_name = metaheuristic_name
        self.save_report = save_report
        self._create_states_and_actions(parameters_config)
        self.current_state_idx = random.randint(0, self.num_states - 1)
        self.last_action_taken = None
        self.epsilon_max = 1.0
        self.restart_epsilon_period = self.max_time * 0.1
        self.next_restart_time = self.restart_epsilon_period

    def _create_states_and_actions(self, parameters_config):
        param_values = list(parameters_config.values())
        all_combinations = list(itertools.product(*param_values))
        self.num_states = len(all_combinations)
        self.states = []
        for i, combo in enumerate(all_combinations):
            self.states.append({'id': i, 'params': dict(zip(self.param_keys, combo))})
        self.q_table = {}
        for i in range(self.num_states):
            self.q_table[i] = {}
            for j in range(self.num_states):
                hamming_dist = sum(1 for k in self.param_keys if self.states[i]['params'][k] != self.states[j]['params'][k])
                if hamming_dist <= 1: self.q_table[i][j] = random.uniform(0.01, 0.05)
        for i in range(self.num_states): self._update_max_q(i)

    def _update_max_q(self, state_idx):
        q_values_for_state = self.q_table.get(state_idx, {})
        self.states[state_idx]['max_q'] = max(q_values_for_state.values()) if q_values_for_state else 0.0

    def get_current_parameters(self):
        return self.states[self.current_state_idx]['params']

    def select_action(self, current_time):
        if self.restart_epsilon_period > 0 and current_time > self.next_restart_time:
            self.next_restart_time += self.restart_epsilon_period
            self.epsilon_max = max(self.epsilon_min, self.epsilon_max - 0.1)
        time_in_period = current_time % self.restart_epsilon_period if self.restart_epsilon_period > 0 else 0
        epsilon = self.epsilon_min + 0.5 * (self.epsilon_max - self.epsilon_min) * (1 + math.cos(time_in_period / self.restart_epsilon_period * math.pi))
        possible_actions = list(self.q_table[self.current_state_idx].keys())
        if not possible_actions: return self.get_current_parameters()
        action = max(self.q_table[self.current_state_idx], key=self.q_table[self.current_state_idx].get) if random.random() > epsilon else random.choice(possible_actions)
        self.last_action_taken = action
        return self.states[action]['params']

    def update_q_value(self, reward, current_time):
        lf = max(0.1, 1.0 - (0.9 * current_time / self.max_time))
        state_idx = self.current_state_idx
        action_idx = self.last_action_taken
        if action_idx is None: return
        next_state_idx = action_idx
        old_q_value = self.q_table[state_idx][action_idx]
        future_best_q = self.states[next_state_idx]['max_q']
        new_q_value = old_q_value + lf * (reward + self.df * future_best_q - old_q_value)
        self.q_table[state_idx][action_idx] = new_q_value
        self._update_max_q(state_idx)
        self.current_state_idx = next_state_idx
    
    def save_final_policy_report(self, instance_name, directory='.'):
        if not self.save_report: return
        if not os.path.exists(directory): os.makedirs(directory)
        filepath = os.path.join(directory, f"policy_report_{self.metaheuristic_name}_{instance_name}.csv")
        report_data = []
        for state_idx, actions in self.q_table.items():
            state_params = self.states[state_idx]['params']
            best_action_for_state = max(actions, key=actions.get) if actions else None
            best_params_for_state = self.states[best_action_for_state]['params'] if best_action_for_state is not None else {}
            entry = {f'state_{k}': v for k, v in state_params.items()}
            entry['state_id'] = state_idx
            entry['best_next_state_id'] = best_action_for_state
            entry.update({f'best_param_{k}': v for k, v in best_params_for_state.items()})
            entry.update({f'Q(s,{a})': round(q, 4) for a, q in actions.items()})
            report_data.append(entry)
        try:
            df = pd.DataFrame(report_data).sort_values(by='state_id').set_index('state_id')
            df.to_csv(filepath)
            print(f"Q-Learning convergence report saved to: {filepath}")
        except Exception as e: print(f"Error saving convergence report to {filepath}: {e}")