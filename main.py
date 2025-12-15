from machine import Pin, PWM
import network    
import time
import socket
import rp2
import array
import ujson


pin = Pin(22, Pin.OUT)
ledQty = 140

led = Pin("LED", Pin.OUT)
red = 0
green = 0
blue = 20
mode = 1


@rp2.asm_pio(sideset_init=rp2.PIO.OUT_LOW, out_shiftdir=rp2.PIO.SHIFT_LEFT, autopull=True, pull_thresh=24)
def ws2812():
    T1 = 2 #2
    T2 = 5 #5
    T3 = 3 #3
    wrap_target()
    label("bitloop")
    out(x, 1) .side(0) [T3 - 1]
    jmp(not_x, "do_zero") .side(1) [T1 - 1]
    jmp("bitloop") .side(1) [T2 - 1]
    label("do_zero")
    nop() .side(0) [T2 - 1]
    wrap()

# Create the StateMachine with the ws2812 program
# GREEN RED BLUE
sm = rp2.StateMachine(0, ws2812, freq=8_000_000, sideset_base=pin)
# Start the StateMachine, it will wait for data on its FIFO.
sm.active(1)

def putRGB(num,color):
    ar = array.array("I", [0 for _ in range(ledQty)])
    ar[num] = color
    sm.put(ar,8)

def putRGBs(color):
    ar = array.array("I", [0 for _ in range(ledQty)])
    for i in range(ledQty):
        ar[i] = color
    sm.put(ar,8)
        
def save_rgb():
    with open("rgb.json", "w") as fp:
        ujson.dump({"red": red, "green": green, "blue": blue}, fp)

def load_state():
    global red, green, blue
    try:
        with open("rgb.json") as fp:
            data = ujson.load(fp)
            red, green, blue = data.get("red",red), data.get("green",green), data.get("blue",blue)           
    except OSError:
        pass 

# Wi-Fi credentials
ssid = 'Sunrise_4513373'
password = 'uh7PbxaR2qridsfj'

# Static IP configuration
static_ip = '192.168.1.20'  # Choose an IP in your network range
subnet_mask = '255.255.255.0'
gateway = '192.168.1.1'  # Usually your router's IP
dns_server = '8.8.8.8'  # Google's DNS, you can use your router's IP instead

# Initialize WLAN interface
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.config(hostname="MyPicoW-1")

# Set static IP before connecting
wlan.ifconfig((static_ip, subnet_mask, gateway, dns_server))

# Connect to Wi-Fi
wlan.connect(ssid, password)

# Wait for connection
max_wait = 10
while max_wait > 0:
    if wlan.status() >= 3:  # Connected
        print('Connected to Wi-Fi')
        print('IP Address:', wlan.ifconfig()[0])
        break
    max_wait -= 1
    print('Waiting for connection...')
    time.sleep(1)

if wlan.status() != 3:
    raise RuntimeError('Failed to connect to Wi-Fi')

# HTML response for the web page
html = """<!DOCTYPE html>
<html>
<head>
    <title>Pico W LED Control</title>
</head>
<body>
    <h1>LED Control</h1>
    <p>LED is currently: <strong>{}</strong></p>
    <form action="/setrgb" method="post">
    <button type="submit">Send</button>
    <div>
    Red:
        <input type="range" min="0" max="255" value={} class="slider" id="slideR" name="RED">
    <div>
        Green:
        <input type="range" min="0" max="255" value={} class="slider" id="slideG" name="GREEN">
    </div>
    <div>
        Blue:
        <input type="range" min="0" max="255" value={} class="slider" id="slideB" name="BLUE">        
    </div>
    <div>
        Mode 1:
        <input type="radio" value=1 name="mode" {}>
        Mode 2:
        <input type="radio" value=2 name="mode" {}>
        Mode 3:
        <input type="radio" value=3 name="mode" {}>        
    </div>
    </form>
</body>
</html>
"""

# Create a socket and bind it to the IP address and port
#addr = socket.getaddrinfo('192.168.1.20', 80)
addr = ('192.168.1.20',80)
print(addr)
s = socket.socket()
s.bind(addr)
s.listen(1)

# print('Listening on', addr)


i = 0
for i in range(30):
    time.sleep_ms(30)
    led.value(i%2)
    i=i+1

load_state()
putRGBs(green << 16 | red << 8 | blue)

while True:        
    # Accept a connection
    cl, addr = s.accept()
    print('Client connected from', addr)
    
    # Receive the request
    request = cl.recv(2048)
    request_str = str(request)
    print(request_str)    
    
    # Check if it's a GET request to toggle the LED
    if '/setrgb' in request_str:
        if request_str.find('RED=') != -1:
            red = int(request_str.split('RED=')[1].split('&')[0])
            print('value of red is: ', red)
            blue = int(request_str.split('BLUE=')[1].split("&")[0])
            print('value of blue is: ', blue)
            green = int(request_str.split('GREEN=')[1].split('&')[0])
            print('value of green is: ', green)                         
            mode = int(request_str.split('mode=')[1].split("'")[0])
            print('value of mode is: ', mode)
            save_rgb()
            led.value(1)
            time.sleep_ms(200)
            led.value(0)
    if '/ledon' in request_str:
        led.value(1)
    if '/ledoff' in request_str:
        led.value(0)

    if mode == 1:
        putRGBs(green << 16 | red << 8 | blue)
    elif mode == 2:
        for i in range(10):
            time.sleep_ms(200)
            putRGBs(green << 16 | red << 8 | blue)
            time.sleep_ms(200)
            putRGBs(0)
    elif mode == 3:
        for i in range(30):
            time.sleep_ms(30)
            putRGBs(green << 16 | red << 8 | blue)
            time.sleep_ms(30)
            putRGBs(0)
    
    # Send back the HTML response with the current state of the LED
    if mode == 1:        
        response_html = html.format("ON" if led.value() else "OFF", red, green, blue, "checked", "unchecked", "unchecked")
    elif mode == 2:
        response_html = html.format("ON" if led.value() else "OFF", red, green, blue, "unchecked", "checked", "unchecked")
    elif mode == 3:
        response_html = html.format("ON" if led.value() else "OFF", red, green, blue, "unchecked", "unchecked", "checked")
    #print(response_html)
    
    cl.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
    cl.send(response_html)
    
    cl.close()
    