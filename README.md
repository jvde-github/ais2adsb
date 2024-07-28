# ais2adsb

This  Python script converts AIS NMEA lines received over UDP to BaseStation [format](http://woodair.net/sbs/article/barebones42_socket_data.htm) and sends it to a specified server e.g. Virtual Radar Server (VRS). Main purpose is to plot data on SAR aircraft picked up by AIS receivers in ADS-B plotting software.  The following is an example of a SAR helicopter broadcasting AIS messages plotted in VRS using AIS messages converted by ais2adsb (courtesy of jonboy1081):

<img width="251" alt="image" src="https://user-images.githubusercontent.com/52420030/220178667-2196cc3d-be5d-4194-a9c3-8d37ac08f672.png">

And plotted using the ADS-B data:

<img width="251" alt="image" src="https://user-images.githubusercontent.com/52420030/220178717-199a5d36-ae7e-4d50-9ef8-931759c1085a.png">

This is a nice example where sometimes AIS has better reception than ADS-B. The idea for this tool came from [flygfantast](https://github.com/jvde-github/AIS-catcher/discussions/73) and jonboy1081.

## Usage
```
AIS2ADSB v0.14- see https://github.com/jvde-github/ais2adsb
Usage: (python) ais2adsb.py <AIS UDP address> <AIS UDP IP> <AIS UDP port> <SBS TCP IP> <SBS TCP port> <options>
Options:
	FILE xxxx        : read mmsi <-> ICAO mapping from file xxxx
	SAR on/off       : include SAR aircraft in sendout
	SHIPS on/off     : include ships in sendout
	CALLSIGN on/off  : include generated callsigns in sendout
	PRINT on/off     : print mmsi/ICAO dictionary
	SAVE xxxx        : save mmsi/ICAO dictionary to file xxxx
```
This is the minimal command line:
```
python3 ./ais2adsb.py 192.168.1.235 4002 192.168.1.239 30003
```
which reads AIS messages coming in on a computer with IP address `192.168.1.235` and port 4002 and sends it to VRS running at `192.168.1.239` port 30003. Below some more instructions to set up.

As a side note, if your receiver is AIS-catcher, you can send it to ais2adsb using the `-u` option:
```
AIS-catcher -u 192.168.1.235 4002 .....
```

There are only a few options. The `FILE` setting will read in a file with a Python Dictionary that maps MMSI numbers to 24-bit ICAO numbers. The Dictionary functionality allows the user to let the program use a pre-defined mapping.  If not provided ais2adsb will auto generate ICAO numbers of the form `FXXXXX`  based on the MMSI number or from a default dictionary embedded in the program. The `PRINT on` option will trigger dumping the Dictionary to stderr periodically (so it can be put back in via the FILE option if desired)

The SAR setting (on/off, default is on) will instruct the program to also include SAR aircraft in the sendout. By default only SAR Aircraft broadcasting AIS message type 9 are included. The SHIPS setting (on/off, default is off) will instruct the program to also include vessels in the sendout. A callsign based on MMSI will be included by default, unless the option `CALLSIGN off` is given. A full example is:
```
python3 ./ais2adsb.py 192.168.1.235 4002 192.168.1.239 30003 SHIPS on FILE mapping.dict PRINT on CALLSIGN off
```

## Installation

For Windows users who do not have Python installed there is a package available in the Release sections created via [pyinstaller](https://pyinstaller.org/en/stable/). 
Usually it is simplest though to install Python3 and pyais (if not already installed):
```
sudo apt install python3 pip
pip3 install pyais
```
Then download the current package and enter the directory:
```
git clone https://github.com/jvde-github/ais2adsb.git
cd ais2adsb
```

Set up for example VRS so that it can receive BaseStation messages as a TCP server:
<img width="659" alt="image" src="https://user-images.githubusercontent.com/52420030/219872223-2d199476-94e4-467c-9943-3cab66e48c4a.png">

The NMEA input should be send over UDP. Most AIS software including AIS-catcher can easily be set up to achieve this, see above. For now we will assume you will have a stream of messages send to the local computer (say `192.168.1.235` at port `4002`). To create BaseStation messages and send to the server use the following command:
```
python3 ./ais2adsb.py 192.168.1.235 4002 192.168.1.239 30003
```
where `192.168.1.239` is the PC running VRS.

This will only pass on SAR aircraft messages. For testing it could be interesting to pass on ship positions as well:
```
python3 ./ais2adsb.py 192.168.1.235 4002 192.168.1.239 30003 SHIPS on
```
You will see in the VRS main window that the client has connected and hopefully some messages have been sent as well:
<img width="552" alt="image" src="https://user-images.githubusercontent.com/52420030/219874149-dd0458dd-d804-4fde-9f2e-cf7812f58d3c.png">

The final output in the webinterface of VRS will look something like:
<img width="1232" alt="image" src="https://user-images.githubusercontent.com/52420030/219868349-5b1dc1e5-33b1-48a0-96a4-9ad4bb49134f.png">

## Default dictionary

The default MMSI to ICAO mapping is shown below which is kindly provided by jonboy1081 and flygfantast. This is also the input format when reading in a dictionary from file: 
```
{ 111232512:0x406C79, 111232511:0x406C82, 111232513:0x406C8E, 111232516:0x406D2C, 111232517:0x406D2D, 111232523:0x406DDB, 111232524:0x406DDC, 111232529:0x406F8B, 111232526:0x406EE7,
            111232528:0x406F2D, 111232518:0x406D21, 111232533:0x406DE5, 111232522:0x406DE6, 111232527:0x406DE7, 111232525:0x406DE8, 111232534:0x406DE9, 111232535:0x406DEA,111232537:0x406DEB,
            111232539:0x406DED, 111232531:0x43ECF4, 250002898:0x4CA98D, 250002897:0x4CA98F, 250002902:0x4CA98B, 250004879:0x4CACA4, 250002901:0x4CA98C, 111232519:0x48644B,111232538:0x485F8F,
            111503003:0x4860B1, 111232509:0x47BFE4, 111265103:0x4AB423, 111224519:0x346105, 111503031:0x7C7590, 111257008:0x47812B, 111257014:0x478131, 111247506:0x32001B,
            111211507:0x3DF1AD, 111224518:0x34220E, 11120554:0x44B918, 111224504:0x343318, 831582013:0x33FD3F, 111224522:0x346401 }
```
## To do
- Fine tuning
- Integrate into other software
- ....
