#!/usr/bin/env bash

set -u

mkdir -p test_out

function error() {
    echo "$1"
    exit 1
}

function check() {
    python3 rasm.py test/"$1".s -o test_out/"$1".bin || error "rasm.py failed"
    cmp test/"$1".bin test_out/"$1".bin || error "output not correct"
}

check empty