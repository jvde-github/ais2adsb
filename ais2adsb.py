import socket
import pyais
from pyais import decode
import time
from datetime import datetime
import sys

ICAOmap = {}
maxICAO = 0xFFFFFF
client_socket = None
SERVER_IP = "192.168.1.235"
SERVER_PORT = 30003

def generateICAO(mmsi):
    global ICAOmap, maxICAO
    if mmsi not in ICAOmap:
        ICAOmap[mmsi] = maxICAO
        maxICAO = maxICAO - 1

    return ICAOmap[mmsi]

def connectClient():
    global client_socket
    global SERVER_IP, SERVER_PORT

    while True:
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((SERVER_IP, SERVER_PORT))
            break
        except (socket.error, OSError) as e:
            print(f"Error: failed to connect to server: error code {e}",file=sys.stderr)
            time.sleep(10)
            continue

    print(f"AIS2ADSB: Connected to ADSB server",file=sys.stderr)

def sendBaseStation(decoded):

    #print(decoded)
    #print(decoded['mmsi'])
    #print(f"Message from {decoded['mmsi']} of type {decoded['msg_type']}", file=sys.stderr)

    ICAO = generateICAO(decoded['mmsi'])
    ICAO = '%X' % ICAO

    now_utc = datetime.now()
    dstr = now_utc.strftime("%Y/%m/%d")
    tstr = now_utc.strftime("%H:%M:%S.%f")[:-3]
    if 'alt' in decoded:
        alt = decoded['alt']
    else:
        alt = 0

    lat = decoded['lat']
    lon = decoded['lon']
    speed = decoded['speed']
    heading = decoded['course']

    global client_socket

    s1 = f'MSG,3,1,0,{ICAO},1,{dstr},{tstr},{dstr},{tstr},,{alt},,,{lat},{lon},,,0,0,0,0\n'
    s2 = f'MSG,4,1,0,{ICAO},1,{dstr},{tstr},{dstr},{tstr},,,{speed},{heading},,,0,,,,,\n'

    if client_socket == None:
        print(s1)
        print(s2)
    else:
        try:            
            client_socket.send(s1.encode())
            client_socket.send(s2.encode())
        except (socket.error, OSError):
            print("Connection lost. Reconnecting...")
            client_socket.close()
            client_socket = None 
            connectClient()
         

if len(sys.argv) < 5:
    print("Usage: python ais2adsb.py <AIS UDP address> <AIS UDP port> <BS server address> <BS server port> <include ships if not empty>")
    sys.exit(1)

UDP_IP = sys.argv[1]
UDP_PORT = int(sys.argv[2])
includeShips = False

SERVER_IP = sys.argv[3]
SERVER_PORT = int(sys.argv[4])

if len(sys.argv) == 6:
    includeShips = True

print(f"AIS address: {UDP_IP} {UDP_PORT}", file=sys.stderr)
print(f"ADSB address: {SERVER_IP} {SERVER_PORT}", file=sys.stderr)
print(f"Ships included: {includeShips}", file=sys.stderr)

connectClient()

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

next_update_time = time.monotonic() + 10
count  = 0

while True:
    data, addr = sock.recvfrom(1024)  
    nmea = data.decode()
    # Does not handle multi-part messages which I am skipping for now
    # Should not be an issue for SAR
    try:
        decoded = decode(nmea).asdict()
    except pyais.exceptions.MissingMultipartMessageException as e:
        pass

    if decoded['msg_type']==9 or (decoded['msg_type']<=3 and includeShips):
        sendBaseStation(decoded)
        count = count + 1

    if time.monotonic() >= next_update_time:
        t = time.strftime('%Y-%m-%d %H:%M:%S')
        print(f'{t} Messages sent: {count}')
        count = 0
        next_update_time += 10

client_socket.close()