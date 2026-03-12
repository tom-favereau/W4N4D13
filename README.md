# W4N4D13

## About

This repository contains a **crackme** built for the Master SIRAV Malware/Reverse course.

We encourage you to **try cracking it by yourself first** before looking at the source code or reading the technical paper.

Good luck.

## What you’ll find (high level)

- A protected Windows x86 program that expects an **8-character license key**
- A build pipeline based on **C transformations (via OCaml/CIL passes)** and a custom **VM-based** protection layer
- An accompanying **technical paper (PDF)** for readers who want full details

## Repository structure

| Path | Description |
|---|---|
| `W4N4D13.cpp` | Main source code |
| `final.c` | Core routine (input to the protection/virtualization stage) |
| `generate_vm.py` | VM + bytecode generator |
| `lib/flatten.ml` | OCaml/CIL pass: control-flow flattening |
| `lib/opaque.ml` | OCaml/CIL pass: opaque predicates (MBA) |
| `lib/virtualize.ml` | OCaml/CIL pass: code virtualization |
| `lib/mba.py` | MBA expression generator |
| `lib/solvemod.py` | Modular solver used by the MBA tooling |
| `bin/main.ml` | OCaml entry point for the passes |
| `prog` | Final protected binary (MSVC10, Windows x86) |
| `W4N4D13.pdf` | Technical paper |

## Build (pipeline overview)

> The full pipeline is documented in the paper. This section only gives an overview.
## Build (pipeline overview)

## Build (pipeline overview)

```sh
# 1) Preprocess
gcc -E W4N4D13.c > out.c

# 2) OCaml/CIL passes
./main.native out.c      out_flat.c -flatten
./main.native out_flat.c out_op.c   -opaque
./main.native out_op.c   out_virt.c -virtualize

# 3) VM generation
python3 generate_vm.py out_virt.c W4N4D13_final.c
```

## Dependencies

- OCaml 4.01.0 (ocamlbuild)
- CIL 1.7
- Python 3.x
- gcc (preprocessor pass)

