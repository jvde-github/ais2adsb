import socket
import pyais
from pyais import decode
import time
from datetime import datetime
import sys

ICAOmap = {}
maxICAO = 0xFFFF00

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

    print(f'MSG,3,1,0,{ICAO},1,{dstr},{tstr},{dstr},{tstr},,{alt},,,{lat},{lon},,,0,0,0,0')
    print(f'MSG,4,1,0,{ICAO},1,{dstr},{tstr},{dstr},{tstr},,,{speed},{heading},,,0,,,,,')


if len(sys.argv) < 3:
    print("Usage: python ais2adsb.py <IP address> <port number>")
    sys.exit(1)

UDP_IP = sys.argv[1]
UDP_PORT = int(sys.argv[2])
includeShips = False

if len(sys.argv) == 4:
    includeShips = True

print(f"IP address: {UDP_IP}", file=sys.stderr)
print(f"Port number: {UDP_PORT}", file=sys.stderr)
print(f"Include Ships: {includeShips}", file=sys.stderr)


sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

while True:
    data, addr = sock.recvfrom(1024)  
    nmea = data.decode()
    # Does not handle multi-part messages which I am skipping for now
    try:
        decoded = decode(nmea).asdict()
    except pyais.exceptions.MissingMultipartMessageException as e:
        print()
    if decoded['msg_type']==9 and includeShips:
        toBSformat(decoded)
    if decoded['msg_type']<=3 and includeShips:
        toBSformat(decoded)
