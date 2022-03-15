#!/usr/bin/env python

# Support Python3 in Python2.
from __future__ import print_function

# The NavienSmartControl code is in a library.
from shared.NavienSmartControl import (
    NavienSmartControl,
    DeviceSorting,
    OnOFFFlag,
    DayOfWeek,
    ControlType,
    TemperatureType,
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
        "-modifyschedule",
        choices={"add", "delete"},
        help="Modify recirculation schedule. Requires scheduletime, scheduleday and schedulestate",
    )
    parser.add_argument(
        "-scheduletime", help="Modify schedule for given time in format HH:MM."
    )
    parser.add_argument(
        "-scheduleday",
        choices={"sun", "mon", "tue", "wed", "thu", "fri", "sat"},
        help="Modify schedule for given day of week.",
    )
    parser.add_argument(
        "-schedulestate",
        choices={"on", "off"},
        help="Modify schedule with given state.",
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

        myChannel = str(1)
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

        # print(
        #    "GatewayID: "
        #    + str(myGatewayID)
        #    + ", channel: "
        #    + str(myChannel)
        #    + ", deviceNumber:"
        #    + str(myDeviceNumber)
        # )

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
                            channelInfo["channel"][str(myChannel)]["deviceSorting"]
                        ).name
                        != DeviceSorting.NO_DEVICE.name
                    ):
                        print("Channel " + str(myChannel) + " Info:")
                        for deviceNumber in range(
                            1, channelInfo["channel"][str(myChannel)]["deviceCount"] + 1
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
                                channelInfo["channel"][str(myChannel)][
                                    "deviceTempFlag"
                                ],
                            )
                            print("---------------------------\n")
                            if (
                                channelInfo["channel"][str(myChannel)]["deviceCount"]
                                > 1
                            ) and (not args.devicenumber):
                                print(
                                    "Specify a devicenumber to select a specific device."
                                )
                    else:
                        raise ValueError(
                            "No device detected on channel " + str(myChannel) + "."
                        )
            print()
            # We need to exit to ensure no other CLI args are processed when requesting
            # summary as we cannot be sure that the appropriate device identifiers have
            # been specified.
            sys.exit("Done")

        # Change the recirculation temperature.
        if args.recirctemp:
            # Send the request
            stateData = navienSmartControl.sendRecirculationTempControlRequest(
                binascii.unhexlify(gateways[myGatewayID]["GID"]),
                int(myChannel),
                myDeviceNumber,
                channelInfo,
                args.recirctemp,
            )
            if ControlType(stateData["controlType"]) == ControlType.STATE:
                if "recirculationSettingTemperature" in stateData:
                    if (
                        TemperatureType(
                            channelInfo["channel"][str(myChannel)]["deviceTempFlag"]
                        )
                        == TemperatureType.CELSIUS
                    ):
                        print(
                            "Recirculation temperature now set to "
                            + str(
                                round(
                                    stateData["recirculationSettingTemperature"] / 2.0,
                                    1,
                                )
                            )
                            + " "
                            + u"\u00b0"
                            + "C"
                        )
                    elif (
                        TemperatureType(
                            channelInfo["channel"][str(myChannel)]["deviceTempFlag"]
                        )
                        == TemperatureType.FAHRENHEIT
                    ):
                        print(
                            "Recirculation temperature now set to "
                            + str(stateData["recirculationSettingTemperature"])
                            + " "
                            + u"\u00b0"
                            + "F"
                        )
                else:
                    raise ValueError(
                        "Recirculation temperature does not appear to be supported."
                    )
            else:
                # We didn't receive the expected response, it's probably an error. Let the print handler deal with it.
                navienSmartControl.printResponseHandler(
                    stateData, channelInfo["channel"][str(myChannel)]["deviceTempFlag"]
                )

        # Set the central heating temperature.
        if args.heatingtemp:
            # Send the request
            stateData = navienSmartControl.sendHeatingWaterTempControlRequest(
                binascii.unhexlify(gateways[myGatewayID]["GID"]),
                int(myChannel),
                myDeviceNumber,
                channelInfo,
                args.heatingtemp,
            )
            if ControlType(stateData["controlType"]) == ControlType.STATE:
                if (
                    TemperatureType(
                        channelInfo["channel"][str(myChannel)]["deviceTempFlag"]
                    )
                    == TemperatureType.CELSIUS
                ):
                    print(
                        "Heating setting temperature now set to "
                        + str(round(stateData["heatSettingTemperature"] / 2.0, 1))
                        + " "
                        + u"\u00b0"
                        + "C"
                    )
                elif (
                    TemperatureType(
                        channelInfo["channel"][str(myChannel)]["deviceTempFlag"]
                    )
                    == TemperatureType.FAHRENHEIT
                ):
                    print(
                        "Heating setting temperature now set to "
                        + str(stateData["heatSettingTemperature"])
                        + " "
                        + u"\u00b0"
                        + "F"
                    )
            else:
                # We didn't receive the expected response, it's probably an error. Let the print handler deal with it.
                navienSmartControl.printResponseHandler(
                    stateData, channelInfo["channel"][str(myChannel)]["deviceTempFlag"]
                )

        # Set the hot water temperature.
        if args.hotwatertemp:
            # Send the request
            stateData = navienSmartControl.sendWaterTempControlRequest(
                binascii.unhexlify(gateways[myGatewayID]["GID"]),
                int(myChannel),
                myDeviceNumber,
                channelInfo,
                args.hotwatertemp,
            )
            if ControlType(stateData["controlType"]) == ControlType.STATE:
                if (
                    TemperatureType(
                        channelInfo["channel"][str(myChannel)]["deviceTempFlag"]
                    )
                    == TemperatureType.CELSIUS
                ):
                    print(
                        "Hot water setting temperature now set to "
                        + str(round(stateData["hotWaterSettingTemperature"] / 2.0, 1))
                        + " "
                        + u"\u00b0"
                        + "C"
                    )
                elif (
                    TemperatureType(
                        channelInfo["channel"][str(myChannel)]["deviceTempFlag"]
                    )
                    == TemperatureType.FAHRENHEIT
                ):
                    print(
                        "Hot water setting temperature now set to "
                        + str(stateData["hotWaterSettingTemperature"])
                        + " "
                        + u"\u00b0"
                        + "F"
                    )
            else:
                # We didn't receive the expected response, it's probably an error. Let the print handler deal with it.
                navienSmartControl.printResponseHandler(
                    stateData, channelInfo["channel"][str(myChannel)]["deviceTempFlag"]
                )

        # Set the power on or off
        if args.power:
            stateData = navienSmartControl.sendPowerControlRequest(
                binascii.unhexlify(gateways[myGatewayID]["GID"]),
                int(myChannel),
                myDeviceNumber,
                OnOFFFlag[(args.power).upper()].value,
            )
            if "powerStatus" in stateData:
                print(
                    "Power status is now "
                    + (OnOFFFlag(stateData["powerStatus"]).name).lower()
                )
            else:
                # We didn't receive the expected response, it's probably an error. Let the print handler deal with it.
                navienSmartControl.printResponseHandler(
                    stateData, channelInfo["channel"][str(myChannel)]["deviceTempFlag"]
                )

        # Set the heat on or off
        if args.heat:
            stateData = navienSmartControl.sendHeatControlRequest(
                binascii.unhexlify(gateways[myGatewayID]["GID"]),
                int(myChannel),
                myDeviceNumber,
                channelInfo,
                OnOFFFlag[(args.heat).upper()].value,
            )
            if "heatStatus" in stateData:
                print(
                    "Heat status is now "
                    + (OnOFFFlag(stateData["heatStatus"]).name).lower()
                )
            else:
                # We didn't receive the expected response, it's probably an error. Let the print handler deal with it.
                navienSmartControl.printResponseHandler(
                    stateData, channelInfo["channel"][str(myChannel)]["deviceTempFlag"]
                )

        # Set on demand on or off
        if args.ondemand:
            stateData = navienSmartControl.sendOnDemandControlRequest(
                binascii.unhexlify(gateways[myGatewayID]["GID"]),
                int(myChannel),
                myDeviceNumber,
                channelInfo,
            )
            if "useOnDemand" in stateData:
                print(
                    "On Demand status is now "
                    + (OnOFFFlag(stateData["useOnDemand"]).name).lower()
                )
            else:
                # We didn't receive the expected response, it's probably an error. Let the print handler deal with it.
                navienSmartControl.printResponseHandler(
                    stateData, channelInfo["channel"][str(myChannel)]["deviceTempFlag"]
                )

        # Set the weekly recirculation schedule on or off
        if args.schedule:
            stateData = navienSmartControl.sendDeviceWeeklyControlRequest(
                binascii.unhexlify(gateways[myGatewayID]["GID"]),
                int(myChannel),
                myDeviceNumber,
                OnOFFFlag[(args.schedule).upper()].value,
            )
            if "weeklyControl" in stateData:
                print(
                    "Weekly schedule control is now "
                    + (OnOFFFlag(stateData["weeklyControl"]).name).lower()
                )
            else:
                # We didn't receive the expected response, it's probably an error. Let the print handler deal with it.
                navienSmartControl.printResponseHandler(
                    stateData, channelInfo["channel"][str(myChannel)]["deviceTempFlag"]
                )

        # Print the trend sample info
        if args.trendsample:
            trendSample = navienSmartControl.sendTrendSampleRequest(
                binascii.unhexlify(gateways[myGatewayID]["GID"]),
                int(myChannel),
                myDeviceNumber,
            )
            navienSmartControl.printResponseHandler(
                trendSample, channelInfo["channel"][str(myChannel)]["deviceTempFlag"]
            )

        # Print the trend month info
        if args.trendmonth:
            trendMonth = navienSmartControl.sendTrendMonthRequest(
                binascii.unhexlify(gateways[myGatewayID]["GID"]),
                int(myChannel),
                myDeviceNumber,
            )
            navienSmartControl.printResponseHandler(
                trendMonth, channelInfo["channel"][str(myChannel)]["deviceTempFlag"]
            )

        # Print the trend year info
        if args.trendyear:
            trendYear = navienSmartControl.sendTrendYearRequest(
                binascii.unhexlify(gateways[myGatewayID]["GID"]),
                int(myChannel),
                myDeviceNumber,
            )
            navienSmartControl.printResponseHandler(
                trendYear, channelInfo["channel"][str(myChannel)]["deviceTempFlag"]
            )

        # Update recirculation schedule
        if args.modifyschedule:
            if args.scheduletime and args.scheduleday and args.schedulestate:
                hourMin = (args.scheduletime).split(":", 1)
                if (int(hourMin[0]) < 24) and (int(hourMin[1]) < 60):
                    weeklyDay = {
                        "dayOfWeek": DayOfWeek[(args.scheduleday).upper()].value,
                        "hour": int(hourMin[0]),
                        "minute": int(hourMin[1]),
                        "isOnOFF": OnOFFFlag[(args.schedulestate).upper()].value,
                    }
                    currentState = navienSmartControl.sendStateRequest(
                        binascii.unhexlify(gateways[myGatewayID]["GID"]),
                        int(myChannel),
                        myDeviceNumber,
                    )
                    stateData = navienSmartControl.sendDeviceControlWeeklyScheduleRequest(
                        currentState, weeklyDay, args.modifyschedule
                    )
                    navienSmartControl.printResponseHandler(
                        stateData,
                        channelInfo["channel"][str(myChannel)]["deviceTempFlag"],
                    )
                else:
                    raise ValueError(
                        "Invalid time specified: " + args.scheduletime + "."
                    )
            else:
                raise ValueError(
                    "Must supply values for modifyschedule, scheduletime, scheduleday and schedulestate."
                )

        # finished parsing everything, just exit
        sys.exit("Done")
