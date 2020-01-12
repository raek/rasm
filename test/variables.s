; Registers
.equ dst = r0
.equ src = r1
        mov     dst, src

; Register pairs
.equ dstpair = r1:r0
.equ srcpair = r3:r2
        movw dstpair, srcpair

; Labels
.equ loc = label
label:
        rjmp    loc

; Constants
.equ loops = 100
        ldi     r17, loops

; Order of definition and usage does not matter
        ldi     r17, defined_later
.equ defined_later = 2

; Fallback values
.default default_a = 3
        ldi     r17, default_a
.default default_b = 4
.equ default_b = 5
        ldi     r17, default_b
