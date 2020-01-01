#!/usr/bin/env bash

set -u
export LANG=C

mkdir -p test_out

function error() {
    echo "$1"
    exit 1
}

function disassemble() {
    (cd "$1" && avr-objdump -b binary -m avr -D "$2".bin > "$2"_dis.txt) || error "disassembly failed: $1/$2.bin"
}

function assemble() {
    python3 rasm.py test/"$1".s -o test_out/"$1".bin || error "assembly failed: test/$1"
}

function diff_disassembly() {
    colordiff -u test/"$1"_dis.txt test_out/"$1"_dis.txt || error "output not correct"
}

function check() {
    echo "$1"
    disassemble test "$1"
    assemble "$1"
    disassemble test_out "$1"
    diff_disassembly "$1"
}

check syntax
check empty
check jumps
check bits
check mcuctrl
check arithlog
