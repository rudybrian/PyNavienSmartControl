#!/usr/bin/env python

# Support Python3 in Python2.
from __future__ import print_function

# The NavienSmartControl code is in a library.
from shared.NavienSmartControl import NavienSmartControl, OperateMode

# The credentials are loaded from a separate file.
import json

# Load credentials.
with open('credentials.json', 'r') as in_file:
 credentials = json.load(in_file)

# Create a reference to the NavienSmartControl library.
navienSmartControl = NavienSmartControl(credentials['Username'], credentials['Password'])

# Perform the login.
encodedUserID = navienSmartControl.login()

# Load the list of devices connected.
gatewayList = navienSmartControl.gatewayList(encodedUserID)

# The first 6 bytes is the MAC address.
if len(gatewayList[0]) == 16:
 print('Serial Number: ' + gatewayList[0])
 print('Ready?: ' + gatewayList[1])
 print('2: ' + gatewayList[2])
 print('Connected: ' + gatewayList[3])
 print('Last Seen: ' + gatewayList[4])
 print('5: ' + gatewayList[5])
 print('6: ' + gatewayList[6])
 print('7: ' + gatewayList[7])
 print('IP Address: ' + gatewayList[8])
 print('TCP Port Number: ' + gatewayList[9])
 print()

 # Connect to the socket.
 homeState = navienSmartControl.connect(gatewayList[0])

 # Print out the status.
 navienSmartControl.printHomeState(homeState)

 # Change temperature.
 #navienSmartControl.setInsideHeat(homeState, 19.0)

else:
 raise ValueError('Bad gateway list returned.')