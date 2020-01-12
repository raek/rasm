        elpm
        elpm    r0, z
        elpm    r0, z+
        in      r0, 63
        lac     z, r0
        las     z, r0
        lat     z, r0
        ld      r0, x
        ld      r0, x+
        ld      r0, -x
        ld      r0, y
        ld      r0, y+
        ld      r0, -y
        ld      r0, z
        ld      r0, z+
        ld      r0, -z
        ldd     r0, y+63
        ldd     r0, z+63
        ldi     r16, 255
        lds     r31, 0
        lpm
        lpm     r0, z
        lpm     r0, z+
        mov     r0, r31
        movw    r1:r0, r31:r30
        out     63, r0
        pop     r0
        push    r0
        spm
        spm     z+
        st      x, r0
        st      x+, r0
        st      -x, r0
        st      y, r0
        st      y+, r0
        st      -y, r0
        st      z, r0
        st      z+, r0
        st      -z, r0
        std     y+63, r0
        std     z+63, r0
        sts     0, r31
        xch     z, r0
