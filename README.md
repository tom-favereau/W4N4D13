# W4N4D13 — Crackme (OCaml CIL / C)

![course](https://pfst.cf2.poecdn.net/base/image/19598122b9f5616f333ad97a1ffd54ac2b16a1869f34238c376e48f8ce8483f8?pmaid=583607117)
![lang](https://pfst.cf2.poecdn.net/base/image/f1a6939261ed3eea40f66399c5098781f18d4d72f6677965bf714a288a094a8b?pmaid=583607118)
![platform](https://pfst.cf2.poecdn.net/base/image/bac601843643965c467dcd4f1a9892145b76c1921218afd84237ed5ffd02d5a7?pmaid=583607116)

**Keywords:** OCaml CIL, C, crackme

## About

This repository contains a **crackme** built for the *Master SIRAV Malware/Reverse Engineering* course.

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
| `prog/` | Final protected binary (MSVC10, Windows x86) |
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

