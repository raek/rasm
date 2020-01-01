    in      r0, 63
    ldi     r0, 255
    lds     r31, 0
    mov     r0, r31
    movw    r1:r0, r31:r30
    out     63, r0
    pop     r0
    push    r0
    sts     0, r31
