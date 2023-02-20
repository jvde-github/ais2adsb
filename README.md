# ais2adsb

This  Python script converts AIS nmea lines to BaseStation format so it can be read by programs like Virtual Radar Server (VRS). Main purpose is to plot data on SAR aircraft picked up by AIS receivers in ADSB plotting software.  The program reads AIS messages coming in as NMEA lines over UDP and sends out ADS-B messages in BaseStation [format](http://woodair.net/sbs/article/barebones42_socket_data.htm) to a server. 

The following is an example of a SAR helicopter broadcasting AIS messages plotted in Virtual Radar Server where reception of AIS is better (courtesy of jonboy1081):

And plotted using the ADS-B data:


## Usage
```
Usage: (python) ais2adsb.py <AIS UDP address> <AIS UDP port> <BS server address> <BS server port> <options>
Options:
	FILE xxxx        : read mmsi <-> ICAO mapping from file xxxx
	SHIPS on/off     : include ships in sendout
	CALLSIGN on/off  : include generated callsigns in sendout
	PRINT on/off     : print mmsi/ICAO dictionary

```
This is the minimal command line:
```
python ./ais2adsb.py 192.168.1.235 4002 192.168.1.239 30003
```
which reads AIS messages coming in on a computer with IP address `192.168.1.235` and port 4002 and sends it to a Virtual Radar Server running at `192.168.1.239` port 30003. Below some more instructions to set up.

There are only a few options. The `FILE` setting will read in a file with a Python Dictionary that maps MMSI numbers to 24-bit ICAO numbers. The Dictionary functionality allows the user to let the program use a pre-defined mapping.  If not provided AIS2ADSB will auto generate ICAO numbers of the form `FXXXXX`  based on the MMSI number or from a default dictionary embedded in the program (courtesy of jonboy1081). The `PRINT on` option will trigger dumping the Dictionary to stderr periodically (so it can be put back in via the FILE option if desired)

The SHIPS setting (on/off, default is off) will instruct the program to also include vessels in the sendout. By default only SAR Aircraft broadcasting AIS message type 9 are included. A callsign based on MMSI will be included by default, unless the option `CALLSIGN off` is given. A full example is:
```
python ./ais2adsb.py 192.168.1.235 4002 192.168.1.239 30003 SHIPS on FILE mapping.dict PRINT on CALLSIGN off
```

## Installation

For Windows users who do not have Python installed there is a package available in the Release sections created via [pyinstaller](https://pyinstaller.org/en/stable/). 
In general simplest is to install Python3 and pyais (if not already installed):
```
sudo apt install python3
pip install pyais
```
Then download this package and enter the directory:
```
git clone https://github.com/jvde-github/ais2adsb.git
cd ais2adsb
```

Set up for example VRS so that it can receive BaseStation messages as a TCP server:
<img width="659" alt="image" src="https://user-images.githubusercontent.com/52420030/219872223-2d199476-94e4-467c-9943-3cab66e48c4a.png">

The NMEA input should be send over UDP. Most AIS software including AIS-catcher can easily be set up to achieve this. For now we will assume you will have a stream of messages send to the local computer (say `192.168.1.235` at port `4002`). To create BaseStation messages and send to the server use the following command:
```
python ./ais2adsb.py 192.168.1.235 4002 192.168.1.239 30003
```
where `192.168.1.239` is the PC running VRS.

This will only pass on SAR aircraft messages. For testing it could be interesting to pass on ship positions as well:
```
python ./ais2adsb.py 192.168.1.235 4002 192.168.1.239 30003 1
```
You will see in the VRS main window that the client has connected and hopefully some messages:
<img width="552" alt="image" src="https://user-images.githubusercontent.com/52420030/219874149-dd0458dd-d804-4fde-9f2e-cf7812f58d3c.png">

Illustration of plotting ships in VRS:
<img width="1232" alt="image" src="https://user-images.githubusercontent.com/52420030/219868349-5b1dc1e5-33b1-48a0-96a4-9ad4bb49134f.png">

## To do
- Fine tuning the Basestation messages (as I learn more about ADSB and the software)
- ....
