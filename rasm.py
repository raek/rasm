import argparse
import collections
import re
import struct


class Label(collections.namedtuple("Label", ["symbol", "weak"])):

    def __new__(cls, symbol, weak=False):
        return super(Label, cls).__new__(cls, symbol, weak)


class Insn(collections.namedtuple("Insn", ["op", "arg", "code", "words"])):

    def __new__(cls, op, arg):
        if op == "jmp":
            return super(Insn, cls).__new__(cls, op, arg, 0x940C, 2)
        else:
            raise Exception("Unknown instruction: " + op)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("infile", nargs="+")
    parser.add_argument("-o", "--outfile", required=True)
    args = parser.parse_args()
    program = []
    program += emit_interrupt_vector_table()
    for infile_name in args.infile:
        with open(infile_name, "rt") as infile:
            program += assemble(infile)
    insns = link(program)
    with open(args.outfile, "wb") as outfile:
        write_program(outfile, insns)


def assemble(infile):
    for line in infile:
        line = line.rstrip("\n")
        yield parse_line(line)


def parse_line(line):
    m = re.match(r"(?P<label>\w+):\s*$", line)
    if m:
        return Label(m.group("label"))
    m = re.match(r"\s+(?P<op>\w+)(\s+(?P<arg>\w+))?\s*$", line)
    if m:
        return Insn(*m.group("op", "arg"))
    else:
        raise Exception("syntax error: " + line)


def emit_interrupt_vector_table():
    interrupts = 26
    # Interrupt vector table
    yield Label("__vectors")
    yield Insn("jmp", "RESET")
    for _ in range(interrupts-1):
        yield Insn("jmp", "__bad_interrupt")
    # Bad interrupt handler
    yield Label("__bad_interrupt")
    yield Label("RESET", weak=True)
    yield Insn("jmp", "__vectors")


def link(program):
    labels = scan(program)
    return list(fix(program, labels))


def scan(program):
    addr = 0
    labels = {}
    weak_labels = {}
    for stmt in program:
        if isinstance(stmt, Label):
            if stmt.weak:
                if stmt.symbol in weak_labels:
                    raise Exception("Weak label mutliply-defined: " + stmt.symbol)
                weak_labels[stmt.symbol] = addr
            else:
                if stmt.symbol in labels:
                    raise Exception("Label mutliply-defined: " + stmt.symbol)
                labels[stmt.symbol] = addr
        elif isinstance(stmt, Insn):
            addr += stmt.words
        else:
            raise ValueError(stmt)
    result = dict(weak_labels)
    for label, addr in labels.items():
        result[label] = addr
    return result


def fix(program, labels):
    for stmt in program:
        if isinstance(stmt, Label):
            pass
        elif isinstance(stmt, Insn):
            yield stmt._replace(arg=eval_addr(stmt.arg, labels))
        else:
            raise ValueError(stmt)


def eval_addr(expr, labels):
    if isinstance(expr, int):
        return expr
    elif isinstance(expr, str):
        return labels[expr]


def write_program(outfile, insns):
    for insn in insns:
        write_word(outfile, insn.code)
        write_word(outfile, insn.arg)


def write_word(outfile, word):
    outfile.write(struct.pack("<H", word))


if __name__ == "__main__":
    main()