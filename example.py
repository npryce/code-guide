#!/usr/bin/env python3

### Button Blink ###

### This example extends the blink program to read from a GPIO input
### pin connected to a push-button.  The LED will only blink while you
### are holding the button down.

from itertools import cycle
from time import sleep
## You must import the GPIO pins and direction constants In
## and Out from quick2wire.gpio before you can use them
from quick2wire.gpio import pins, In, Out
##.

## blah blah
button = pins.pin(0, direction=In)
led = pins.pin(1, direction=Out)
##.

## The with statement acquires the button and led pins and ensures
## that they are always released when the body of the statement
## finishes, whether successfully or by an exception being thrown.
with button, led:
##.
    print("ready")
    ## the program then runs an infinite loop.  Each time round the
    ## loop, v alternates between True and False.
    for v in cycle([True,False]):
        ## read button and assign to LED
        led.value = v and button.value
        ##.
        sleep(0.5)
    ##.

