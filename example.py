#!/usr/bin/env python3

#### Button Blink ####

### This example extends the blink program to read from a GPIO input
### pin connected to a push-button.  The LED will only blink while you
### are holding the button down.

from itertools import cycle
from time import sleep
## You must import the GPIO pins and direction constants In
## and Out from quick2wire.gpio before you can use them
from quick2wire.gpio import pins, In, Out
##.

## Get hold of the input and output pins from the bank of GPIO pins.
button = pins.pin(0, direction=In)
led = pins.pin(1, direction=Out)
##.

## The with statement acquires the button and led pins and ensures
## that they are always released when the body of the statement
## finishes, whether successfully or by an exception being thrown.
with button, led:
##.
    print("ready")
    ## The program then runs an infinite loop.  Each time round the
    ## loop, v alternates between True and False.
    for v in cycle([True,False]):
        ## Read the state of the button pin and combine with v to get
        ## the new state to be written to the LED pin.  When both the
        ## button pin and v are True, this will set the LED pin to
        ## True. If either are False, this sets the LED pin to False.
        led.value = v and button.value
        ##.
        ## Sleep a bit before the next iteration, so that the LED
        ## blinks on-and-off once per second.
        sleep(0.5)
    ##.

