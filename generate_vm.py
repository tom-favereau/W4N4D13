#!/usr/bin/env python3
import sys
import re

EXTERNS = [
    {
        "name": "ext_puts",
        "code": r"""
static inline int32_t ext_puts(VM *vm, int32_t *args, int32_t argc) {
  if (argc != 1) return 0;
  const char *s = vm_get_str(vm, args[0]);
  return (int32_t)puts(s);
}
""",
    },
    {
        "name": "ext_printf1",
        "code": r"""
static inline int32_t ext_printf1(VM *vm, int32_t *args, int32_t argc) {
  if (argc != 2) return 0;
  const char *fmt = vm_get_str(vm, args[0]);
  return (int32_t)printf(fmt, args[1]);
}
""",
    },
    {
        "name": "ext_printf2",
        "code": r"""
static inline int32_t ext_printf2(VM *vm, int32_t *args, int32_t argc) {
  if (argc != 3) return 0;
  const char *fmt = vm_get_str(vm, args[0]);
  return (int32_t)printf(fmt, args[1], args[2]);
}
""",
    },
    {
        "name": "ext_printf3",
        "code": r"""
static inline int32_t ext_printf3(VM *vm, int32_t *args, int32_t argc) {
  if (argc != 4) return 0;
  const char *fmt = vm_get_str(vm, args[0]);
  return (int32_t)printf(fmt, args[1], args[2], args[3]);
}
""",
    },
    {
        "name": "ext_printi",
        "code": r"""
static inline int32_t ext_printi(VM *vm, int32_t *args, int32_t argc) {
  if (argc != 1) return 0;
  return (int32_t)printf("%d", args[0]);
}
""",
    },
    {
        "name": "ext_rand",
        "code": r"""
static inline int32_t ext_rand(VM *vm, int32_t *args, int32_t argc) {
  if (argc != 0) return 0;
  return (int32_t)rand();
}
""",
    },
    {   "name": "ext_system",
        "code": r"""
static inline int32_t ext_system(VM *vm, int32_t *args, int32_t argc) {
    if (argc != 1) return 0;
    const char *cmd = (const char *)args[0];
    return (int32_t)system(cmd);                
}
        """
    },
    {   "name": "ext_getKeya",
        "code": r"""
static inline int32_t ext_getKeya(VM *vm, int32_t *args, int32_t argc) {
        if (argc != 0) return 0;
        return (int32_t)conv_a(globalInput);
}
        """
    },
    {   "name": "ext_getKeyb",
        "code": r"""
static inline int32_t ext_getKeyb(VM *vm, int32_t *args, int32_t argc) {
        if (argc != 0) return 0;
        return (int32_t)conv_b(globalInput);
}
        """
    },
    {   "name": "ext_getKeyc",
        "code": r"""
static inline int32_t ext_getKeyc(VM *vm, int32_t *args, int32_t argc) {
        if (argc != 0) return 0;
        return (int32_t)conv_c(globalInput);
}
        """
    },
    {   "name": "ext_getKeyd",
        "code": r"""
static inline int32_t ext_getKeyd(VM *vm, int32_t *args, int32_t argc) {
        if (argc != 0) return 0;
        return (int32_t)conv_d(globalInput);
}
        """
    },
    {   "name": "ext_getLen",
        "code": r"""
static inline int32_t ext_getLen(VM *vm, int32_t *args, int32_t argc) {
    if (argc != 0) return 0;
    return (int32_t)globalInputLen;                
}
        """
    }
]

OP_NAMES = [
    "OP_NOP",
    "OP_PUSH",
    "OP_LOAD",
    "OP_STORE",
    "OP_POP",
    "OP_ADD", "OP_SUB", "OP_MUL", "OP_DIV", "OP_MOD",
    "OP_LT", "OP_GT", "OP_LE", "OP_GE", "OP_EQ", "OP_NE",
    "OP_AND", "OP_OR",
    "OP_BAND", "OP_BOR", "OP_BXOR", "OP_SHL", "OP_SHR",
    "OP_NEG", "OP_NOT", "OP_BNOT",
    "OP_JMP", "OP_JZ", "OP_JNZ",
    "OP_CALL",
    "OP_CALLX",
    "OP_RET",
    "OP_RET0",
]
OP_INDEX = {name[3:]: i for i, name in enumerate(OP_NAMES)}  # "PUSH" -> index
OP_COUNT = 33

# encoding params
P1 = 5
P2 = 7
A_PC = 11
B_PC = 3

# -----------------------
# helpers
# -----------------------
def die(msg, line_no=None):
    if line_no is not None:
        sys.stderr.write(f"error line {line_no}: {msg}\n")
    else:
        sys.stderr.write(f"error: {msg}\n")
    sys.exit(1)

def modn(x):
    r = x % OP_COUNT
    return r + OP_COUNT if r < 0 else r

def egcd(a, b):
    if b == 0:
        return (a, 1, 0)
    g, x1, y1 = egcd(b, a % b)
    return (g, y1, x1 - (a // b) * y1)

def modinv(a, m):
    g, x, y = egcd(a, m)
    if g != 1 and g != -1:
        return None
    inv = x % m
    return inv + m if inv < 0 else inv

_INV_P1 = modinv(P1, OP_COUNT)

def decode_opcode(op_enc, pc):
    fpc = modn(A_PC * pc + B_PC)
    t = modn(op_enc - P2 - fpc)
    op = modn(_INV_P1 * t)
    return op

def parse_int32(s, line_no):
    s = s.strip()
    v = int(s, 0)
    v = (v + 2**31) % 2**32 - 2**31
    return v

def parse_quoted(s, line_no):
    i = 1
    out = []
    while i < len(s):
        c = s[i]
        if c == '"':
            return "".join(out), s[i+1:]
        if c == "\\":
            i += 1
            if i >= len(s):
                break
            esc = s[i]
            if esc == "n": out.append("\n")
            elif esc == "t": out.append("\t")
            elif esc == "r": out.append("\r")
            elif esc == "\\": out.append("\\")
            elif esc == '"': out.append('"')
            else: out.append(esc)
            i += 1
        else:
            out.append(c)
            i += 1

def c_escape(s):
    out = []
    for ch in s:
        if ch == "\\":
            out.append("\\\\")
        elif ch == '"':
            out.append('\\"')
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\t":
            out.append("\\t")
        elif ch == "\r":
            out.append("\\r")
        else:
            out.append(ch)
    return "".join(out)

class Instr:
    __slots__ = ("op_enc", "op_name", "a", "b", "label")
    def __init__(self, op_enc, op_name, a=0, b=0, label=None):
        self.op_enc = op_enc
        self.op_name = op_name
        self.a = a
        self.b = b
        self.label = label

def parse_file(text):
    code = []
    labels = {}
    strs = []
    funcs = []
    locals_len = 0
    entry_label = None

    lines = text.splitlines()
    for line_no, line in enumerate(lines, 1):
        s = line.lstrip()
        s = s.rstrip()
        if s == "" or s.startswith("#") or s.startswith(";"):
            continue
        cut = None
        for i, ch in enumerate(s):
            if ch == ";" or ch == "#":
                cut = i
                break
        if cut is not None:
            s = s[:cut].rstrip()
        if s == "":
            continue

        if s.endswith(":") and ":" in s and s.count(":") == 1:
            name = s[:-1].rstrip()
            labels[name] = len(code)
            continue

        if s.startswith(".locals") and len(s) > 7 and s[7].isspace():
            locals_len = parse_int32(s[7:], line_no)
            continue
        if s.startswith(".entry") and len(s) > 6 and s[6].isspace():
            entry_label = s[6:].strip()
            continue
        if s.startswith(".str") and len(s) > 4 and s[4].isspace():
            rest = s[4:].lstrip()
            parts = rest.split(None, 1)
            id_tok = parts[0]
            txt_part = parts[1].lstrip()
            sid = parse_int32(id_tok, line_no)
            txt, _ = parse_quoted(txt_part, line_no)
            strs.append((sid, txt))
            continue
        if s.startswith(".func") and len(s) > 5 and s[5].isspace():
            rest = s[5:].lstrip()
            parts = rest.split()
            name, label, locs = parts
            locs_i = parse_int32(locs, line_no)
            funcs.append((name, label, locs_i))
            continue

        parts = s.split(None, 1)
        op_tok = parts[0]
        op_enc = OP_INDEX[op_tok]
        op_name = "OP_" + op_tok
        pc = len(code)
        op_dec = decode_opcode(op_enc, pc)

        rest = parts[1].lstrip() if len(parts) > 1 else ""

        ins = Instr(op_enc, op_name)

        if op_dec in (OP_INDEX["PUSH"], OP_INDEX["LOAD"], OP_INDEX["STORE"]):
            ins.a = parse_int32(rest, line_no)
        elif op_dec in (OP_INDEX["JMP"], OP_INDEX["JZ"], OP_INDEX["JNZ"]):
            ins.label = rest
        elif op_dec == OP_INDEX["CALLX"]:
            sub = rest.split(None, 1)
            ins.a = parse_int32(sub[0], line_no)
            ins.b = parse_int32(sub[1], line_no)
        elif op_dec == OP_INDEX["CALL"]:
            sub = rest.split(None, 1)
            ins.label = sub[0]
            ins.b = parse_int32(sub[1], line_no)

        code.append(ins)

    # resolve labels in code
    for ins in code:
        if ins.label is not None:
            ins.a = labels[ins.label]
            ins.label = None

    # resolve funcs
    funcs_res = []
    for name, label, locs in funcs:
        ip = labels[label]
        funcs_res.append((name, ip, locs))

    # entry
    entry_ip = 0
    if entry_label is not None:
        if entry_label not in labels:
            die("unknown entry label: " + entry_label)
        entry_ip = labels[entry_label]

    return {
        "code": code,
        "strs": strs,
        "funcs": funcs_res,
        "locals_len": locals_len,
        "entry_ip": entry_ip,
    }

def generate_c(ast):
    code = ast["code"]
    strs = ast["strs"]
    funcs = ast["funcs"]
    locals_len = ast["locals_len"]
    entry_ip = ast["entry_ip"]

    func_mode = 1 if len(funcs) > 0 else 0
    func_locals_by_ip = [-1] * len(code)
    if func_mode:
        for _, ip, locs in funcs:
            if ip < 0 or ip >= len(code):
                die("bad func ip")
            func_locals_by_ip[ip] = locs

    externs_code = "\n".join(e["code"].strip() for e in EXTERNS)
    externs_names = ",\n    ".join(e["name"] for e in EXTERNS)
    externs_count = len(EXTERNS)

    # code array
    code_lines = []
    for ins in code:
        code_lines.append(f"  {{ {ins.op_name}, {ins.a}, {ins.b} }}")
    code_block = ",\n".join(code_lines)

    # strs array
    if strs:
        str_lines = []
        for sid, txt in strs:
            str_lines.append(f'  {{ {sid}, "{c_escape(txt)}" }}')
        strs_block = ",\n".join(str_lines)
    else:
        strs_block = ""
    strs_len = len(strs)

    # func_locals_by_ip array
    if func_mode:
        fl_lines = ", ".join(str(v) for v in func_locals_by_ip)
        fl_block = fl_lines
    else:
        fl_block = ""

    c = f"""
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>

#define VM_STACK_MAX 1024

typedef struct VM VM;
typedef int32_t (*vm_extern_fn)(VM *vm, int32_t *args, int32_t argc);

typedef enum {{
  OP_NOP,
  OP_PUSH,
  OP_LOAD,
  OP_STORE,
  OP_POP,

  OP_ADD, OP_SUB, OP_MUL, OP_DIV, OP_MOD,
  OP_LT, OP_GT, OP_LE, OP_GE, OP_EQ, OP_NE,
  OP_AND, OP_OR,
  OP_BAND, OP_BOR, OP_BXOR, OP_SHL, OP_SHR,
  OP_NEG, OP_NOT, OP_BNOT,

  OP_JMP, OP_JZ, OP_JNZ,

  OP_CALL,
  OP_CALLX,
  OP_RET,
  OP_RET0,
}} Op;

#define OP_COUNT 33

// encoded ops
#define P1   5
#define P2   7
#define A_PC 11
#define B_PC 3

typedef struct {{
  Op op;
  int32_t a;
  int32_t b;
}} Instr;

typedef struct {{
  int32_t id;
  const char *text;
}} StrEntry;

typedef struct {{
  int ret_ip;
  int locals_base;
  int locals_len;
}} CallFrame;

typedef struct {{
  CallFrame *data;
  int len;
  int cap;
}} FrameVec;

struct VM {{
  const Instr *code;
  int code_len;

  int32_t *locals;
  int locals_cap;
  int locals_top;
  int locals_base;
  int locals_len;

  int legacy_locals_len;

  int32_t stack[VM_STACK_MAX];
  int sp;

  int ip;
  int entry_ip;

  vm_extern_fn *externs;
  int externs_count;

  const StrEntry *strs;
  int strs_len;

  const int *func_locals_by_ip;
  int func_mode;
  FrameVec frames;
}};


static const Instr PROGRAM_CODE[] = {{
{code_block}
}};
static const int PROGRAM_CODE_LEN = {len(code)};
static const int PROGRAM_ENTRY_IP = {entry_ip};
static const int PROGRAM_LEGACY_LOCALS_LEN = {locals_len};
static const int PROGRAM_FUNC_MODE = {func_mode};

static const StrEntry PROGRAM_STRS[] = {{
{strs_block}
}};
static const int PROGRAM_STRS_LEN = {strs_len};

static const int PROGRAM_FUNC_LOCALS_BY_IP[] = {{
{fl_block}
}};


static char globalInput[100];
static int32_t globalInputLen;

//utils
static inline uint32_t hash(const void *data, size_t len){{
    const uint8_t *bytes = (const uint8_t *)data;
    uint32_t h = 0x811C9DC5;    
    for (size_t i = 0; i < len; i++){{
        h ^= bytes[i];
        h *= 0x01000193;
    }}
    return h;
}}

  
static inline void conv_all(const char* str, uint32_t* a, uint32_t* b, uint32_t* c, uint32_t* d) {{
    uint32_t w0 = 0, w1 = 0, w2 = 0, w3 = 0;

    const unsigned char* s = (const unsigned char*)str;
    while (*s != 0) {{
        uint32_t byte = (uint32_t)(*s++);
        uint64_t v0 = (uint64_t)w0 * 255u + byte;
        w0 = (uint32_t)v0;
        uint64_t carry = v0 >> 32;

        uint64_t v1 = (uint64_t)w1 * 255u + carry;
        w1 = (uint32_t)v1;
        carry = v1 >> 32;

        uint64_t v2 = (uint64_t)w2 * 255u + carry;
        w2 = (uint32_t)v2;
        carry = v2 >> 32;

        uint64_t v3 = (uint64_t)w3 * 255u + carry;
        w3 = (uint32_t)v3;
    }}

    *a = w0; *b = w1; *c = w2; *d = w3;
}}

static inline uint32_t conv_a(const char* str) {{ uint32_t a,b,c,d; conv_all(str,&a,&b,&c,&d); return a; }}
static inline uint32_t conv_b(const char* str) {{ uint32_t a,b,c,d; conv_all(str,&a,&b,&c,&d); return b; }}
static inline uint32_t conv_c(const char* str) {{ uint32_t a,b,c,d; conv_all(str,&a,&b,&c,&d); return c; }}
static inline uint32_t conv_d(const char* str) {{ uint32_t a,b,c,d; conv_all(str,&a,&b,&c,&d); return d; }}

static inline int modn(int x) {{
  int r = x % OP_COUNT;
  return (r < 0) ? (r + OP_COUNT) : r;
}}

static inline int egcd(int a, int b, int *x, int *y) {{
  if (b == 0) {{ *x = 1; *y = 0; return a; }}
  int x1, y1;
  int g = egcd(b, a % b, &x1, &y1);
  *x = y1;
  *y = x1 - (a / b) * y1;
  return g;
}}

static inline int modinv(int a, int m) {{
  int x, y;
  int g = egcd(a, m, &x, &y);
  if (g != 1 && g != -1) return -1;
  int inv = x % m;
  if (inv < 0) inv += m;
  return inv;
}}

static inline Op decode_opcode(Op enc, int pc) {{
  static int inv_p1 = -1;
  if (inv_p1 < 0) {{
    inv_p1 = modinv(P1, OP_COUNT);
  }}
  int op_enc = (int)enc;
  int fpc = modn(A_PC * pc + B_PC);
  int t = modn(op_enc - P2 - fpc);
  int op = modn(inv_p1 * t);
  return (Op)op;
}}

static inline void vec_frame_push(FrameVec *v, CallFrame f) {{
  if (v->len == v->cap) {{
    v->cap = v->cap ? v->cap * 2 : 16;
    v->data = (CallFrame*)realloc(v->data, sizeof(CallFrame) * v->cap);
  }}
  v->data[v->len++] = f;
}}

static inline CallFrame vec_frame_pop(FrameVec *v) {{
  return v->data[--v->len];
}}

static inline const char *vm_get_str(VM *vm, int32_t id) {{
  for (int i = 0; i < vm->strs_len; i++) {{
    if (vm->strs[i].id == id) return vm->strs[i].text;
  }}
  return "";
}}


static inline void ensure_locals_cap(VM *vm, int need) {{
  if (need <= vm->locals_cap) return;
  int newcap = vm->locals_cap ? vm->locals_cap * 2 : 64;
  while (newcap < need) newcap *= 2;
  vm->locals = (int32_t*)realloc(vm->locals, sizeof(int32_t) * (size_t)newcap);
  vm->locals_cap = newcap;
}}

static inline void enter_function(VM *vm, int locals_len, int argc, int32_t *args, int push_frame) {{
  if (push_frame) {{
    CallFrame fr;
    fr.ret_ip = vm->ip;
    fr.locals_base = vm->locals_base;
    fr.locals_len = vm->locals_len;
    vec_frame_push(&vm->frames, fr);
  }}

  int new_base = vm->locals_top;
  int new_top = vm->locals_top + locals_len;
  ensure_locals_cap(vm, new_top);

  for (int i = 0; i < locals_len; i++) vm->locals[new_base + i] = 0;
  for (int i = 0; i < argc; i++) {{
    vm->locals[new_base + i] = args[i];
  }}

  vm->locals_base = new_base;
  vm->locals_len = locals_len;
  vm->locals_top = new_top;
}}

static inline int leave_function(VM *vm, int32_t retv, int has_ret) {{
  if (vm->frames.len == 0) {{
    return has_ret ? retv : 0;
  }}

  vm->locals_top = vm->locals_base;

  CallFrame fr = vec_frame_pop(&vm->frames);
  vm->locals_base = fr.locals_base;
  vm->locals_len = fr.locals_len;
  vm->ip = fr.ret_ip;

  vm->stack[vm->sp++] = has_ret ? retv : 0;

  return 0x7fffffff;
}}

//externs functions
{externs_code}

//handlers
typedef int32_t (*OpHandler)(VM *vm, Instr in);

#define VM_CONTINUE 0x7fffffff

static OpHandler DISPATCH_BASE[OP_COUNT];  

static inline int32_t op_nop(VM *vm, Instr in) {{ (void)vm; (void)in; return VM_CONTINUE; }}

static inline int32_t op_push(VM *vm, Instr in) {{ vm->stack[vm->sp++] = in.a; return VM_CONTINUE; }}

static inline int32_t op_load(VM *vm, Instr in) {{
  int idx = in.a;
  int base = vm->func_mode ? vm->locals_base : 0;
  int len = vm->func_mode ? vm->locals_len : vm->legacy_locals_len;
  (void)len;
  vm->stack[vm->sp++] = vm->locals[base + idx];
  return VM_CONTINUE;
}}

static inline int32_t op_store(VM *vm, Instr in) {{
  int idx = in.a;
  int base = vm->func_mode ? vm->locals_base : 0;
  int len = vm->func_mode ? vm->locals_len : vm->legacy_locals_len;
  (void)len;
  vm->locals[base + idx] = vm->stack[--vm->sp];
  return VM_CONTINUE;
}}

static inline int32_t op_pop(VM *vm, Instr in) {{ (void)in; vm->sp--; return VM_CONTINUE; }}

static inline int32_t op_add(VM *vm, Instr in) {{
  (void)in;
  int32_t b = vm->stack[--vm->sp];
  int32_t a = vm->stack[--vm->sp];
  vm->stack[vm->sp++] = a + b;
  return VM_CONTINUE;
}}
static inline int32_t op_sub(VM *vm, Instr in) {{
  (void)in;
  int32_t b = vm->stack[--vm->sp];
  int32_t a = vm->stack[--vm->sp];
  vm->stack[vm->sp++] = a - b;
  return VM_CONTINUE;
}}
static inline int32_t op_mul(VM *vm, Instr in) {{
  (void)in;
  int32_t b = vm->stack[--vm->sp];
  int32_t a = vm->stack[--vm->sp];
  vm->stack[vm->sp++] = a * b;
  return VM_CONTINUE;
}}
static inline int32_t op_div(VM *vm, Instr in) {{
  (void)in;
  int32_t b = vm->stack[--vm->sp];
  int32_t a = vm->stack[--vm->sp];
  vm->stack[vm->sp++] = (b == 0) ? 0 : (a / b);
  return VM_CONTINUE;
}}
static inline int32_t op_mod(VM *vm, Instr in) {{
  (void)in;
  int32_t b = vm->stack[--vm->sp];
  int32_t a = vm->stack[--vm->sp];
  vm->stack[vm->sp++] = (b == 0) ? 0 : (a % b);
  return VM_CONTINUE;
}}

static inline int32_t op_neg(VM *vm, Instr in) {{ (void)in; vm->stack[vm->sp-1] = -vm->stack[vm->sp-1]; return VM_CONTINUE; }}

static inline int32_t op_eq(VM *vm, Instr in) {{
  (void)in;
  int32_t b = vm->stack[--vm->sp];
  int32_t a = vm->stack[--vm->sp];
  vm->stack[vm->sp++] = (a == b);
  return VM_CONTINUE;
}}
static inline int32_t op_ne(VM *vm, Instr in) {{
  (void)in;
  int32_t b = vm->stack[--vm->sp];
  int32_t a = vm->stack[--vm->sp];
  vm->stack[vm->sp++] = (a != b);
  return VM_CONTINUE;
}}
static inline int32_t op_lt(VM *vm, Instr in) {{
  (void)in;
  int32_t b = vm->stack[--vm->sp];
  int32_t a = vm->stack[--vm->sp];
  vm->stack[vm->sp++] = (a < b);
  return VM_CONTINUE;
}}
static inline int32_t op_le(VM *vm, Instr in) {{
  (void)in;
  int32_t b = vm->stack[--vm->sp];
  int32_t a = vm->stack[--vm->sp];
  vm->stack[vm->sp++] = (a <= b);
  return VM_CONTINUE;
}}
static inline int32_t op_gt(VM *vm, Instr in) {{
  (void)in;
  int32_t b = vm->stack[--vm->sp];
  int32_t a = vm->stack[--vm->sp];
  vm->stack[vm->sp++] = (a > b);
  return VM_CONTINUE;
}}
static inline int32_t op_ge(VM *vm, Instr in) {{
  (void)in;
  int32_t b = vm->stack[--vm->sp];
  int32_t a = vm->stack[--vm->sp];
  vm->stack[vm->sp++] = (a >= b);
  return VM_CONTINUE;
}}

static inline int32_t op_and(VM *vm, Instr in) {{
  (void)in;
  int32_t b = vm->stack[--vm->sp];
  int32_t a = vm->stack[--vm->sp];
  vm->stack[vm->sp++] = (a && b);
  return VM_CONTINUE;
}}
static inline int32_t op_or(VM *vm, Instr in) {{
  (void)in;
  int32_t b = vm->stack[--vm->sp];
  int32_t a = vm->stack[--vm->sp];
  vm->stack[vm->sp++] = (a || b);
  return VM_CONTINUE;
}}

static inline int32_t op_band(VM *vm, Instr in) {{
  (void)in;
  int32_t b = vm->stack[--vm->sp];
  int32_t a = vm->stack[--vm->sp];
  vm->stack[vm->sp++] = (a & b);
  return VM_CONTINUE;
}}
static inline int32_t op_bor(VM *vm, Instr in) {{
  (void)in;
  int32_t b = vm->stack[--vm->sp];
  int32_t a = vm->stack[--vm->sp];
  vm->stack[vm->sp++] = (a | b);
  return VM_CONTINUE;
}}
static inline int32_t op_bxor(VM *vm, Instr in) {{
  (void)in;
  int32_t b = vm->stack[--vm->sp];
  int32_t a = vm->stack[--vm->sp];
  vm->stack[vm->sp++] = (a ^ b);
  return VM_CONTINUE;
}}
static inline int32_t op_shl(VM *vm, Instr in) {{
  (void)in;
  int32_t b = vm->stack[--vm->sp];
  int32_t a = vm->stack[--vm->sp];
  vm->stack[vm->sp++] = (a << b);
  return VM_CONTINUE;
}}
static inline int32_t op_shr(VM *vm, Instr in) {{
  (void)in;
  int32_t b = vm->stack[--vm->sp];
  int32_t a = vm->stack[--vm->sp];
  vm->stack[vm->sp++] = (a >> b);
  return VM_CONTINUE;
}}

static inline int32_t op_not(VM *vm, Instr in) {{ (void)in; vm->stack[vm->sp-1] = !vm->stack[vm->sp-1]; return VM_CONTINUE; }}

static inline int32_t op_bnot(VM *vm, Instr in) {{ (void)in; vm->stack[vm->sp-1] = ~vm->stack[vm->sp-1]; return VM_CONTINUE; }}

static inline int32_t op_jmp(VM *vm, Instr in) {{ vm->ip = in.a; return VM_CONTINUE; }}

static inline int32_t op_jz(VM *vm, Instr in) {{
  if (vm->stack[--vm->sp] == 0) vm->ip = in.a;
  return VM_CONTINUE;
}}

static inline int32_t op_jnz(VM *vm, Instr in) {{
  if (vm->stack[--vm->sp] != 0) vm->ip = in.a;
  return VM_CONTINUE;
}}

static inline int32_t op_call(VM *vm, Instr in) {{
  int target = in.a;
  int argc = in.b;
  int locals_len = vm->func_locals_by_ip[target];

  int32_t *args = NULL;
  if (argc > 0) {{
    args = (int32_t*)malloc(sizeof(int32_t) * (size_t)argc);
    for (int32_t i = 0; i < argc; i++) {{
      args[argc - 1 - i] = vm->stack[--vm->sp];
    }}
  }}

  enter_function(vm, locals_len, argc, args, 1);
  free(args);
  vm->ip = target;
  return VM_CONTINUE;
}}

static inline int32_t op_callx(VM *vm, Instr in) {{
  int32_t id = in.a;
  int32_t argc = in.b;
  int32_t *args = (int32_t*)malloc(sizeof(int32_t) * (size_t)argc);
  for (int32_t i = 0; i < argc; i++) {{
    args[argc - 1 - i] = vm->stack[--vm->sp];
  }}
  int32_t ret = vm->externs[id](vm, args, argc);
  free(args);
  vm->stack[vm->sp++] = ret;
  return VM_CONTINUE;
}}

static inline int32_t op_ret(VM *vm, Instr in) {{
  (void)in;
  int32_t retv = vm->stack[--vm->sp];
  int32_t r = leave_function(vm, retv, 1);
  return r;
}}

static inline int32_t op_ret0(VM *vm, Instr in) {{
  (void)in;
  int32_t r = leave_function(vm, 0, 0);
  return r;
}}

static inline void init_dispatch(){{
DISPATCH_BASE[0] = op_nop;
DISPATCH_BASE[1] = op_push;
DISPATCH_BASE[2] = op_load;
DISPATCH_BASE[3] = op_store;
DISPATCH_BASE[4] = op_pop;

DISPATCH_BASE[5] = op_add;
DISPATCH_BASE[6] = op_sub;
DISPATCH_BASE[7] = op_mul;
DISPATCH_BASE[8] = op_div;
DISPATCH_BASE[9] = op_mod;

DISPATCH_BASE[10] = op_lt;
DISPATCH_BASE[11] = op_gt;
DISPATCH_BASE[12] = op_le;
DISPATCH_BASE[13] = op_ge;
DISPATCH_BASE[14] = op_eq;
DISPATCH_BASE[15] = op_ne;

DISPATCH_BASE[16] = op_and;
DISPATCH_BASE[17] = op_or;

DISPATCH_BASE[18] = op_band;
DISPATCH_BASE[19] = op_bor;
DISPATCH_BASE[20] = op_bxor;
DISPATCH_BASE[21] = op_shl;
DISPATCH_BASE[22] = op_shr;

DISPATCH_BASE[23] = op_neg;
DISPATCH_BASE[24] = op_not;
DISPATCH_BASE[25] = op_bnot;

DISPATCH_BASE[26] = op_jmp;
DISPATCH_BASE[27] = op_jz;
DISPATCH_BASE[28] = op_jnz;

DISPATCH_BASE[29] = op_call;
DISPATCH_BASE[30] = op_callx;
DISPATCH_BASE[31] = op_ret;
DISPATCH_BASE[32] = op_ret0;
}}
  
static inline void permute(int pc, OpHandler *out) {{
  for (int enc = 0; enc < OP_COUNT; enc++) {{
    Op real = decode_opcode((Op)enc, pc);
    out[enc] = DISPATCH_BASE[(int)real];
  }}
}}

/* ---------- VM run ---------- */

static inline int32_t vm_run(vm_extern_fn *externs, int externs_count) {{
  init_dispatch();
  VM vm;
  memset(&vm, 0, sizeof(vm));

  vm.externs = externs;
  vm.externs_count = externs_count;

  vm.code = PROGRAM_CODE;
  vm.code_len = PROGRAM_CODE_LEN;
  vm.entry_ip = PROGRAM_ENTRY_IP;
  vm.ip = PROGRAM_ENTRY_IP;

  vm.strs = PROGRAM_STRS;
  vm.strs_len = PROGRAM_STRS_LEN;

  vm.func_mode = PROGRAM_FUNC_MODE;
  vm.func_locals_by_ip = PROGRAM_FUNC_MODE ? PROGRAM_FUNC_LOCALS_BY_IP : NULL;
  vm.legacy_locals_len = PROGRAM_LEGACY_LOCALS_LEN;

  vm.sp = 0;

  if (vm.func_mode) {{
    int entry_locals = (vm.entry_ip >= 0 && vm.entry_ip < vm.code_len)
                         ? vm.func_locals_by_ip[vm.entry_ip]
                         : -1;
    enter_function(&vm, entry_locals, 0, NULL, 0);
  }} else {{
    vm.locals_len = vm.legacy_locals_len;
    if (vm.locals_len) {{
      vm.locals = (int32_t*)calloc((size_t)vm.locals_len, sizeof(int32_t));
    }}
  }}

  for (;;) {{
    int pc = vm.ip;
    Instr in = vm.code[vm.ip++];

    OpHandler dispatch_op[OP_COUNT];
    permute(pc, dispatch_op);

    int32_t r = dispatch_op[(int)in.op](&vm, in);
    if (r != VM_CONTINUE) return r;
  }}
}}


int main(void) {{
  scanf("%s", globalInput);
  int i;
  while (globalInput[globalInputLen++] != '\\0');
  vm_extern_fn externs[] = {{
    {externs_names}
  }};
  int32_t ret = vm_run(externs, {externs_count});
  if (ret) printf("%s\\n", globalInput);
  return (int)ret;
}}
"""
    return c



if __name__ == "__main__":
    with open(sys.argv[1], "r", encoding="utf-8") as f:
        text = f.read()

    parsed = parse_file(text)
    c = generate_c(parsed)

    with open(sys.argv[2], "w", encoding="utf-8") as f:
        f.write(c)
