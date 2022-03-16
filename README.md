# PyNavienSmartControl
Python library for getting information about and controlling your Navien tankless water heater, combi-boiler or boiler connected via NaviLink.

Originally based on [matthew1471/Navien-API](https://github.com/matthew1471/Navien-API/), this module and tools have been completely rewritten to support the current protocols used by mobile applications.

This updated implementation supports individual NPE, NCB, NHB, NFB, NFC, NPN, NPE2. NCB-H, NVW as well as cascaded NPE, NHB, NFB, NPN, NPE2 and NVW device types.

Included with the Python library are two tools: CLI.py and PoC.py.

CLI.py is a commandline tool that can be used interactively or scripted via automation to read and print specific information and provide full control for a specific device.
```
usage: NavienSmartControl-CLI.py [-h] [-gatewayid GATEWAYID]
                                 [-channel CHANNEL]
                                 [-devicenumber DEVICENUMBER]
                                 [-recirctemp RECIRCTEMP]
                                 [-heatingtemp HEATINGTEMP]
                                 [-hotwatertemp HOTWATERTEMP]
                                 [-power {on,off}] [-heat {on,off}]
                                 [-ondemand] [-schedule {on,off}] [-summary]
                                 [-trendsample] [-trendmonth] [-trendyear]
                                 [-modifyschedule {add,delete}]
                                 [-scheduletime SCHEDULETIME]
                                 [-scheduleday {wed,sun,thu,tue,mon,fri,sat}]
                                 [-schedulestate {on,off}]

Control a Navien tankless water heater, combi-boiler or boiler connected via
NaviLink.

optional arguments:
  -h, --help            show this help message and exit
  -gatewayid GATEWAYID  Specify gatewayID (required when multiple gateways are
                        used)
  -channel CHANNEL      Specify channel (required when multiple channels are
                        used)
  -devicenumber DEVICENUMBER
                        Specify device number (required when multiple devices
                        on a common channel are used)
  -recirctemp RECIRCTEMP
                        Set the recirculation temperature to this value.
  -heatingtemp HEATINGTEMP
                        Set the central heating temperature to this value.
  -hotwatertemp HOTWATERTEMP
                        Set the hot water temperature to this value.
  -power {on,off}       Turn the power on or off.
  -heat {on,off}        Turn the heat on or off.
  -ondemand             Trigger On Demand.
  -schedule {on,off}    Turn the weekly recirculation schedule on or off.
  -summary              Show the device's extended status.
  -trendsample          Show the device's trend sample report.
  -trendmonth           Show the device's trend month report.
  -trendyear            Show the device's trend year report.
  -modifyschedule {add,delete}
                        Modify recirculation schedule. Requires scheduletime,
                        scheduleday and schedulestate
  -scheduletime SCHEDULETIME
                        Modify schedule for given time in format HH:MM.
  -scheduleday {wed,sun,thu,tue,mon,fri,sat}
                        Modify schedule for given day of week.
  -schedulestate {on,off}
                        Modify schedule with given state.
```
PoC.py is a test framework that can iterate through all detected gateways and connected devices and demonstrates how to use each function in the module.

Details on the protocol used by the Python module can be found in the [Wiki](https://github.com/rudybrian/PyNavienSmartControl/wiki/Protocol-Decoding)
