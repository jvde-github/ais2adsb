# ais2adsb


This simple python scripts converts AIS nmea lines to BaseStation format so it can be read by programs like Virtual Radar Server (VRS). Main purpose is to plot data on SAR aircraft picked up by AIS receivers in ADSB plotting software.

To use, you need to install Python3 and:
```
pip install pyais
```
The input is NMEA input over UDP that most AIS-software can deal with. For this I assume you will have a stream of messages send to the local computer (say `192.168.1.235` at port `4002`). To create BaseStation messages and write these to a file `out`, give the following command:
```
python ./ais2adsb.py 192.168.1.235 4002 >out
```
To pass these messages to VRS, set up this computer as receiver in VRS and transfer via `netcat`:
```
cat out | netcat -l 192.168.1.235 30003
```

This will only pass on SAR aircraft messages. For testing it could be interesting to pass on ship positions as well:
```
python ./ais2adsb.py 192.168.1.235 4002 1 >out
```

Illustration of plotting ships in VRS:
<img width="1232" alt="image" src="https://user-images.githubusercontent.com/52420030/219868349-5b1dc1e5-33b1-48a0-96a4-9ad4bb49134f.png">

To do:
- Include TCP socket in program so runs on Windows
- Fine tuning the Basestation messages (as I learn more about ADSB and the software)
- A lot....
