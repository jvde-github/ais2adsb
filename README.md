# ais2adsb


This simple python scripts converts AIS nmea lines to BaseStation format so it can be read by programs like Virtual Radar Server (VRS). Main purpose is to plot data on SAR aircraft picked up by AIS receivers in ADSB plotting software.

To use, you need to install Python3 and:
```
pip install pyais
```
Set up VRS so that it can receive BaseStation as a TCP server:
<img width="659" alt="image" src="https://user-images.githubusercontent.com/52420030/219872223-2d199476-94e4-467c-9943-3cab66e48c4a.png">


The input is NMEA input over UDP that most AIS-software can deal with. For this I assume you will have a stream of messages send to the local computer (say `192.168.1.235` at port `4002`). To create BaseStation messages and send to the server use the following command:
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

To do:
- Fine tuning the Basestation messages (as I learn more about ADSB and the software)
- A lot....
