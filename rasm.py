import argparse
import collections
import enum
import re
import struct


class ArgType(enum.Enum):
    ADDR = 0
    ADDR_OFFSET = 1


INSTRUCTIONS = {
    "rjmp":  ("1100 aaaa aaaa aaaa",                     ArgType.ADDR_OFFSET),
    "jmp":   ("1001 010a aaaa 110a aaaa aaaa aaaa aaaa", ArgType.ADDR),
}


class Label(collections.namedtuple("Label", ["symbol", "weak"])):

    def __new__(cls, symbol, weak=False):
        return super(Label, cls).__new__(cls, symbol, weak)


class Insn(collections.namedtuple("Insn", ["op", "arg", "bit_pattern", "size", "arg_type"])):

    def __new__(cls, op, arg):
        if op in INSTRUCTIONS:
            bit_pattern, arg_type = INSTRUCTIONS[op]
            size = len(bit_pattern) // 16
            return super(Insn, cls).__new__(cls, op, arg, bit_pattern, size, arg_type)
        else:
            raise Exception("Unknown instruction: " + op)

    def words(self):
        arg = self.arg
        words = []
        word = 0
        i = 0
        for bit_type in reversed(self.bit_pattern):
            if bit_type == " ":
                continue
            elif bit_type == "0":
                bit = 0
            elif bit_type == "1":
                bit = 1
            elif bit_type == "a":
                bit = arg & 1
                arg >>= 1
            else:
                raise ValueError(bit_type)
            word |= bit << i
            i += 1
            if i == 16:
                words.insert(0, word)
                i = 0
                word = 0
        return words


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
            addr += stmt.size
        else:
            raise ValueError(stmt)
    result = dict(weak_labels)
    for label, addr in labels.items():
        result[label] = addr
    return result


def fix(program, labels):
    addr = 0
    for stmt in program:
        if isinstance(stmt, Label):
            pass
        elif isinstance(stmt, Insn):
            addr += stmt.size
            yield stmt._replace(arg=eval_arg(stmt.arg_type, stmt.arg, labels, addr))
        else:
            raise ValueError(stmt)


def eval_arg(arg_type, arg, labels, current_addr):
    dest_addr = labels[arg]
    if arg_type == ArgType.ADDR:
        return dest_addr
    elif arg_type == ArgType.ADDR_OFFSET:
        return (dest_addr - current_addr) % 0x10000


def write_program(outfile, insns):
    for insn in insns:
        for word in insn.words():
            write_word(outfile, word)


def write_word(outfile, word):
    outfile.write(struct.pack("<H", word))


if __name__ == "__main__":
    main()