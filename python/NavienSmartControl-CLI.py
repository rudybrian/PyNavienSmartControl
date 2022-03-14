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
        description="Control a Navien tankless water heater, combi-boiler or boiler connected via NaviLink.",
        prefix_chars="-/",
    )
    parser.add_argument(
        "-gatewayid",
        help="Specify gatewayID (required when multiple gateways are used)",
    )
    parser.add_argument(
        "-channel",
        type=int,
        help="Specify channel (required when multiple channels are used)",
    )
    parser.add_argument(
        "-devicenumber",
        type=int,
        help="Specify device number (required when multiple devices on a common channel are used)",
    )
    parser.add_argument(
        "-recirctemp", type=int, help="Set the recirculation temperature to this value."
    )
    parser.add_argument(
        "-heatingtemp",
        type=int,
        help="Set the central heating temperature to this value.",
    )
    parser.add_argument(
        "-hotwatertemp", type=int, help="Set the hot water temperature to this value."
    )
    parser.add_argument(
        "-power", choices={"on", "off"}, help="Turn the power on or off."
    )
    parser.add_argument("-heat", choices={"on", "off"}, help="Turn the heat on or off.")
    parser.add_argument("-ondemand", action="store_true", help="Trigger On Demand.")
    parser.add_argument(
        "-schedule",
        choices={"on", "off"},
        help="Turn the weekly recirculation schedule on or off.",
    )
    parser.add_argument(
        "-summary", action="store_true", help="Show the device's extended status."
    )
    parser.add_argument(
        "-trendsample",
        action="store_true",
        help="Show the device's trend sample report.",
    )
    parser.add_argument(
        "-trendmonth", action="store_true", help="Show the device's trend month report."
    )
    parser.add_argument(
        "-trendyear", action="store_true", help="Show the device's trend year report."
    )
    parser.add_argument(
        "-updateschedule",
        help="Update recirculation schedule for given time, day and state",
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

        myGatewayID = 0
        # If a gateway is specified, make sure it is in the list
        if args.gatewayid:
            foundGateway = False
            for i in range(len(gateways)):
                if args.gatewayid == gateways[i]["GID"]:
                    myGatewayID = i
                    foundGateway = True
                    break
            if not foundGateway:
                raise ValueError("No such gatewayID " + args.gatewayid)
        elif len(gateways) > 1:
            if not args.summary:
                raise ValueError(
                    "Must specify gatewayID when more than one is available. View summary to see list of gatewayIDs."
                )

        myChannel = 1
        # If a channel is specified, ensure that it has a device connected
        channelInfo = navienSmartControl.connect(gateways[myGatewayID]["GID"])
        channels = 0
        if args.channel:
            if (
                DeviceSorting(
                    channelInfo["channel"][str(args.channel)]["deviceSorting"]
                ).name
                == DeviceSorting.NO_DEVICE.name
            ):
                raise ValueError(
                    "No device detected on channel "
                    + str(args.channel)
                    + " on gatewayID "
                    + gateways[myGatewayID]["GID"]
                )
            else:
                myChannel = str(args.channel)
                channels = 1
        else:
            # No channel is specified, so find the one that has a device connected if any
            foundChannel = False
            for chan in channelInfo["channel"]:
                if (
                    DeviceSorting(channelInfo["channel"][chan]["deviceSorting"]).name
                    != DeviceSorting.NO_DEVICE.name
                ):
                    myChannel = chan
                    if foundChannel:
                        if not args.summary:
                            raise ValueError(
                                "Must specify channel when more than one device is connected. View summary to see list of devicenumbers."
                            )
                    foundChannel = True
                    channels += channels
            if not foundChannel:
                raise ValueError(
                    "No device detected on any channel on gatewayID "
                    + gateways[myGatewayID]["GID"]
                )

        myDeviceNumber = 1
        # If a devicenumber is specified, make sure it is present
        if args.devicenumber:
            if args.devicenumber > channelInfo["channel"][myChannel]["deviceCount"]:
                raise ValueError(
                    "Devicenumber "
                    + str(args.devicenumber)
                    + " not found on channel "
                    + str(myChannel)
                    + " on gatewayID "
                    + gateways[myGatewayID]["GID"]
                )
            else:
                myDeviceNumber = args.devicenumber
        elif channelInfo["channel"][myChannel]["deviceCount"] > 1:
            if not args.summary:
                raise ValueError(
                    "Must specify devicenumber when more than one is available. View summary to see list of devicenumbers."
                )

        print(
            "GatewayID: "
            + str(myGatewayID)
            + ", channel: "
            + str(myChannel)
            + ", deviceNumber:"
            + str(myDeviceNumber)
        )

        # We can provide a full summary.
        if args.summary:
            if (len(gateways) > 1) and (not args.gatewayid):
                # There is more than one gateway, and no gateway was specified, print all the gateways
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
                print("Specify a gateway to view channel details.")

            else:
                print("---------------------------")
                print("Device ID: " + gateways[myGatewayID]["GID"])
                print("Nickname: " + gateways[myGatewayID]["NickName"])
                print("State: " + gateways[myGatewayID]["State"])
                print("Connected: " + gateways[myGatewayID]["ConnectionTime"])
                print("Server IP Address: " + gateways[myGatewayID]["ServerIP"])
                print("Server TCP Port Number: " + gateways[myGatewayID]["ServerPort"])
                print("---------------------------\n")

                # Print the channel info
                print("Channel Info")
                print("---------------------------")
                navienSmartControl.printResponseHandler(channelInfo, 0)
                print("---------------------------\n")

                print()
                if (channels > 1) and (not args.channel):
                    print("Specify a channel to view device details.")
                else:
                    if (
                        DeviceSorting(
                            channelInfo["channel"][myChannel]["deviceSorting"]
                        ).name
                        != DeviceSorting.NO_DEVICE.name
                    ):
                        print("Channel " + str(myChannel) + " Info:")
                        for deviceNumber in range(
                            1, channelInfo["channel"][myChannel]["deviceCount"] + 1
                        ):
                            # Request the current state
                            print("Device: " + str(deviceNumber))
                            state = navienSmartControl.sendStateRequest(
                                binascii.unhexlify(gateways[myGatewayID]["GID"]),
                                int(myChannel),
                                deviceNumber,
                            )

                            # Print out the current state
                            print("State")
                            print("---------------------------")
                            navienSmartControl.printResponseHandler(
                                state,
                                channelInfo["channel"][myChannel]["deviceTempFlag"],
                            )
                            print("---------------------------\n")
                            if (
                                channelInfo["channel"][myChannel]["deviceCount"] > 1
                            ) and (not args.devicenumber):
                                print(
                                    "Specify a devicenumber to select a specific device."
                                )
                    else:
                        raise ValueError(
                            "No device detected on channel " + str(myChannel)
                        )
            print()

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
