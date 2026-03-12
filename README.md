# W4N4D13

## About

This repository contains a **crackme** built for the Master SIRAV Malware/Reverse course.

We encourage you to **try cracking it by yourself first** before looking at the source code or reading the technical paper.

Good luck.

## Repository structure

| Path | Description |
|---|---|
| `W4N4D13.cpp` | Main source code |
| `final.c` | Core routine (that is virtualized) |
| `generate_vm.py` | VM + bytecode packer |
| `lib/flatten.ml` | OCaml pass: control-flow flattening |
| `lib/opaque.ml` | OCaml pass: opaque predicates (MBA) |
| `lib/virtualize.ml` | OCaml pass: code virtualization |
| `lib/mba.py` | MBA expression generator |
| `lib/solvemod.py` | Linear solver over ring used by the MBA tooling |
| `bin/main.ml` | OCaml main |
| `W4N4D13.exe` | Final binary (MSVC10, Windows x86) |
| `W4N4D13.pdf` | Technical paper |



## Build (pipeline overview)

```sh
# 1) Preprocess
gcc -E W4N4D13.c > out.c

# 2) OCaml/CIL passes
./main.native out.c      out_flat.c -flatten
./main.native out_flat.c out_op.c   -opaque
./main.native out_op.c   out_virt.opcode -virtualize

# 3) VM generation
python3 generate_vm.py out_virt.opcode W4N4D13.c
```

## Dependencies

- OCaml 4.01.0 (ocamlbuild)
- CIL 1.7
- Python 3.x
- gcc (preprocessor pass)

