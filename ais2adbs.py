import socket
import pyais
from pyais import decode
import time
from datetime import datetime
import sys

ICAOmap = {}
maxICAO = 0xFFFF00
client_socket = None

def generateICAO(mmsi):
    global ICAOmap, maxICAO
    if mmsi not in ICAOmap:
        ICAOmap[mmsi] = maxICAO
        maxICAO = maxICAO + 1

    return ICAOmap[mmsi]


def toBSformat(decoded):

    #print(decoded)
    #print(decoded['mmsi'])
    print(f"Message from {decoded['mmsi']} of type {decoded['msg_type']}", file=sys.stderr)

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
        client_socket.send(s1.encode())
        client_socket.send(s2.encode())

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

print(f"IP address: {UDP_IP}", file=sys.stderr)
print(f"Port number: {UDP_PORT}", file=sys.stderr)
print(f"Include Ships: {includeShips}", file=sys.stderr)

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((SERVER_IP, SERVER_PORT))

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

while True:
    data, addr = sock.recvfrom(1024)  
    nmea = data.decode()
    # Does not handle multi-part messages which I am skipping for now
    try:
        decoded = decode(nmea).asdict()
    except pyais.exceptions.MissingMultipartMessageException as e:
        print('Skipping message',file=sys.stderr)

    if decoded['msg_type']==9 and includeShips:
        toBSformat(decoded)
    if decoded['msg_type']<=3 and includeShips:
        toBSformat(decoded)

client_socket.send(message.encode())
client_socket.close()
