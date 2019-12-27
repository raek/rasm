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


INSTRUCTIONS = {
    "asr":   ("1001 010a aaaa 0101",                     ArgType.REG,         ArgType.NONE),
    "bclr":  ("1001 0100 1aaa 1000",                     ArgType.BIT,         ArgType.NONE),
    "bld":   ("1111 100a aaaa 0bbb",                     ArgType.REG,         ArgType.BIT),
    "bset":  ("1001 0100 0aaa 1000",                     ArgType.BIT,         ArgType.NONE),
    "bst":   ("1111 101a aaaa 0bbb",                     ArgType.REG,         ArgType.BIT),
    "cbi":   ("1001 1000 aaaa abbb",                     ArgType.IO,          ArgType.BIT),
    "clc":   ("1001 0100 1000 1000",                     ArgType.NONE,        ArgType.NONE),
    "clh":   ("1001 0100 1101 1000",                     ArgType.NONE,        ArgType.NONE),
    "cli":   ("1001 0100 1111 1000",                     ArgType.NONE,        ArgType.NONE),
    "cln":   ("1001 0100 1010 1000",                     ArgType.NONE,        ArgType.NONE),
    "cls":   ("1001 0100 1100 1000",                     ArgType.NONE,        ArgType.NONE),
    "clt":   ("1001 0100 1110 1000",                     ArgType.NONE,        ArgType.NONE),
    "clv":   ("1001 0100 1011 1000",                     ArgType.NONE,        ArgType.NONE),
    "clz":   ("1001 0100 1001 1000",                     ArgType.NONE,        ArgType.NONE),
    "lsl":   ("0000 11Aa aaaa AAAA",                     ArgType.REG,         ArgType.NONE),
    "lsr":   ("1001 010a aaaa 0110",                     ArgType.REG,         ArgType.NONE),
    "rjmp":  ("1100 aaaa aaaa aaaa",                     ArgType.ADDR_OFFSET, ArgType.NONE),
    "rol":   ("0001 11Aa aaaa AAAA",                     ArgType.REG,         ArgType.NONE),
    "ror":   ("1001 010a aaaa 0111",                     ArgType.REG,         ArgType.NONE),
    "sbi":   ("1001 1010 aaaa abbb",                     ArgType.IO,          ArgType.BIT),
    "sec":   ("1001 0100 0000 1000",                     ArgType.NONE,        ArgType.NONE),
    "seh":   ("1001 0100 0101 1000",                     ArgType.NONE,        ArgType.NONE),
    "sei":   ("1001 0100 0111 1000",                     ArgType.NONE,        ArgType.NONE),
    "sen":   ("1001 0100 0010 1000",                     ArgType.NONE,        ArgType.NONE),
    "ses":   ("1001 0100 0100 1000",                     ArgType.NONE,        ArgType.NONE),
    "set":   ("1001 0100 0110 1000",                     ArgType.NONE,        ArgType.NONE),
    "sev":   ("1001 0100 0011 1000",                     ArgType.NONE,        ArgType.NONE),
    "sez":   ("1001 0100 0001 1000",                     ArgType.NONE,        ArgType.NONE),
    "swap":  ("1001 010a aaaa 0010",                     ArgType.REG,         ArgType.NONE),
    "jmp":   ("1001 010a aaaa 110a aaaa aaaa aaaa aaaa", ArgType.ADDR,        ArgType.NONE),
}


class Label(collections.namedtuple("Label", ["symbol", "weak"])):

    def __new__(cls, symbol, weak=False):
        return super(Label, cls).__new__(cls, symbol, weak)


class Insn(collections.namedtuple("Insn", ["op", "arg1", "arg2", "bit_pattern", "size", "arg1_type", "arg2_type"])):

    def __new__(cls, op, arg1=None, arg2=None):
        if op in INSTRUCTIONS:
            bit_pattern, arg1_type, arg2_type = INSTRUCTIONS[op]
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