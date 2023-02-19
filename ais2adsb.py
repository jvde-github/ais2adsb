#!/usr/bin/python3

import socket
import pyais
from pyais import decode
import time
from datetime import datetime
import sys

ICAOmap = { 111232512:0x406C79,
            111232511:0x406C82,
            111232513:0x406C8E,
            111232516:0x406D2C,
            111232517:0x406D2D,
            111232523:0x406DDB,
            111232524:0x406DDC,
            111232529:0x406F8B,
            111232526:0x406EE7,
            111232528:0x406F2D,
            111232518:0x406D21,
            111232533:0x406DE5,
            111232522:0x406DE6,
            111232527:0x406DE7,
            111232525:0x406DE8,
            111232534:0x406DE9,
            111232535:0x406DEA,
            111232537:0x406DEB,
            111232539:0x406DED,
            111232531:0x43ECF4,
            250002898:0x4CA98D,
            250002897:0x4CA98F,
            250002902:0x4CA98B,
            250004879:0x4CACA4,
            250002901:0x4CA98C,
            111232519:0x48644B,
            111232538:0x485F8F,
            111503003:0x4860B1,
            111232509:0x47BFE4
}

client_socket = None
SERVER_IP = "192.168.1.235"
SERVER_PORT = 30003

def generateICAO(mmsi):
    global ICAOmap, maxICAO
    if mmsi not in ICAOmap:
        proposedICAO = 0xF00000 | (mmsi & 0xFFFFF)
        print(hex(proposedICAO))
        if proposedICAO in ICAOmap.values():
            while True:
                proposedICAO = (proposedICAO + 1) & 0xFFFFFF
                if proposedICAO not in ICAOmap.values():
                    break
        ICAOmap[mmsi] = proposedICAO

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
    callsign = "AIS" + ICAO[4:]

    global client_socket

    #s1 = f'MSG,3,1,0,{ICAO},1,{dstr},{tstr},{dstr},{tstr},,{alt},,,{lat},{lon},,,0,0,0,0\n'
    #s2 = f'MSG,4,1,0,{ICAO},1,{dstr},{tstr},{dstr},{tstr},,,{speed},{heading},,,0,,,,,\n'

    spos = f'MSG,2,1,0,{ICAO},1,{dstr},{tstr},{dstr},{tstr},,{alt},{speed},{heading},{lat},{lon},,,,,,0\n'
    scs = f'MSG,2,1,0,{ICAO},1,{dstr},{tstr},{dstr},{tstr},{callsign},,,,,,,,,,,\n'

    if client_socket == None:
        print(spos)
    else:
        try:            
            client_socket.send(spos.encode())
            #client_socket.send(scs.encode())
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