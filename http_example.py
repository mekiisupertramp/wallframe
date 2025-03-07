import network
import time
import socket
import machine

ssid = 'Sunrise_4513373'
password = 'uh7PbxaR2qridsfj'

# Initialize the LED on GPIO pin 25 (onboard LED)
led = machine.Pin("LED", machine.Pin.OUT)
led.off()  # Ensure the LED is off initially

# Define the static IP address for the Raspberry Pi Pico WH
static_ip = '192.168.1.20'
# Define the subnet mask for the network
subnet_mask = '255.255.255.0'
# Define the gateway IP address, usually the IP of your router
gateway = '192.168.1.1'
# Define the DNS server IP address, using Google's DNS in this case
dns_server = '8.8.8.8'

# Initialize the Wi-Fi interface in station mode
wlan = network.WLAN(network.STA_IF)
# Activate the Wi-Fi interface
wlan.active(True)
# Set the hostname for the device
wlan.config(hostname="MyPicoW-1")
# Configure the Wi-Fi interface with the static IP, subnet mask, gateway, and DNS server
wlan.ifconfig((static_ip, subnet_mask, gateway, dns_server))
# Connect to the Wi-Fi network using the provided SSID and password
wlan.connect(ssid, password)

max_wait = 10
while max_wait > 0:
    if wlan.status() >= 3:
        print('Connected to Wi-Fi')
        print('IP Address:', wlan.ifconfig()[0])
        break
    max_wait -= 1
    print('Waiting for connection...')
    time.sleep(1)

if wlan.status() != 3:
    raise RuntimeError('Failed to connect to Wi-Fi')

# Create a socket object
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(('0.0.0.0', 80))  # Bind to all interfaces on port 80
s.listen(5)  # Listen for incoming connections

print('Web server is running...')

while True:
    conn, addr = s.accept()
    print('Got a connection from %s' % str(addr))
    request = str(conn.recv(1024))
    print('Content = %s' % request)

    if '/led_on' in request:
        led.on()
        response = 'LED is ON'
    elif '/led_off' in request:
        led.off()
        response = 'LED is OFF'
    else:
        response = 'Unknown request'

    conn.send('HTTP/1.1 200 OK\n')
    conn.send('Content-Type: text/html\n')
    conn.send('Connection: close\n\n')
    conn.sendall(response)
    conn.close()
