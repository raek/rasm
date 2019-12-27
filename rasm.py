import argparse
import collections
import enum
import re
import struct


class ArgType(enum.Enum):
    NONE = 0
    ADDR = 1
    ADDR_OFFSET = 2
    IO = 3
    BIT = 4
    REG = 5


ARG_TYPE_CHARS = {
    " ": ArgType.NONE,
    "A": ArgType.ADDR,
    "a": ArgType.ADDR_OFFSET,
    "i": ArgType.IO,
    "b": ArgType.BIT,
    "r": ArgType.REG,
}


INSTRUCTIONS = {
    "nop":   ("  ", "0000 0000 0000 0000"),
    "lsl":   ("r ", "0000 11Aa aaaa AAAA"),
    "rol":   ("r ", "0001 11Aa aaaa AAAA"),
    "swap":  ("r ", "1001 010a aaaa 0010"),
    "asr":   ("r ", "1001 010a aaaa 0101"),
    "lsr":   ("r ", "1001 010a aaaa 0110"),
    "ror":   ("r ", "1001 010a aaaa 0111"),
    "jmp":   ("A ", "1001 010a aaaa 110a aaaa aaaa aaaa aaaa"),
    "bset":  ("b ", "1001 0100 0aaa 1000"),
    "sec":   ("  ", "1001 0100 0000 1000"),
    "sez":   ("  ", "1001 0100 0001 1000"),
    "sen":   ("  ", "1001 0100 0010 1000"),
    "sev":   ("  ", "1001 0100 0011 1000"),
    "ses":   ("  ", "1001 0100 0100 1000"),
    "seh":   ("  ", "1001 0100 0101 1000"),
    "set":   ("  ", "1001 0100 0110 1000"),
    "sei":   ("  ", "1001 0100 0111 1000"),
    "bclr":  ("b ", "1001 0100 1aaa 1000"),
    "clc":   ("  ", "1001 0100 1000 1000"),
    "clz":   ("  ", "1001 0100 1001 1000"),
    "cln":   ("  ", "1001 0100 1010 1000"),
    "clv":   ("  ", "1001 0100 1011 1000"),
    "cls":   ("  ", "1001 0100 1100 1000"),
    "clh":   ("  ", "1001 0100 1101 1000"),
    "clt":   ("  ", "1001 0100 1110 1000"),
    "cli":   ("  ", "1001 0100 1111 1000"),
    "sleep": ("  ", "1001 0101 1000 1000"),
    "break": ("  ", "1001 0101 1001 1000"),
    "wdr":   ("  ", "1001 0101 1010 1000"),
    "cbi":   ("ib", "1001 1000 aaaa abbb"),
    "sbi":   ("ib", "1001 1010 aaaa abbb"),
    "rjmp":  ("a ", "1100 aaaa aaaa aaaa"),
    "bld":   ("rb", "1111 100a aaaa 0bbb"),
    "bst":   ("rb", "1111 101a aaaa 0bbb"),
}


class Label(collections.namedtuple("Label", ["symbol", "weak"])):

    def __new__(cls, symbol, weak=False):
        return super(Label, cls).__new__(cls, symbol, weak)


class Insn(collections.namedtuple("Insn", ["op", "arg1", "arg2", "bit_pattern", "size", "arg1_type", "arg2_type"])):

    def __new__(cls, op, arg1=None, arg2=None):
        if op in INSTRUCTIONS:
            arg_types, bit_pattern = INSTRUCTIONS[op]
            arg1_type = ARG_TYPE_CHARS[arg_types[0]]
            arg2_type = ARG_TYPE_CHARS[arg_types[1]]
            size = len(bit_pattern) // 16
            return super(Insn, cls).__new__(cls, op, arg1, arg2, bit_pattern, size, arg1_type, arg2_type)
        else:
            raise Exception("Unknown instruction: " + op)

    def words(self):
        arg1 = self.arg1
        arg2 = self.arg2
        arg1_dupe = self.arg1
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
                bit = arg1 & 1
                arg1 >>= 1
            elif bit_type == "b":
                bit = arg2 & 1
                arg2 >>= 1
            elif bit_type == "A":
                bit = arg1_dupe & 1
                arg1_dupe >>= 1
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
    m = re.match(r"\s+(?P<op>\w+)(\s+(?P<arg1>\w+)(,\s*(?P<arg2>\w+))?)?\s*$", line)
    if m:
        return Insn(*m.group("op", "arg1", "arg2"))
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
            arg1 = eval_arg(stmt.arg1_type, stmt.arg1, labels, addr)
            arg2 = eval_arg(stmt.arg2_type, stmt.arg2, labels, addr)
            yield stmt._replace(arg1=arg1, arg2=arg2)
        else:
            raise ValueError(stmt)


def eval_arg(arg_type, arg, labels, current_addr):
    if arg_type == ArgType.NONE:
        assert arg is None
        return None
    if arg_type == ArgType.ADDR:
        dest_addr = labels[arg]
        return dest_addr
    elif arg_type == ArgType.ADDR_OFFSET:
        dest_addr = labels[arg]
        return (dest_addr - current_addr) % 0x10000
    elif arg_type == ArgType.IO:
        return int(arg)
    elif arg_type == ArgType.BIT:
        return int(arg)
    elif arg_type == ArgType.REG:
        assert arg.startswith("r")
        return int(arg[1:])
    else:
        raise ValueError(arg_type)


def write_program(outfile, insns):
    for insn in insns:
        for word in insn.words():
            write_word(outfile, word)


def write_word(outfile, word):
    outfile.write(struct.pack("<H", word))


if __name__ == "__main__":
    main()