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
        ldi     r1, loops

; Order of definition and usage does not matter
        ldi     r1, defined_later
.equ defined_later = 2
