#!/usr/bin/env python3

#|| Button Blink
#|| ============
#||
#|| This example extends the [blink program](blink) to read from a
#|| GPIO input pin connected to a push-button.  The LED will only
#|| blink while you are holding the button down.

from itertools import cycle
from time import sleep
#| [5] You must import the GPIO pins and direction constants In and
#| Out from quick2wire.gpio before you can use them
from quick2wire.gpio import pins, In, Out
#|.

#| [4] Get hold of the input and output pins from the bank of GPIO
#| pins.
button = pins.pin(0, direction=In)
led = pins.pin(1, direction=Out)
#|.

#| [6] The with statement acquires the button and led pins and ensures
#| that they are always released when the body of the statement
#| finishes, whether successfully or by an exception being thrown.
with button, led:
#|.
    print("ready")
    #| [1] This is the core of the program: an infinite loop that
    #| reads from and writes to the GPIO pins connected to the button
    #| and LED.  Each time round the loop, _blink_state_ alternates
    #| between 1 (voltage high) and 0 (voltage low).
    for blink_state in cycle([1,0]):
        #| [2] Read the state of the button pin multiply it with
        #| _blink_state_ to get the new state to be written to the LED
        #| pin.  When both the button pin and _blink_state_ are 1,
        #| this will set the LED pin to 1. If either are 0, this will
        #| set the LED pin to 0.
        led.value = blink_state and button.value
        #|.
        #| [3] Sleep a bit before the next iteration, so that the LED
        #| blinks on and off once per second.
        sleep(0.5)
    #|.
