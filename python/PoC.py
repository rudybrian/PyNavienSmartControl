#!/usr/bin/env python

# Support Python3 in Python2.
from __future__ import print_function

# The NavienSmartControl code is in a library.
from shared.NavienSmartControl import NavienSmartControl

# Import select enums from the NavienSmartControl library
from shared.NavienSmartControl import DeviceSorting
from shared.NavienSmartControl import OnOFFFlag
from shared.NavienSmartControl import DayOfWeek

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
    print("Gateway List")
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
    print("Channel Info")
    print("---------------------------")
    navienSmartControl.printChannelInformation(channelInfo)
    print("---------------------------\n")

    print()
    # Request the info for each connected device
    for chan in channelInfo:
        if (
            DeviceSorting(channelInfo[chan].deviceSorting).name
            != DeviceSorting.NO_DEVICE.name
        ):
            print("Channel " + chan + " Info:")
            for deviceNumber in range(1, channelInfo[chan].deviceCount + 1):
                # Request the current state
                print("Device: " + str(deviceNumber))
                state = navienSmartControl.sendStateRequest(
                    binascii.unhexlify(gateways[i]["GID"]), int(chan), deviceNumber
                )

                # Print out the current state
                print("State")
                print("---------------------------")
                navienSmartControl.printState(state, channelInfo[chan].deviceTempFlag)
                print("---------------------------\n")

                # Request the trend sample data
                trendSample = navienSmartControl.sendTrendSampleRequest(
                    binascii.unhexlify(gateways[i]["GID"]), int(chan), deviceNumber
                )

                # Print out the trend sample data
                print("Trend Sample")
                print("---------------------------")
                navienSmartControl.printTrendSample(
                    trendSample, channelInfo[chan].deviceTempFlag
                )
                print("---------------------------\n")

                # Request the trend month data
                trendMonth = navienSmartControl.sendTrendMonthRequest(
                    binascii.unhexlify(gateways[i]["GID"]), int(chan), deviceNumber
                )

                # Print out the trend month data
                print("Trend Month")
                print("---------------------------")
                navienSmartControl.printTrendMY(
                    trendMonth, channelInfo[chan].deviceTempFlag
                )
                print("---------------------------\n")

                # Request the trend year data
                trendYear = navienSmartControl.sendTrendYearRequest(
                    binascii.unhexlify(gateways[i]["GID"]), int(chan), deviceNumber
                )

                # Print out the trend year data
                print("Trend Year")
                print("---------------------------")
                navienSmartControl.printTrendMY(
                    trendYear, channelInfo[chan].deviceTempFlag
                )
                print("---------------------------\n")

                ## Turn the power off
                # print("Turn the power off")
                # state = navienSmartControl.sendPowerControlRequest(
                #     binascii.unhexlify(gateways[i]["GID"]),
                #     int(chan),
                #     deviceNumber,
                #     OnOFFFlag.OFF.value
                # )

                ## Turn the power on
                # print("Turn the power on")
                # state = navienSmartControl.sendPowerControlRequest(
                #     binascii.unhexlify(gateways[i]["GID"]),
                #     int(chan),
                #     deviceNumber,
                #     OnOFFFlag.ON.value,
                # )

                ## Turn heat on
                # print("Turn heat on")
                # state = navienSmartControl.sendHeatControlRequest(
                #     binascii.unhexlify(gateways[i]["GID"]),
                #     int(chan),
                #     deviceNumber,
                #     OnOFFFlag.ON.value,
                # )

                ## Turn on on demand (equivalent of pressing HotButton)
                # print("Turn on on-demand")
                # state = navienSmartControl.sendOnDemandControlRequest(
                #     binascii.unhexlify(gateways[i]["GID"]),
                #     int(chan),
                #     deviceNumber,
                # )

                ## Turn weekly schedule on
                # print("Turn weekly schedule on")
                # state = navienSmartControl.sendDeviceWeeklyControlRequest(
                #     binascii.unhexlify(gateways[i]["GID"]),
                #     int(chan),
                #     deviceNumber,
                #     OnOFFFlag.ON.value,
                # )

                ## Set the water temperature to 125
                # tempToSet = 125
                # print("Set the water temperature to " + str(tempToSet))
                # state = navienSmartControl.sendWaterTempControlRequest(
                #     binascii.unhexlify(gateways[i]["GID"]),
                #     int(chan),
                #     deviceNumber,
                #     tempToSet,
                # )

                ## Set the device heating water temperature to 125
                # tempToSet = 125
                # print("Set the water temperature to " + str(tempToSet))
                # state = navienSmartControl.sendHeatingWaterTempControlRequest(
                #     binascii.unhexlify(gateways[i]["GID"]),
                #     int(chan),
                #     deviceNumber,
                #     tempToSet,
                # )

                ## Set the recirculation temperature to 125
                # tempToSet = 125
                # print("Set the water temperature to " + str(tempToSet))
                # state = navienSmartControl.sendRecirculationTempControlRequest(
                #     binascii.unhexlify(gateways[i]["GID"]),
                #     int(chan),
                #     deviceNumber,
                #     tempToSet,
                # )

                WeeklyDay = {
                    "dayOfWeek": DayOfWeek.SUN.value,
                    "hour": 1,  # 1AM
                    "minute": 20,  # 20 minutes past the hour (01:20)
                    "isOnOFF": OnOFFFlag.OFF.value,  # turn off
                }

                ## Add an entry to the weekly schedule
                # print("Add an entry to the weekly schedule")
                # state = navienSmartControl.sendDeviceControlWeeklyScheduleRequest(
                #     state,
                #     WeeklyDay,
                #     "add"
                # )

                ## Delete an entry from the weekly schedule
                # print("Delete an entry from the weekly schedule")
                # state = navienSmartControl.sendDeviceControlWeeklyScheduleRequest(
                #     state,
                #     WeeklyDay,
                #     "delete"
                # )

                ## Print out the current state
                # print("State")
                # print("---------------------------")
                # navienSmartControl.printState(state, channelInfo[chan].deviceTempFlag)
                # print("---------------------------\n")
