OCAMLBUILD=ocamlbuild
PKGS=cil
INCLUDES=-Is bin -Is lib
TARGET=bin/main.native

.PHONY: all build run clean

all: build

build:
	$(OCAMLBUILD) -use-ocamlfind -pkgs $(PKGS) $(INCLUDES) $(TARGET)

run: build
	./_build/$(TARGET)

clean:
	$(OCAMLBUILD) -clean
