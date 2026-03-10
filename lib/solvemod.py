import random
from math import gcd

def egcd(a, b):
    if b == 0:
        return (abs(a), 1 if a >= 0 else -1, 0)
    g, x1, y1 = egcd(b, a % b)
    return (g, y1, x1 - (a // b) * y1)

def modinv(a, n):
    g, x, _ = egcd(a, n)
    if g != 1:
        raise ValueError("No inverse")
    return x % n

def row_swap(A, b, i, j):
    A[i], A[j] = A[j], A[i]
    b[i], b[j] = b[j], b[i]

def row_combine(A, b, i, j, col):
    a = A[i][col]
    c = A[j][col]
    g, s, t = egcd(a, c)

    row_i = A[i][:]
    row_j = A[j][:]

    A[i] = [s*row_i[k] + t*row_j[k] for k in range(len(A[0]))]
    A[j] = [(-c//g)*row_i[k] + (a//g)*row_j[k] for k in range(len(A[0]))]

    bi, bj = b[i], b[j]
    b[i] = s*bi + t*bj
    b[j] = (-c//g)*bi + (a//g)*bj

def echelon_gcd(A, b):
    m, n = len(A), len(A[0])
    pivot_cols = []
    pivot_rows = []

    r = 0
    for col in range(n):
        pivot = None
        best = None
        for i in range(r, m):
            if A[i][col] != 0:
                val = abs(A[i][col])
                if best is None or val < best:
                    best = val
                    pivot = i
        if pivot is None:
            continue

        if pivot != r:
            row_swap(A, b, r, pivot)

        # eliminer ?
        for i in range(r+1, m):
            if A[i][col] != 0:
                row_combine(A, b, r, i, col)

        pivot_cols.append(col)
        pivot_rows.append(r)
        r += 1
        if r == m:
            break

    return A, b, pivot_cols, pivot_rows

def solve_single_congruence(a, rhs, n):
    a_mod = a % n
    rhs_mod = rhs % n

    if a_mod == 0:
        if rhs_mod == 0:
            return list(range(n))
        else:
            return []

    g = gcd(a_mod, n)
    if rhs_mod % g != 0:
        return []

    a1 = a_mod // g
    n1 = n // g
    rhs1 = rhs_mod // g

    inv = modinv(a1, n1)
    x0 = (inv * rhs1) % n1

    return [(x0 + t*n1) % n for t in range(g)]

def solve_mod_system(A, b, n, max_solutions=None, randomize=False, seed=None):
    if seed is not None:
        random.seed(seed)

    A = [row[:] for row in A]
    b = b[:]

    A, b, pivot_cols, pivot_rows = echelon_gcd(A, b)

    m, vars_ = len(A), len(A[0])
    pivot_map = {c: r for c, r in zip(pivot_cols, pivot_rows)}

    solutions = []
    assign = [None] * vars_

    def iter_values(lst):
        if randomize:
            lst = lst[:]
            random.shuffle(lst)
        return lst

    def iter_range(n):
        if not randomize:
            return range(n)
        vals = list(range(n))
        random.shuffle(vals)
        return vals

    def dfs(j):
        if max_solutions is not None and len(solutions) >= max_solutions:
            return
        if j < 0:
            solutions.append(assign[:])
            return

        if j in pivot_map:
            row = pivot_map[j]
            rhs = b[row]
            for k in range(j+1, vars_):
                rhs -= A[row][k] * assign[k]
            sols = solve_single_congruence(A[row][j], rhs, n)
            for x in iter_values(sols):
                assign[j] = x
                dfs(j-1)
                if max_solutions is not None and len(solutions) >= max_solutions:
                    break
            assign[j] = None
        else:
            for x in iter_range(n):
                assign[j] = x
                dfs(j-1)
                if max_solutions is not None and len(solutions) >= max_solutions:
                    break
            assign[j] = None

    dfs(vars_ - 1)
    return solutions

if __name__ == "__main__":
    A = [
        [0, 0, 1],
        [1, 1, 1],
        [1, 1, 1],
        [0, 1, 0]
    ]
    b = [-3, -3, -3, -3]
    mod = 1 << 8

    sols = solve_mod_system(A, b, mod, max_solutions=20, randomize=True, seed=42)
    for s in sols:
        print(s)
