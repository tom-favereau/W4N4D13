# W4N4D13

![course](https://img.shields.io/badge/course-Master%20SIRAV%20Malware%2FRE-blue)
![lang](https://img.shields.io/badge/lang-C%20%7C%20OCaml%20%7C%20Python-lightgrey)
![platform](https://img.shields.io/badge/platform-Windows%20x86-orange)

## Abstract

W4N4D13 is a software-protection project built for the Malware/Reverse Engineering course (Master SIRAV, Prof. Guillaume Bonfante). The program requires an 8-character license key drawn from `[0-9a-zA-Z]^8`; both the verification logic and the correct key must be completely obscured. To that end, the core verification routine is hidden inside a custom stack-based bytecode virtual machine, and the source is hardened by a three-stage static obfuscation pipeline (control-flow flattening, MBA-based opaque predicates, virtualization). Protections target dynamic analysis: the primary defensive mechanism is a self-debugging watchdog process that exchanges cryptographic heartbeats every 200 ms, supplemented by VM-embedded honeypot anti-debug checks and an RDTSC-based ratio test that detects Intel PIN instrumentation.

---

## Repository Structure

| Path | Role |
|---|---|
| `W4N4D13.cpp` | source code |
| `final.c` | code that is virtualized |
| `generate_vm.py` | Python script that emits the bytecode VM and compiled bytecode |
| `lib/flatten.ml` | OCaml/CIL pass — control-flow flattening |
| `lib/opaque.ml` | OCaml/CIL pass — opaque predicates via MBA |
| `lib/virtualize.ml` | OCaml/CIL pass — code virtualization |
| `lib/mba.py` | MBA expression generator |
| `lib/solvemod.py` | Modular linear system solver over rings |
| `bin/main.ml` | OCaml main |
| `prog` | Final protected binary MSVC10 |
| `W4N4D13.pdf` | technical paper |

---

## Build Pipeline

The full obfuscation pipeline is (Listing 1 from the paper):

```sh
# 1. C preprocessor pass
gcc -E W4N4D13.c > out.c

# 2. CIL passes (OCaml — requires ocamlfind + CIL)
./main.native out.c out_flat.c    -flatten
./main.native out_flat.c out_op.c -opaque
./main.native out_op.c  out_virt.c -virtualize

# 3. VM generation (Python 3)
python3 generate_vm.py out_virt.c W4N4D13_final.c
```

**Dependencies:** OCaml ≥ 4.x with `ocamlfind` and the CIL library; Python 3.

Each pass operates on a plain C file and writes a transformed C file. The final output `W4N4D13_final.c` contains the embedded bytecode and VM interpreter and can be compiled with any x86 C compiler targeting Windows.

---

## Static Obfuscation

### Control-Flow Flattening (CFF)

Implemented in `lib/flatten.ml`. Every function's control flow is completely flattened into a single `switch` statement inside an infinite loop. The original basic blocks become cases, and a `state` variable determines which case executes next. The program becomes a state machine whose edges are no longer visible in the CFG.

```c
// Before
if (cond) A(); else B();

// After (schematic)
while (1) {
    switch (state) {
        case 0: if (cond) state = 1; else state = 2; break;
        case 1: A(); state = EXIT; break;
        case 2: B(); state = EXIT; break;
    }
}
```

CFF alone does not resist modern deobfuscators, so it is reinforced by opaque predicates.

### Opaque Predicates via MBA

Implemented in `lib/opaque.ml` using `lib/mba.py` / `lib/solvemod.py`. For every state-variable assignment produced by CFF:

```
next = x   →   next = O^x
```

where `O^x` is a Mixed Boolean-Arithmetic expression that always evaluates to `x` but is hard to simplify automatically. A canonical example:

```
x + y  =  (x ⊕ y) + 2·(x ∧ y)
```

Arithmetic operations are rewritten as linear combinations of bitwise operations (`⊕`, `∧`, `∨`, `¬`). Modern tools can simplify many linear MBA instances, so a non-linear layer is added via permutation polynomials (see next section).

---

## MBA Generation & Permutation Polynomials

Finding a MBA rewrite is reduced to solving a linear system over the ring R = ℤ/2³²ℤ. Because R is not a field, the system may have many solutions; the implementation selects the most voluminous one (most nonzero coefficients) to maximise term count and complicate simplification.

**Basis.** A small number of Boolean variables `a_i` are chosen; the basis consists of all pairwise combinations `a_i ⊕ a_j`, `a_i ∧ a_j`, `a_i ∨ a_j` and their bitwise negations `¬(·)`. Coefficients `c_k` are solved such that their weighted sum equals the target constant truth-table vector (mod 2³²).

**Non-linear layer.** After obtaining a linear MBA expression `comb_lin`, a permutation polynomial `P(x)` over R = ℤ/2³²ℤ and its inverse `P⁻¹(x)` are composed around it:

```
result = P(P⁻¹(comb_lin))
```

This is semantically a no-op, but it wraps the linear expression in a non-linear shell. A polynomial `f(x) = Σ aₖxᵏ` (mod 2³²) is a permutation polynomial of R when:
- `a₁` is odd,
- Σ `a_k` for even k ≥ 2 is even,
- Σ `a_k` for odd k ≥ 3 is even.

The inverse `P⁻¹` is computed iteratively: `g = inv(P) ∘ P`, refined up to 32 rounds until `g` is the identity. Canonical representation uses falling-factorial polynomials `Pᵢ(x) = n/gcd(n,i!) · (x)ᵢ` to handle the quotient structure of R reliably.

---

## Virtualization

Implemented in `lib/virtualize.ml` and `generate_vm.py`. The obfuscated C function is compiled to a custom stack-based bytecode with **33 opcodes**. The VM interpreter (`generate_vm.py` output) is embedded directly in the final binary.

Key design points:

- **CALLX instruction** — provides an oracle for operations too complex for the VM's restricted C subset (no `struct`, no arrays). `CALLX` invokes host functions through a VM API.
- **Semantic permutation** — after every opcode execution, the VM state is transformed by an affine pseudo-random permutation shared between the compiler (which emits the bytecode) and the interpreter (which decodes it). This means raw bytecode has no stable semantic meaning and cannot be disassembled without knowing the permutation key.

When a debugger is detected, the VM intentionally skips the opcode decoding phase, causing the executed bytecode to lose all semantic meaning. The interpreter then crashes via a segmentation fault, preventing dynamic instrumentation tools (e.g. Intel PIN) from continuing their analysis.

---

## Malware Protection

Protection operates at three independent levels.

### 1 — Self-Debugging Watchdog

A program cannot be attached to by more than one debugger simultaneously. On startup the main process (parent) spawns a copy of itself (child). The child immediately calls `DebugActiveProcess` to attach to the parent as its exclusive debugger.

**Heartbeat protocol (every 200 ms):**

1. The parent waits on a named Windows Event object (name derived from a secret random `DWORD` key transmitted to the child as `argv[2]` in hexadecimal — not from the PID, to prevent name guessing).
2. The parent deposits a random nonce in a named shared memory region. The child reads the nonce, computes `response = ComputeResponse(nonce, secretKey)`, writes the response back, then calls `SetEvent`.
3. The parent verifies the response value before accepting the heartbeat.

If the child cannot launch (e.g. IDA opens the binary in debug mode), `SetEvent` is never called, the parent's `WaitForSingleObject` times out, and the parent enters an altered execution path.

**Hook detection:** before every `WaitForSingleObject` call, the parent reads the first 5 bytes of the function in memory and compares them against the expected Windows XP x86 prologue (`8B FF 55 8B EC` — `MOV EDI,EDI / PUSH EBP / MOV EBP,ESP`). An inline hook would replace those bytes with a `JMP (0xE9...)`, which is detected immediately.

### 2 — Honeypots (VM Disguise)

Each opcode handler contains a fake but credible anti-debug check. Since the real protection is the challenge-response watchdog, these checks never alter VM behaviour — their sole purpose is to waste analyst time. Implemented honeypots:

| Opcode | Check |
|---|---|
| `op_nop` | NtGlobalFlag via PEB (`__readfsdword(0x30) + 0x68`): bits `0x70` set when debugged |
| `op_push` | Timing: delta > 50 ms between two successive PUSH instructions → single-stepping |
| `op_load` | Heap debug flags: `_HEAP.Flags` at offset `0x0C`; extra bits beyond `HEAP_GROWABLE (0x02)` |
| `op_store` | `IsDebuggerPresent` — the classic PEB check |
| `op_jmp` | INT3 scan: verifies the first 16 bytes of the `op_jmp` handler for `0xCC` breakpoints |
| `op_callx` | `NtQueryInformationProcess` class 7 (`ProcessDebugPort`): nonzero → debugger attached |
| `op_ret` | `NtQueryInformationProcess` class `0x1E` (`ProcessDebugObjectHandle`): non-null → debugged |

### 3 — Anti-PIN (RDTSC Ratio)

Intel PIN is a Dynamic Binary Instrumentation framework that JIT-compiles user-mode code while leaving kernel code uninstrumented. This inflates user-mode execution time by 10–50× while syscall time remains nearly constant.

The ratio is measured with RDTSC:

- **t_user** — RDTSC around a pure arithmetic loop (user-mode dominated).
- **t_kernel** — RDTSC around N `CloseHandle(INVALID_HANDLE_VALUE)` calls (kernel dominated).

Normally `t_user / t_kernel ≈ 1`. Under PIN, `t_user` explodes (~×20) while `t_kernel` stays stable. When the ratio exceeds **20.0**, the program switches to an altered execution path (same as when the watchdog fires).

---

## License Verification Core

The verification routine is a **modified SHA-256** operating over a 128-bit state represented as four 32-bit unsigned integers (instead of the standard eight). The 8-character input key (charset `[0-9a-zA-Z]`) is first encoded via base-255 into four `uint32_t` values, which seed the modified hash. The expected digest of the correct key is hard-coded in the binary.

---

## Authors

- **Thomas Dollé**
- **Tom Favereau**

*Master SIRAV — Malware/Reverse Engineering, Prof. Guillaume Bonfante — March 2026*

## References

1. Christian Collberg, Jasvir Nagra. *Surreptitious Software: Obfuscation, Watermarking, and Tamperproofing for Software Protection.* Addison-Wesley Professional, 2009.
2. Justus Polzin. *Mixed Boolean Arithmetics.*
