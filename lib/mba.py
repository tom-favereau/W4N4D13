from solvemod import solve_mod_system
import random
import sys


def truth_table_vars(nb_vars):
    size = 1 << nb_vars
    vars_vecs = []
    for i in range(nb_vars):
        period = 1 << (nb_vars - i)
        half = period >> 1
        vec = []
        val = 0
        count = 0
        for _ in range(size):
            vec.append(val)
            count += 1
            if count == half:
                val ^= 1
                count = 0
        vars_vecs.append(vec)
    return vars_vecs


def bitwise_not_vec(v, n):
    return [((~x) & (n - 1)) for x in v]


def bitwise_op_vec(a, b, op):
    if op == '^':
        return [x ^ y for x, y in zip(a, b)]
    if op == '|':
        return [x | y for x, y in zip(a, b)]
    if op == '&':
        return [x & y for x, y in zip(a, b)]
    raise ValueError(f"Unsupported op: {op}")


def build_matrix(nb_vars, n=2**32):
    vars_vecs = truth_table_vars(nb_vars)
    cols = []
    names = []

    ops = ['^', '|', '&']

    for i in range(nb_vars):
        for j in range(i + 1, nb_vars):
            for op in ops:
                v = bitwise_op_vec(vars_vecs[i], vars_vecs[j], op)
                cols.append(v)
                names.append(f"a{i} {op} a{j}")

                cols.append(bitwise_not_vec(v, n))
                names.append(f"~(a{i} {op} a{j})")

    for i in range(nb_vars):
        for op in ops:
            v = bitwise_op_vec(vars_vecs[i], vars_vecs[i], op)
            cols.append(v)
            names.append(f"a{i} {op} a{i}")

            cols.append(bitwise_not_vec(v, n))
            names.append(f"~(a{i} {op} a{i})")

    if not cols:
        A = []
    else:
        size = len(cols[0])
        A = [[col[r] for col in cols] for r in range(size)]

    return A, names


def select_most_voluminous(solutions, n):
    def score(sol):
        return sum(1 for x in sol if (x % n) != 0)
    return max(solutions, key=score)


def obfuscate_constant(y, nb_vars, n=2**32, max_sol=500):
    A, names = build_matrix(nb_vars, n)
    size = 1 << nb_vars
    b = [y for _ in range(size)]

    solutions = solve_mod_system(A, b, n, max_solutions=max_sol)
    if not solutions:
        return None, names, A, b

    best = select_most_voluminous(solutions, n)
    return best, names, A, b


def v2(i):
    return (i & -i).bit_length() - 1


def min_d_for_power_of_two(w):
    v2fact = 0
    d = 1
    while v2fact < w:
        d += 1
        v2fact += v2(d)
    return d


def poly_trim(p):
    q = p[:]
    while q and q[-1] == 0:
        q.pop()
    return q if q else [0]


def poly_add_int(a, b):
    m = max(len(a), len(b))
    res = [0] * m
    for i in range(m):
        av = a[i] if i < len(a) else 0
        bv = b[i] if i < len(b) else 0
        res[i] = av + bv
    return poly_trim(res)


def poly_sub_int(a, b):
    m = max(len(a), len(b))
    res = [0] * m
    for i in range(m):
        av = a[i] if i < len(a) else 0
        bv = b[i] if i < len(b) else 0
        res[i] = av - bv
    return poly_trim(res)


def poly_mul_int(a, b):
    res = [0] * (len(a) + len(b) - 1)
    for i, av in enumerate(a):
        if av == 0:
            continue
        for j, bv in enumerate(b):
            res[i + j] += av * bv
    return poly_trim(res)


def poly_scale_int(a, k):
    if k == 0:
        return [0]
    return [k * x for x in a]


def poly_shift_int(a, s):
    if s <= 0:
        return a[:]
    return [0] * s + a


def falling_factorial_poly(i):
    p = [1]
    for j in range(i):
        p = poly_mul_int(p, [-j, 1])
    return p


def build_null_generators(n):
    w = n.bit_length() - 1
    d = min_d_for_power_of_two(w)

    P_list = []
    c_list = []

    v2fact = 0
    for i in range(0, d + 1):
        if i >= 2:
            v2fact += v2(i)
        g = 1 << min(w, v2fact)
        c = n // g
        ff = falling_factorial_poly(i)
        P_i = poly_scale_int(ff, c)
        P_list.append(P_i)
        c_list.append(c)

    return d, P_list, c_list


def reduce_poly(p, n, d, P_list, c_list):
    p = [c % n for c in p]
    p = poly_trim(p)

    Pd = P_list[d]
    while len(p) - 1 >= d:
        k = len(p) - 1
        ak = p[k]
        if ak != 0:
            sub = poly_shift_int(poly_scale_int(Pd, ak), k - d)
            p = poly_sub_int(p, sub)
            p = poly_trim([c % n for c in p])
        else:
            p.pop()

    for i in range(d - 1, -1, -1):
        ai = p[i] if i < len(p) else 0
        ci = c_list[i]

        if ci == 0:
            continue

        ri = ai % ci
        qi = (ai - ri) // ci

        if qi != 0:
            p = poly_sub_int(p, poly_scale_int(P_list[i], qi))

        if i >= len(p):
            if ri != 0:
                p = p + [0] * (i - len(p) + 1)
                p[i] = ri
        else:
            p[i] = ri

        p = poly_trim(p)

    p = [c % n for c in p]
    return poly_trim(p)


def poly_add_mod(a, b, n, d, P_list, c_list):
    return reduce_poly(poly_add_int(a, b), n, d, P_list, c_list)


def poly_mul_mod(a, b, n, d, P_list, c_list):
    return reduce_poly(poly_mul_int(a, b), n, d, P_list, c_list)


def poly_compose(f, g, n, d, P_list, c_list):
    res = [0]
    for coeff in reversed(f):
        res = poly_mul_mod(res, g, n, d, P_list, c_list)
        res = poly_add_mod(res, [coeff], n, d, P_list, c_list)
    return res


def is_identity_poly(p, n, d, P_list, c_list):
    p = reduce_poly(p, n, d, P_list, c_list)
    if len(p) < 2:
        return False
    if p[0] % n != 0:
        return False
    if p[1] % n != 1:
        return False
    return all((c % n) == 0 for c in p[2:])


def invert_poly(f, w, n, d, P_list, c_list):
    inv = f[:]
    for _ in range(0, w):
        g = poly_compose(inv, f, n, d, P_list, c_list)
        if is_identity_poly(g, n, d, P_list, c_list):
            return inv
        inv = poly_compose(inv, g, n, d, P_list, c_list)
    return inv


def random_perm_poly(degree, n, rng=None):
    if degree < 1:
        raise ValueError("degree must be >= 1")
    if rng is None:
        rng = random.Random()

    coeffs = [0] * (degree + 1)

    coeffs[0] = rng.randrange(0, n)
    coeffs[1] = (rng.randrange(0, n // 2) * 2 + 1) % n

    for k in range(2, degree + 1):
        coeffs[k] = rng.randrange(0, n)

    even_sum = sum(coeffs[k] for k in range(2, degree + 1, 2)) & 1
    if even_sum == 1 and degree >= 2:
        coeffs[2] = (coeffs[2] + 1) % n

    odd_sum = sum(coeffs[k] for k in range(3, degree + 1, 2)) & 1
    if odd_sum == 1 and degree >= 3:
        coeffs[3] = (coeffs[3] + 1) % n

    return coeffs


def pretty_printer_c_expr(solution, names, n=2**32):
    if solution is None:
        return "(0u)"

    mask = f"{n-1}u"
    terms = []
    for coeff, name in zip(solution, names):
        c = coeff % n
        if c == 0:
            continue

        if name.startswith("~(") and name.endswith(")"):
            inner = name[2:-1]
            term = f"(~({inner}))"
        elif name.startswith("~"):
            var = name[1:].strip()
            term = f"(~{var})"
        elif " ^ " in name or " | " in name or " & " in name:
            term = f"({name})"
        else:
            term = f"({name})"

        terms.append(f"({c}u * {term})")

    if not terms:
        expr = "0u"
    else:
        expr = " + ".join(terms)

    return f"(({expr}) & {mask})"


def poly_eval_expr_c(x_expr, coeffs, n):
    mask = f"{n-1}u"
    expr = f"({coeffs[-1]}u)"
    for c in reversed(coeffs[:-1]):
        expr = f"((({expr}) * ({x_expr}) + {c}u) & {mask})"
    return expr


def pretty_printer_with_perm_inline_c(solution, names, perm_poly, inv_poly, n=2**32):
    comb = pretty_printer_c_expr(solution, names, n)
    pinv_inline = poly_eval_expr_c(comb, inv_poly, n)
    p_inline = poly_eval_expr_c(pinv_inline, perm_poly, n)

    return p_inline


if __name__ == "__main__":
    y = int(sys.argv[1])
    sol, names, A, b = obfuscate_constant(y, nb_vars=2, max_sol=19000)

    n = 2**32
    d, P_list, c_list = build_null_generators(n)

    degree = 2
    P = random_perm_poly(degree, n)
    P = reduce_poly(P, n, d, P_list, c_list)

    Pinv = invert_poly(P, w=32, n=n, d=d, P_list=P_list, c_list=c_list)

    expr_c = pretty_printer_with_perm_inline_c(sol, names, P, Pinv, n)
    print(expr_c)
