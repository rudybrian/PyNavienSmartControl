#!/usr/bin/env python

# Support Python3 in Python2.
from __future__ import print_function

# The NavienSmartControl code is in a library.
from shared.NavienSmartControl import NavienSmartControl

# Import select enums from the NavienSmartControl library
from shared.NavienSmartControl import DeviceSorting

# The credentials are loaded from a separate file.
import json

import binascii

# Load credentials.
with open("credentials.json", "r") as in_file:
    credentials = json.load(in_file)

# Create a reference to the NavienSmartControl library.
navienSmartControl = NavienSmartControl(
    credentials["Username"], credentials["Password"]
)

# Perform the login and get the list of gateways
gateways = navienSmartControl.login()

for i in range(len(gateways)):
    # Print out the gateway list information.
    print("---------------------------")
    print("Device ID: " + gateways[i]["GID"])
    print("Nickname: " + gateways[i]["NickName"])
    print("State: " + gateways[i]["State"])
    print("Connected: " + gateways[i]["ConnectionTime"])
    print("Server IP Address: " + gateways[i]["ServerIP"])
    print("Server TCP Port Number: " + gateways[i]["ServerPort"])
    print("---------------------------\n")

    # Connect to the socket.
    channelInfo = navienSmartControl.connect(gateways[i]["GID"])

    # Print the channel info
    navienSmartControl.printChannelInformation(channelInfo)

    print()
    # Request the state for each connected device
    for chan in channelInfo:
        if (
            DeviceSorting(channelInfo[chan].deviceSorting).name
            != DeviceSorting.NO_DEVICE.name
        ):
            print("Channel " + chan + " Info:")
            for deviceNumber in range(1, channelInfo[chan].deviceCount + 1):
                print("Device: " + str(deviceNumber))
                state = navienSmartControl.sendStateRequest(
                    binascii.unhexlify(gateways[i]["GID"]), int(chan), deviceNumber
                )

                # Print out the current state
                navienSmartControl.printState(state, channelInfo[chan].deviceTempFlag)

# Change the temperature.
# navienSmartControl.setInsideHeat(homeState, 19.0)
