#!/usr/bin/python3

import socket
import signal
import pyais
from pyais import decode
import ast
import time
from datetime import datetime
import sys

ICAOmap = { 111232512:0x406C79, 111232511:0x406C82, 111232513:0x406C8E, 111232516:0x406D2C, 111232517:0x406D2D, 111232523:0x406DDB, 111232524:0x406DDC, 111232529:0x406F8B, 111232526:0x406EE7,
            111232528:0x406F2D, 111232518:0x406D21, 111232533:0x406DE5, 111232522:0x406DE6, 111232527:0x406DE7, 111232525:0x406DE8, 111232534:0x406DE9, 111232535:0x406DEA,111232537:0x406DEB,
            111232539:0x406DED, 111232531:0x43ECF4, 250002898:0x4CA98D, 250002897:0x4CA98F, 250002902:0x4CA98B, 250004879:0x4CACA4, 250002901:0x4CA98C, 111232519:0x48644B,111232538:0x485F8F,
            111503003:0x4860B1, 111232509:0x47BFE4 }

settings = { "SERVER_IP":"", "SERVER_PORT": 0, "UDP_IP":"" , "UDP_PORT":0, "includeShips":False, "includeCallSign": True, "printDict": False }

client_socket = None
sent = 0

def generateICAO(mmsi):
    global ICAOmap, maxICAO
    if mmsi not in ICAOmap:
        proposedICAO = 0xF00000 | (mmsi & 0xFFFFF)
        print(f'New mmsi: {mmsi}, generated ICAO: {"%X" % proposedICAO}', file=sys.stderr)
        if proposedICAO in ICAOmap.values():
            while True:
                print(f'ICAO occupied, skipping to next', file=sys.stderr)
                proposedICAO = (proposedICAO + 1) & 0xFFFFFF
                if proposedICAO not in ICAOmap.values():
                    break
        ICAOmap[mmsi] = proposedICAO

    return ICAOmap[mmsi]

def connectClient():
    global client_socket
    global settings

    while True:
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((settings["SERVER_IP"], settings["SERVER_PORT"]))
            break
        except (socket.error, OSError) as e:
            print(f"Error: failed to connect to server: error code {e}",file=sys.stderr)
            time.sleep(10)
            continue

    print(f"Status: Connected to ADSB server",file=sys.stderr)

def loadMMSIdict(str):
    
    print(f'Reading dictionary from MMSI to ICAO from file "{str}"')

    with open(str) as f:
        data = f.read()
        d = ast.literal_eval(data)
  
        global ICAOmap

        for key in d:
            if key in ICAOmap and ICAOmap[key] != d[key]:                
                print(f'\tWarning: overwrite {key} -> {"%X" % ICAOmap[key]}',file=sys.stderr)
            ICAOmap[key] =  d[key]
    f.close()

def printDictionary():
    print("{", end="",file=sys.stderr)
    first = True
    for key in ICAOmap:
        if first: 
            first = False
        else:
            print(",", end="",file=sys.stderr)

        print(f"{key}:0x{'%X'%ICAOmap[key]}", end="",file=sys.stderr)

    print("}",file=sys.stderr)

def sendBaseStation(decoded):

    global settings

    alt = decoded.get('alt', 0)
    lat = decoded.get('lat', None)
    lon = decoded.get('lon', None)
    speed = decoded.get('speed', None)
    heading = decoded.get('course', None)

    if lat != None and lon != None and speed != None and heading != None:
        ICAO = '%X' % generateICAO(decoded['mmsi'])

        now_utc = datetime.now()
        dstr = now_utc.strftime("%Y/%m/%d")
        tstr = now_utc.strftime("%H:%M:%S.%f")[:-3]
        callsign = "V:" + ("00000" + str(decoded['mmsi']) )[-6:]

        global client_socket

        spos = f'MSG,2,1,0,{ICAO},1,{dstr},{tstr},{dstr},{tstr},,{alt},{speed},{heading},{lat},{lon},,,,,,0\n'
        scs = f'MSG,1,1,0,{ICAO},1,{dstr},{tstr},{dstr},{tstr},{callsign},,,,,,,,,,,\n'
        
        if client_socket == None:
            print(spos)
            print(scs)
        else:
            try:         
                client_socket.send(spos.encode())
                if settings["includeCallSign"]:
                    client_socket.send(scs.encode())

                global sent
                sent = sent + 1

            except (socket.error, OSError):
                print("Connection lost. Reconnecting...")
                client_socket.close()
                client_socket = None 
                connectClient()
            
# this should be fixed so we properly close the sockets etc....

def printUsage():
    print("Usage: (python) ais2adsb.py <AIS UDP address> <AIS UDP port> <BS server address> <BS server port> <options>")
    print("Options:")
    print("\tFILE xxxx        : read mmsi <-> ICAO mapping from file xxxx")
    print("\tSHIPS on/off     : include ships in sendout")
    print("\tCALLSIGN on/off  : include generated callsigns in sendout")
    print("\tPRINT on/off     : print mmsi/ICAO dictionary")

def signalHandler(sig, frame):
    print('Ctrl+C pressed terminating')
    sys.exit(0)

def parseSwitch(str):
    if str.upper() == "ON": 
        return True
    elif str.upper() == "OFF": 
        return False

    raise Exception("Unknown switch on command line: " + str)
    
def parseCommandLine():
    global UDP_IP, UDP_PORT, SERVER_IP,SERVER_PORT, includeShips, includeCallSign

    if len(sys.argv) < 5:
        if len(sys.argv) > 1:
            raise Exception("Command line should at least have 4 parameters")
    
        return False

    settings["UDP_IP"] = sys.argv[1]
    settings["UDP_PORT"] = int(sys.argv[2])

    settings["SERVER_IP"] = sys.argv[3]
    settings["SERVER_PORT"] = int(sys.argv[4])

    if len(sys.argv) >= 6:
        if len(sys.argv) >= 7 and len(sys.argv) % 2 == 1:
            for i in range(5,  len(sys.argv),2):   
                opt = sys.argv[i].upper()
                if opt == 'SHIPS':
                    settings["includeShips"] = parseSwitch(sys.argv[i+1])
                elif opt == 'PRINT':
                    settings["printDict"] = parseSwitch(sys.argv[i+1])                    
                elif opt == 'FILE':
                    loadMMSIdict(sys.argv[i+1])
                elif opt == 'CALLSIGN':
                    settings["includeCallSign"] = parseSwitch(sys.argv[i+1])
                else:
                    raise Exception("Unknown option on command line: " + opt)
        else:
            # allow old command line for now....
            if len(sys.argv) == 6 and sys.argv[5] == '1':
                settings["includeShips"] = True
                print("Warning: command line parameters - please use ais2adsb .... SHIPS on, shortcut will disappear in future versions")
                return True
            
            raise Exception("Command line options should be in key/value pairs")

    return True


signal.signal(signal.SIGINT, signalHandler)

print(f"AIS2ADSB v0.11 - see https://github.com/jvde-github/ais2adsb", file=sys.stderr)

try:
    if not parseCommandLine():
        printUsage()
        sys.exit(0)
except Exception as e:
    print(e)
    sys.exit(1)

print(f"Input AIS        : {settings['UDP_IP']}:{settings['UDP_PORT']}", file=sys.stderr)
print(f"Output SBS       : {settings['SERVER_IP']}:{settings['SERVER_PORT']}", file=sys.stderr)
print(f"Include ships    : {settings['includeShips']}", file=sys.stderr)
print(f"Include callsign : {settings['includeCallSign']}", file=sys.stderr)
print(f"Print Dictionary : {settings['printDict']}", file=sys.stderr)

connectClient()

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((settings['UDP_IP'], settings['UDP_PORT']))

next_update_time = time.monotonic() + 10
count  = 0
sent = 0

while True:
    data, addr = sock.recvfrom(1024)  
    nmea = data.decode()
    # Does not handle multi-part messages which I am skipping for now
    # Should not be an issue for SAR
    try:
        decoded = decode(nmea).asdict()
    except pyais.exceptions.MissingMultipartMessageException as e:
        continue

    if decoded['msg_type']==9 or settings['includeShips'] or (decoded['mmsi'] in ICAOmap):
        sendBaseStation(decoded)
        count = count + 1

    if time.monotonic() >= next_update_time:
        t = time.strftime('%Y-%m-%d %H:%M:%S')
        print(f'{t} Messages sent: {sent}/{count}')
        if settings['printDict']:
            printDictionary()

        count = 0
        sent = 0
        next_update_time += 10
        
client_socket.close()