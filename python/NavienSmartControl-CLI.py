#!/usr/bin/env python

# Support Python3 in Python2.
from __future__ import print_function

# The NavienSmartControl code is in a library.
from shared.NavienSmartControl import (
    NavienSmartControl,
    DeviceSorting,
    OnOFFFlag,
    DayOfWeek,
)

# The credentials are loaded from a separate file.
import json

# We support command line arguments.
import argparse

# We use the system package for interaction with the OS.
import sys

# We need to convert between human readable and raw hex forms of the ID
import binascii

# This script's version.
version = 1.0

# Check the user is invoking us directly rather than from a module.
if __name__ == "__main__":

    # Output program banner.
    print("--------------")
    print("Navien-API V" + str(version))
    print("--------------")
    print()

    # Get an initialised parser object.
    parser = argparse.ArgumentParser(
        description="Control a Navien boiler.", prefix_chars="-/"
    )
    parser.add_argument(
        "/roomtemp",
        "-roomtemp",
        type=float,
        help="Set the indoor room temperature to this value.",
    )
    parser.add_argument(
        "/heatingtemp",
        "-heatingtemp",
        type=float,
        help="Set the central heating temperature to this value.",
    )
    parser.add_argument(
        "/hotwatertemp",
        "-hotwatertemp",
        type=float,
        help="Set the hot water temperature to this value.",
    )
    parser.add_argument(
        "/heatlevel",
        "-heatlevel",
        type=int,
        choices={1, 2, 3},
        help="Set the boiler's heat level.",
    )
    parser.add_argument(
        "/status",
        "-status",
        action="store_true",
        help="Show the boiler's simple status.",
    )
    parser.add_argument(
        "/summary",
        "-summary",
        action="store_true",
        help="Show the boiler's extended status.",
    )
    parser.add_argument(
        "/mode",
        "-mode",
        choices={
            "PowerOff",
            "PowerOn",
            "HolidayOn",
            "HolidayOff",
            "SummerOn",
            "SummerOff",
            "QuickHotWater",
        },
        help="Set the boiler's mode.",
    )

    # The following function provides arguments for calling functions when command line switches are used.
    args = parser.parse_args()

    # Were arguments specified?
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)

    # Yes, there was.
    else:

        # Load credentials.
        with open("credentials.json", "r") as in_file:
            credentials = json.load(in_file)

        # Create a reference to the NavienSmartControl library.
        navienSmartControl = NavienSmartControl(
            credentials["Username"], credentials["Password"]
        )

        # Perform the login.
        gateways = navienSmartControl.login()

        # We can provide a full summary.
        if args.summary:
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
                print("Channel Info")
                print("---------------------------")
                navienSmartControl.printResponseHandler(channelInfo, 0)
                print("---------------------------\n")

                print()
                # Request the info for each connected device
                for chan in channelInfo["channel"]:
                    if (
                        DeviceSorting(
                            channelInfo["channel"][chan]["deviceSorting"]
                        ).name
                        != DeviceSorting.NO_DEVICE.name
                    ):
                        print("Channel " + chan + " Info:")
                        for deviceNumber in range(
                            1, channelInfo["channel"][chan]["deviceCount"] + 1
                        ):
                            # Request the current state
                            print("Device: " + str(deviceNumber))
                            state = navienSmartControl.sendStateRequest(
                                binascii.unhexlify(gateways[i]["GID"]),
                                int(chan),
                                deviceNumber,
                            )

                            # Print out the current state
                            print("State")
                            print("---------------------------")
                            navienSmartControl.printResponseHandler(
                                state, channelInfo["channel"][chan]["deviceTempFlag"]
                            )
                            print("---------------------------\n")

            print()

        # We provide a quick status.
        if args.status:

            print("Current Mode: ", end="")
            if homeState.currentMode == ModeState.POWER_OFF.value:
                print("Powered Off")
            elif homeState.currentMode == ModeState.GOOUT_ON.value:
                print("Holiday Mode")
            elif homeState.currentMode == ModeState.INSIDE_HEAT.value:
                print("Room Temperature Control")
            elif homeState.currentMode == ModeState.ONDOL_HEAT.value:
                print("Central Heating Control")
            elif homeState.currentMode == ModeState.SIMPLE_RESERVE.value:
                print("Heating Inteval")
            elif homeState.currentMode == ModeState.CIRCLE_RESERVE.value:
                print("24 Hour Program")
            elif homeState.currentMode == ModeState.HOTWATER_ON.value:
                print("Hot Water Only")
            else:
                print(str(homeState.currentMode))
            print(
                "Current Operation: "
                + (
                    "Active"
                    if homeState.operateMode & OperateMode.ACTIVE.value
                    else "Inactive"
                )
            )
            print()

            print(
                "Room Temperature : "
                + str(
                    navienSmartControl.getTemperatureFromByte(
                        homeState.currentInsideTemp
                    )
                )
                + " °C"
            )
            print()

            if homeState.currentMode == ModeState.INSIDE_HEAT.value:
                print(
                    "Inside Heating Temperature: "
                    + str(
                        navienSmartControl.getTemperatureFromByte(
                            homeState.insideHeatTemp
                        )
                    )
                    + " °C"
                )
            elif homeState.currentMode == ModeState.ONDOL_HEAT.value:
                print(
                    "Central Heating Temperature: "
                    + str(
                        navienSmartControl.getTemperatureFromByte(
                            homeState.ondolHeatTemp
                        )
                    )
                    + " °C"
                )

            print(
                "Hot Water Set Temperature : "
                + str(
                    navienSmartControl.getTemperatureFromByte(homeState.hotWaterSetTemp)
                )
                + " °C"
            )

        # Change the mode.
        if args.mode:

            # Various allowed mode toggles.
            if args.mode == "PowerOff":
                navienSmartControl.setPowerOff(homeState)
            elif args.mode == "PowerOn":
                navienSmartControl.setPowerOn(homeState)
            elif args.mode == "HolidayOn":
                navienSmartControl.setGoOutOn(homeState)
            elif args.mode == "HolidayOff":
                navienSmartControl.setGoOutOff(homeState)
            elif args.mode == "SummerOn":
                navienSmartControl.setHotWaterOn(homeState)
            elif args.mode == "SummerOff":
                navienSmartControl.setHotWaterOff(homeState)
            elif args.mode == "QuickHotWater":
                navienSmartControl.setQuickHotWater(homeState)

            # Update user.
            print("Mode now set to " + str(args.mode) + ".")

        # Change the heat level.
        if args.heatlevel:
            navienSmartControl.setHeatLevel(homeState, HeatLevel(args.heatlevel))
            print("Heat level now set to " + str(HeatLevel(args.heatlevel)) + ".")

        # Change the room temperature.
        if args.roomtemp:
            navienSmartControl.setInsideHeat(homeState, args.roomtemp)
            print("Indoor temperature now set to " + str(args.roomtemp) + "°C.")

        # Change the central heating system's temperature.
        if args.heatingtemp:
            navienSmartControl.setOndolHeat(homeState, args.heatingtemp)
            print(
                "Central heating temperature now set to "
                + str(args.heatingtemp)
                + "°C."
            )

        # Change the room temperature.
        if args.hotwatertemp:
            navienSmartControl.setHotWaterHeat(homeState, args.hotwatertemp)
            print("Hot water temperature now set to " + str(args.hotwatertemp) + "°C.")
