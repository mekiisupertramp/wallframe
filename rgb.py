import neopixel
import machine
import time

# Setting the GP0 pin (#1 on the RP2040's connector)
pin = machine.Pin(0)
# Setting the number of stripes
ledQty = 2
# Create a strip object
strip = neopixel.NeoPixel(pin,ledQty) 

# set color BRG (24=3*8 bits)
b = 30
r = 30
g = 0
strip[0] = (b, r, g) # type: ignore | purple
b = 0
r = 30
g = 30
strip[1] = (b, r, g) # type: ignore | yellow
strip.write()

# Wait 2 seconds
time.sleep(2)

# Do something completly random (what? it's my code!)
while True:
    time.sleep_ms(20)
    b = b+10
    g = g+5
    if b > 80:
        g = g+10
    strip[0] = (g,30,15) # type: ignore
    strip[1] = (0, b, g) # type: ignore
    strip.write()
