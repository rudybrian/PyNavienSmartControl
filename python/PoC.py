#!/usr/bin/env python

# Support Python3 in Python2.
from __future__ import print_function

# The NavienSmartControl code is in a library.
from shared.NavienSmartControl import NavienSmartControl

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

# The first 16 characters (8 bytes represented as hex characters) is the DeviceID (only seen with a valid response).
if len(gatewayList[0]) == 16:

 # Print out the gateway list information.
 print('---------------------------')
 print('Device ID: ' + gatewayList[0])
 print('Ready?: ' + gatewayList[1])
 print('Unknown 1: ' + gatewayList[2])
 print('Connected: ' + gatewayList[3])
 print('Last Seen: ' + gatewayList[4])
 print('Unknown 2-4: ' + gatewayList[5] + '/' + gatewayList[6] + '/' + gatewayList[7])
 print('IP Address: ' + gatewayList[8])
 print('TCP Port Number: ' + gatewayList[9])
 print('---------------------------\n')

 # Connect to the socket.
 homeState = navienSmartControl.connect(gatewayList[0])

 # Print out the current status.
 navienSmartControl.printHomeState(homeState)

 # Change the temperature.
 #navienSmartControl.setInsideHeat(homeState, 19.0)

else:
 raise ValueError('Bad gateway list returned.')