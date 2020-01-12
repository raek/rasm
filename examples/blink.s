; Output square wave of CPU frequency / 1000

.equ PINB = 3
.equ DDRB = 4
.equ PORTB = 5
.equ LED_BIT = 5

RESET:
        sbi     DDRB, LED_BIT
blink_loop:

; 495 cycles
        ldi     r16, 165
delay_loop:
        dec     r16
        brne    delay_loop

; 5 cycles
        nop
        sbi     PINB, LED_BIT
        rjmp    blink_loop
