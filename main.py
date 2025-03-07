from machine import Pin
import network    
import time
import socket
import neopixel

pin = Pin(0)
ledQty = 2
strip = neopixel.NeoPixel(pin,ledQty)

led = Pin("LED", Pin.OUT)
red = 180
green = 0
blue = 150

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

print('Listening on', addr)

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
            blue = int(request_str.split('BLUE=')[1].split("'")[0])
            print('value of blue is: ', blue)
            green = int(request_str.split('GREEN=')[1].split('&')[0])
            print('value of green is: ', green)
            strip[0] = (blue, red, green)
            strip[1] = (blue, red, green)
            strip.write()
            led.value(1)
            time.sleep_ms(200)
            led.value(0)
    if '/ledon' in request_str:
        led.value(1)
    if '/ledoff' in request_str:
        led.value(0)
    
    # Send back the HTML response with the current state of the LED
    response_html = html.format("ON" if led.value() else "OFF", red, green, blue)
    
    cl.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
    cl.send(response_html)
    
    cl.close()

