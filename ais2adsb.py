#!/usr/bin/python3

# Copyright (c) 2023 jvde.github@gmail.com and jonboy1081

import socket
import signal
import pyais
from pyais import decode
import pyais.exceptions
import ast
import time
from datetime import datetime
import sys

ICAOmap = { 111232512:0x406C79, 111232511:0x406C82, 111232513:0x406C8E, 111232516:0x406D2C, 111232517:0x406D2D, 111232523:0x406DDB, 111232524:0x406DDC, 111232529:0x406F8B, 111232526:0x406EE7,
            111232528:0x406F2D, 111232518:0x406D21, 111232533:0x406DE5, 111232522:0x406DE6, 111232527:0x406DE7, 111232525:0x406DE8, 111232534:0x406DE9, 111232535:0x406DEA,111232537:0x406DEB,
            111232539:0x406DED, 111232531:0x43ECF4, 250002898:0x4CA98D, 250002897:0x4CA98F, 250002902:0x4CA98B, 250004879:0x4CACA4, 250002901:0x4CA98C, 111232519:0x48644B,111232538:0x485F8F,
            111503003:0x4860B1, 111232509:0x47BFE4, 111265103:0x4AB423, 111224519:0x346105, 111503031:0x7C7590, 111257008:0x47812B, 111257014:0x478131, 111247506:0x32001B,
            111211507:0x3DF1AD, 111224518:0x34220D, 11120554:0x44B918, 111224504:0x343318, 831582013:0x33FD3F, 111224522:0x346401, 111224520:0x3462C3,  111224505:0x343619,
            111211512:0x3DF3B7, 111224509:0x343318, 111224521:0x3462CC, 111224503:0x3430CA, 111247102:0x320013,
            111247103:0x32000C, 111503024:0x7C7646, 111257603:0x478777,111277501:0x503FDA, 111257001:0x478124,
            111265586:0x4AAA4D, 111219510:0x45F434, 111219508:0x45F432, 111265582:0x4AAA49, 111224501:0x3430C8,
            2366:0x32001A, 31941:0x33FD3C, 111265584:0x4AAA4B, 111224102:0x342555, 1037:0x342697,
            111257507:0x47A6BC,  111503027:0x7C7647, 111257013:0x478130,111257012:0x47812F, 111257011:0x47C19E,
            111224508:0x343550, 111265581:0x4AAA48, 111257011:0x47812E, 111257509:0x47C19E, 111257506:0x47A711,
            111257002:0x478125, 111257010:0x47812D, 111265585:0x4AAA4C, 111257512:0x479C74, 111244515:0x486449,
            41541:0x0D0B2B, 111257005:0x478128, 111224101:0x2AA42C, 111257007:0x47812A, 1001:0x320037,
            111224507:0x34354F, 111224516:0x345542, 111257004:0x478127, 31940:0x33FD3D, 31937:0x320056,
            1125:0x320059, 100046:0x478056, 111219512:0x45F436,111277502:0x503FDB,111211504:0x3DDDDF,
            111257123:0x479EDE, 1190:0x342693, 111224502:0x342556, 2287:0x7C44C8, 338060099:0x8A066A,
            100026:0x479E84, 111247509:0x32001D, 100265:0x320041, 111247508:0x33FDBF, 111247524:0x320027, 111247199:0x33FDD0,
            111247200:0x33FDB3, 2187:0x4D20C3, 2281:0x4D20DE, 100232:0x382CFA, 1111:0x32005E,
            111211514:0x3DDDDD, 111211510:0x3DF1AA, 111224517:0x34220E, 111257006:0x478129,
            111276002:0x5110FA, 2228:0x47B858, 2380:0xE494F3,  2209:0x382CBA, 1000:0x32003F, 100118:0x7C2AB5, 111211509:0x3DF1AC,111244514:0x485F8F,
            831581990:0x33FD4A, 111440540:0x71D870, 111257009:0x47812C, 111257511:0x479C60, 111244513:0x48644B, 2143:0x353542,
            111211501:0x3DDDDC, 111247533:0x32004E, 111265102:0x4AB422, 111265101:0x4AB421, 111247510:0x32001E,
            111261507:0x48DA8F, 111265583:0x4AAA4A
          }

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
    print("Usage: (python) ais2adsb.py <AIS UDP address> <AIS UDP IP> <AIS UDP port> <SBS TCP IP> <SBS TCP port> <options>")
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
    except:
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
