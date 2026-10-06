from machine import Pin, PWM, reset
import network    
import time
import socket
import rp2
import array
import ujson
import os


STATE_FILE = "rgb.json"
UPDATE_FILE = "main.py.new"
BACKUP_FILE = "main.py.bak"
MAX_UPLOAD_SIZE = 200000

pin = Pin(22, Pin.OUT)
ledQty = 2 # 140 for charizard

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

def clamp_color(value, fallback):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return fallback
    return max(0, min(255, value))

def clamp_mode(value, fallback):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return fallback
    if value in (1, 2, 3):
        return value
    return fallback

def save_state():
    with open(STATE_FILE, "w") as fp:
        ujson.dump({
            "red": red,
            "green": green,
            "blue": blue,
            "mode": mode,
        }, fp)

def load_state():
    global red, green, blue, mode
    try:
        with open(STATE_FILE) as fp:
            data = ujson.load(fp)
            red = clamp_color(data.get("red"), red)
            green = clamp_color(data.get("green"), green)
            blue = clamp_color(data.get("blue"), blue)
            mode = clamp_mode(data.get("mode"), mode)
    except (OSError, ValueError):
        save_state()

def get_form_value(request_str, name):
    marker = name + "="
    if request_str.find(marker) == -1:
        return None
    return request_str.split(marker, 1)[1].split("&", 1)[0].split("'", 1)[0].split("\\r\\n", 1)[0]

def get_header(headers, name):
    name = name.lower() + ":"
    for line in headers.split("\r\n"):
        if line.lower().startswith(name):
            return line.split(":", 1)[1].strip()
    return None

def remove_if_exists(filename):
    try:
        os.remove(filename)
    except OSError:
        pass

def install_update():
    remove_if_exists(BACKUP_FILE)
    os.rename("main.py", BACKUP_FILE)
    try:
        os.rename(UPDATE_FILE, "main.py")
    except OSError:
        os.rename(BACKUP_FILE, "main.py")
        raise

def handle_upload(cl, headers, body):
    update_installed = False
    try:
        content_length = get_header(headers, "Content-Length")
        content_type = get_header(headers, "Content-Type")
        if content_length is None or content_type is None:
            return False, "Missing upload headers"

        content_length = int(content_length)
        if content_length <= 0 or content_length > MAX_UPLOAD_SIZE:
            return False, "Upload is empty or too large"
        if content_type.find("boundary=") == -1:
            return False, "Missing multipart boundary"

        boundary = content_type.split("boundary=", 1)[1].strip().strip('"')
        boundary = boundary.encode()
        end_marker = b"\r\n--" + boundary

        received = len(body)
        buffer = body
        while buffer.find(b"\r\n\r\n") == -1:
            if received >= content_length:
                return False, "Upload part header was incomplete"
            chunk = cl.recv(min(1024, content_length - received))
            if not chunk:
                return False, "Upload stopped before file data"
            buffer += chunk
            received += len(chunk)

        part_header_end = buffer.find(b"\r\n\r\n")
        part_headers = buffer[:part_header_end].decode()
        if part_headers.find('name="file"') == -1:
            return False, "Upload field must be named file"

        data = buffer[part_header_end + 4:]
        bytes_written = 0
        keep = len(end_marker)

        remove_if_exists(UPDATE_FILE)
        with open(UPDATE_FILE, "wb") as fp:
            while True:
                marker_index = data.find(end_marker)
                if marker_index != -1:
                    fp.write(data[:marker_index])
                    bytes_written += marker_index
                    break

                safe_len = len(data) - keep
                if safe_len > 0:
                    fp.write(data[:safe_len])
                    bytes_written += safe_len
                    data = data[safe_len:]

                if received >= content_length:
                    return False, "Upload ended before multipart boundary"

                chunk = cl.recv(min(1024, content_length - received))
                if not chunk:
                    return False, "Upload connection closed early"
                data += chunk
                received += len(chunk)

        if bytes_written == 0:
            return False, "Uploaded file was empty"

        install_update()
        update_installed = True
        return True, "main.py uploaded. Rebooting Pico..."
    finally:
        if not update_installed:
            remove_if_exists(UPDATE_FILE)

def send_html(cl, body):
    cl.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
    cl.send(body)

# Wi-Fi credentials
ssid = 'Sunrise_4513373'
password = 'uh7PbxaR2qridsfj'

# Static IP configuration
static_ip = '192.168.1.21'  # Choose an IP in your network range
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
    <hr>
    <h2>Update code</h2>
    <form action="/upload" method="post" enctype="multipart/form-data">
        <input type="file" name="file" accept=".py">
        <button type="submit">Upload main.py</button>
    </form>
</body>
</html>
"""

# Create a socket and bind it to the IP address and port
#addr = socket.getaddrinfo('192.168.1.20', 80)
addr = (static_ip,80)
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
    request = cl.recv(4096)
    header_end = request.find(b"\r\n\r\n")
    if header_end != -1:
        headers = request[:header_end].decode()
        body = request[header_end + 4:]
    else:
        headers = request.decode()
        body = b""
    request_str = str(request)
    print(headers)

    if headers.find("POST /upload") != -1:
        try:
            update_ok, update_message = handle_upload(cl, headers, body)
        except Exception as e:
            update_ok = False
            update_message = "Upload failed: " + str(e)

        send_html(cl, "<html><body><p>{}</p><a href='/'>Back</a></body></html>".format(update_message))
        cl.close()

        if update_ok:
            time.sleep_ms(500)
            reset()
        continue
    
    # Check if it's a GET request to toggle the LED
    if '/setrgb' in request_str:
        red_value = get_form_value(request_str, "RED")
        green_value = get_form_value(request_str, "GREEN")
        blue_value = get_form_value(request_str, "BLUE")
        mode_value = get_form_value(request_str, "mode")

        if red_value is not None and green_value is not None and blue_value is not None:
            red = clamp_color(red_value, red)
            print('value of red is: ', red)
            green = clamp_color(green_value, green)
            print('value of green is: ', green)
            blue = clamp_color(blue_value, blue)
            print('value of blue is: ', blue)                         
            mode = clamp_mode(mode_value, mode)
            print('value of mode is: ', mode)
            save_state()
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
    
