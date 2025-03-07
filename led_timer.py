import machine
import time

# Initialize the onboard LED
led = machine.Pin("LED", machine.Pin.OUT)

# Create a Timer object
timer = machine.Timer()

# Define a function with timer as parameter
def toggle_led(timer):
    led.toggle()

# Initialise the timer to call the function *toggle_led* 
# *period* in milliseconds
# *mode* calling the function periodically (vs one shot)
# *callback* the function to be called
timer.init(period=200, mode=machine.Timer.PERIODIC, callback=toggle_led)

def main():
    print("Hello, world!")
    while True:
        ... # do what you want


# Call main function
main()