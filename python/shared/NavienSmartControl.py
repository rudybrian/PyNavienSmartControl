#!/usr/bin/env python

# Third party library; "pip install requests" if getting import errors.
import requests

# We use raw sockets.
import socket

# We unpack structures.
import struct

# We use namedtuple to reduce index errors.
import collections

# We use binascii to convert some consts from hex.
import binascii

# We use Python enums.
import enum

# We need json support for parsing the REST API response
import json


class OperateMode(enum.Enum):
    POWER_OFF = 1
    POWER_ON = 2
    GOOUT_OFF = 3
    GOOUT_ON = 4
    INSIDE_HEAT = 5
    ONDOL_HEAT = 6
    REPEAT_RESERVE = 7
    CIRCLE_RESERVE = 8
    SIMPLE_RESERVE = 9
    HOTWATER_ON = 10
    HOTWATER_OFF = 11
    WATER_SET_TEMP = 12
    QUICK_HOTWATER = 13
    HEAT_LEVEL = 14
    ACTIVE = 128


class ModeState(enum.Enum):
    POWER_OFF = 1
    GOOUT_ON = 2
    INSIDE_HEAT = 3
    ONDOL_HEAT = 4
    SIMPLE_RESERVE = 5
    CIRCLE_RESERVE = 6
    HOTWATER_ON = 8


class HeatLevel(enum.Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3


class ControlType(enum.Enum):
    UNKNOWN = 0
    CHANNEL_INFORMATION = 1
    STATE = 2
    TREND_SAMPLE = 3
    TREND_MONTH = 4
    TREND_YEAR = 5
    ERROR_CODE = 6


class ChannelUse(enum.Enum):
    UNKNOWN = 0
    CHANNEL_1_USE = 1
    CHANNEL_2_USE = 2
    CHANNEL_1_2_USE = 3
    CHANNEL_3_USE = 4
    CHANNEL_1_3_USE = 5
    CHANNEL_2_3_USE = 6
    CHANNEL_1_2_3_USE = 7


class DeviceSorting(enum.Enum):
    NO_DEVICE = 0
    NPE = 1
    NCB = 2
    NHB = 3
    CAS_NPE = 4
    CAS_NHB = 5
    NFB = 6
    CAS_NFB = 7
    NFC = 8
    NPN = 9
    CAS_NPN = 10
    NPE2 = 11
    CAS_NPE2 = 12
    NCB_H = 13
    NVW = 14
    CAS_NVW = 15


class TemperatureType(enum.Enum):
    UNKNOWN = 0
    CELSIUS = 1
    FAHRENHEIT = 2


class OnDemandFlag(enum.Enum):
    UNKNOWN = 0
    ON = 1
    OFF = 2
    WARMUP = 3


class HeatingControl(enum.Enum):
    UNKNOWN = 0
    SUPPLY = 1
    RETURN = 2
    OUTSIDE_CONTROL = 3


class WWSDFlag(enum.Enum):
    OK = False
    FAIL = True


class WWSDMask(enum.Enum):
    wwsdFlag = 0x01
    commercialLock = 0x02
    hotwaterPossibility = 0x04
    recirculationPossibility = 0x08


class CommercialLockFlag(enum.Enum):
    OK = False
    LOCK = True


class NFBWaterFlag(enum.Enum):
    OFF = False
    ON = True


class RecirculationFlag(enum.Enum):
    OFF = False
    ON = True


class HighTemperature(enum.Enum):
    TEMPERATURE_60 = 0
    TEMPERATURE_83 = 1


class OnOFFFlag(enum.Enum):
    UNKNOWN = 0
    ON = 1
    OFF = 2


class TempControlType(enum.IntFlag):

    # 3rd bit.
    POINTINSIDE = 32

    # 4th bit.
    POINTONDOL = 16

    # 5th bit.
    POINTWATER = 8

    # 6th - 8th bits (last 3 bits).
    WATERMODE = 7


class NavienSmartControl:

    # This prevents the requests module from creating its own user-agent.
    stealthyHeaders = {"User-Agent": None}

    # The Navien server.
    navienServer = "uscv2.naviensmartcontrol.com"
    navienWebServer = "https://" + navienServer
    navienServerSocketPort = 6001

    def __init__(self, userID, passwd):
        self.userID = userID
        self.passwd = passwd
        self.connection = None

    def login(self):
        # Login.
        response = requests.post(
            NavienSmartControl.navienWebServer + "/api/requestDeviceList",
            headers=NavienSmartControl.stealthyHeaders,
            data={"userID": self.userID, "password": self.passwd},
        )

        # If an error occurs this will raise it, otherwise it returns the gateway list.
        return self.handleResponse(response)

    def handleResponse(self, response):

        # We need to check for the HTTP response code before attempting to parse the data
        # print('Response status code=' + str(response.status_code))
        if response.status_code != 200:
            print(response.text)
            response_data = json.loads(response.text)
            if response_data["msg"] == "DB_ERROR":
                # Credentials invalid or some other error
                raise Exception(
                    "Error: "
                    + response_data["msg"]
                    + ": Login details incorrect. Please note, these are case-sensitive."
                )
            else:
                raise Exception("Error: " + response_data["msg"])

        # Print what we received
        # print(response.json())
        response_data = json.loads(response.text)
        for key in response_data:
            # print(key + '->' + response_data[key])
            if key == "data":
                # print(response_data['data'])
                # json.loads() doesn't parse the json device array into a list for some reason, so we need to do this explicitly
                gateway_data = json.loads(response_data["data"])
                # print('There are ' + str(len(gateway_data)) + ' gateways.')
                # for j in range(len(gateway_data)):
                #    print('Gateway ' + str(j))
                #    for key_k in gateway_data[j]:
                #        print('\t' + key_k + '->' + gateway_data[j][key_k])

        # print('NickName=' + gateway_data[0]['NickName'] + ', gatewayID=' + gateway_data[0]['GID'])
        return gateway_data

    def connect(self, gatewayID):

        # Construct a socket object.
        self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Connect to the socket server.
        self.connection.connect(
            (NavienSmartControl.navienServer, NavienSmartControl.navienServerSocketPort)
        )

        # Request the status.
        self.connection.sendall(
            (self.userID + "$" + "iPhone1.0" + "$" + gatewayID).encode()
        )

        # Receive the status.
        data = self.connection.recv(1024)

        # Return the parsed home state data.
        return self.parseResponse(data)

    # Main handler for parsing responses from the binary protocol
    def parseResponse(self, data):
        # The response is returned with a fixed header for the first 12 bytes
        commonResponseColumns = collections.namedtuple(
            "response",
            [
                "deviceID",
                "countryCD",
                "controlType",
                "swVersionMajor",
                "swVersionMinor",
            ],
        )
        commonResponseData = commonResponseColumns._make(
            struct.unpack(
                "8s          B             B                B                  B",
                data[:12],
            )
        )

        # print("Device ID: " + "".join("%02x" % b for b in commonResponseData.deviceID))

        # Based on the controlType, parse the response accordingly
        if commonResponseData.controlType == ControlType.CHANNEL_INFORMATION.value:
            retval = self.parseChannelInformationResponse(commonResponseData, data)
        elif commonResponseData.controlType == ControlType.STATE.value:
            retval = self.parseStateResponse(commonResponseData, data)
        elif commonResponseData.controlType == ControlType.TREND_SAMPLE.value:
            retval = self.parseTrendSampleResponse(commonResponseData, data)
        elif commonResponseData.controlType == ControlType.TREND_MONTH.value:
            retval = self.parseTrendMonthResponse(commonResponseData, data)
        elif commonResponseData.controlType == ControlType.YEAR.value:
            retval = self.parseTrendYearResponse(commonResponseData, data)
        elif commonResponseData.controlType == ControlType.ERROR_CODE.value:
            retval = self.parseErrorCodeResponse(commonResponseData, data)
        elif commonResponseData.controlType == ControlType.UNKNOWN.value:
            raise Exception("Error: Unknown controlType. Please restart to retry.")
        else:
            raise Exception(
                "An error occurred in the process of retrieving data; please restart to retry."
            )

        return retval

    # Parse channel information response
    def parseChannelInformationResponse(self, commonResponseData, data):
        # This tells us which serial channels are in use
        chanUse = data[12]
        fwVersion = int(
            commonResponseData.swVersionMajor * 100 + commonResponseData.swVersionMinor
        )
        channelResponseData = {}
        if fwVersion > 1500:
            chanOffset = 15
        else:
            chanOffset = 13

        if chanUse != ChannelUse.UNKNOWN.value:
            if fwVersion < 1500:
                channelResponseColumns = collections.namedtuple(
                    "response",
                    [
                        "channel",
                        "deviceSorting",
                        "deviceCount",
                        "deviceTempFlag",
                        "minimumSettingWaterTemperature",
                        "maximumSettingWaterTemperature",
                        "heatingMinimumSettingWaterTemperature",
                        "heatingMaximumSettingWaterTemperature",
                        "useOnDemand",
                        "heatingControl",
                        "wwsdFlag",
                        "highTemperature",
                        "useWarmWater",
                    ],
                )
                for x in range(3):
                    channelResponseData[str(x + 1)] = channelResponseColumns._make(
                        struct.unpack(
                            "B B B B B B B B B B B B B",
                            data[
                                (13 + chanOffset * x) : (13 + chanOffset * x)
                                + chanOffset
                            ],
                        )
                    )
            else:
                channelResponseColumns = collections.namedtuple(
                    "response",
                    [
                        "channel",
                        "deviceSorting",
                        "deviceCount",
                        "deviceTempFlag",
                        "minimumSettingWaterTemperature",
                        "maximumSettingWaterTemperature",
                        "heatingMinimumSettingWaterTemperature",
                        "heatingMaximumSettingWaterTemperature",
                        "useOnDemand",
                        "heatingControl",
                        "wwsdFlag",
                        "highTemperature",
                        "useWarmWater",
                        "minimumSettingRecirculationTemperature",
                        "maximumSettingRecirculationTemperature",
                    ],
                )
                for x in range(3):
                    channelResponseData[str(x + 1)] = channelResponseColumns._make(
                        struct.unpack(
                            "B B B B B B B B B B B B B B B",
                            data[
                                (13 + chanOffset * x) : (13 + chanOffset * x)
                                + chanOffset
                            ],
                        )
                    )
            return channelResponseData
        else:
            raise Exception(
                "Error: Unknown Channel: An error occurred in the process of parsing channel information; please restart to retry."
            )

    # Parse state response
    def parseStateResponse(self, commonResponseData, data):
        print("Run away!")

    # Parse trend sample response
    def parseTrendSampleResponse(self, commonResponseData, data):
        print("Run away!")

    # Parse trend month response
    def parseTrendMonthResponse(self, commonResponseData, data):
        print("Run away!")

    # Parse trend year response
    def parseTrendYearResponse(self, commonResponseData, data):
        print("Run away!")

    # Parse error code response
    def parseErrorCodeResponse(self, commonResponseData, data):
        print("Run away!")

    # Print Channel Information response data
    def printChannelInformation(self, channelInformation):
        for chan in channelInformation:
            print("Channel:" + chan)
            # for name, value in channelInformation[chan]._asdict().items():
            #    print('\t' + name + '->' + str(value))
            print(
                "\tDevice Model Type: "
                + DeviceSorting(channelInformation[chan].deviceSorting).name
            )
            print("\tDevice Count: " + str(channelInformation[chan].deviceCount))
            print(
                "\tTemp Flag: "
                + TemperatureType(channelInformation[chan].deviceTempFlag).name
            )
            print(
                "\tMinimum Setting Water Temperature: "
                + str(channelInformation[chan].minimumSettingWaterTemperature)
            )
            print(
                "\tMaximum Setting Water Temperature: "
                + str(channelInformation[chan].maximumSettingWaterTemperature)
            )
            print(
                "\tHeating Minimum Setting Water Temperature: "
                + str(channelInformation[chan].heatingMinimumSettingWaterTemperature)
            )
            print(
                "\tHeating Maximum Setting Water Temperature: "
                + str(channelInformation[chan].heatingMaximumSettingWaterTemperature)
            )
            print(
                "\tUse On Demand: "
                + OnDemandFlag(channelInformation[chan].useOnDemand).name
            )
            print(
                "\tHeating Control: "
                + HeatingControl(channelInformation[chan].heatingControl).name
            )
            # Do some different stuff with the wwsdFlag value
            print(
                "\twwsdFlag: "
                + WWSDFlag(
                    (channelInformation[chan].wwsdFlag & WWSDMask.wwsdFlag.value) > 0
                ).name
            )
            print(
                "\tcommercialLock: "
                + CommercialLockFlag(
                    (channelInformation[chan].wwsdFlag & WWSDMask.commercialLock.value)
                    > 0
                ).name
            )
            print(
                "\thotwaterPossibility: "
                + NFBWaterFlag(
                    (
                        channelInformation[chan].wwsdFlag
                        & WWSDMask.hotwaterPossibility.value
                    )
                    > 0
                ).name
            )
            print(
                "\trecirculationPossibility: "
                + RecirculationFlag(
                    (
                        channelInformation[chan].wwsdFlag
                        & WWSDMask.recirculationPossibility.value
                    )
                    > 0
                ).name
            )
            print(
                "\tHigh Temperature: "
                + HighTemperature(channelInformation[chan].highTemperature).name
            )
            print(
                "\tUse Warm Water: "
                + OnOFFFlag(channelInformation[chan].useWarmWater).name
            )

    def printHomeState(self, homeState):
        print("Device ID: " + ":".join("%02x" % b for b in homeState.deviceid))
        print("Country Code: " + str(homeState.nationCode))
        print("Hardware Revision: V" + str(homeState.hwRev))
        print("Software Version: V" + str(homeState.swRev) + ".0")
        print("Network Type: " + str(homeState.netType))
        print("Control Type?: " + str(homeState.controlType))
        print("Boiler Model Type: " + str(homeState.boilerModelType))
        print("Room Controllers: " + str(homeState.roomCnt))
        print("smsFg?: " + str(homeState.smsFg))
        print(
            "Error: "
            + ("No Error" if homeState.errorCode == 0 else homeState.errorCode)
        )
        print(
            "Hot Water Set Temperature: "
            + str(self.getTemperatureFromByte(homeState.hotWaterSetTemp))
            + " °C"
        )
        print(
            "Heat Intensity Type: "
            + ["Unknown", "Low", "Medium", "High"][homeState.heatLevel]
        )
        print(
            "Option Use Flags: "
            + bin(homeState.optionUseFg)
            + (
                " (Usable 24 Hour Reserve)"
                if homeState.optionUseFg & 128 == 128
                else ""
            )
        )
        print()

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
            "Current Room Temperature: "
            + str(self.getTemperatureFromByte(homeState.currentInsideTemp))
            + " °C"
        )
        print(
            "Inside Heating Temperature: "
            + str(self.getTemperatureFromByte(homeState.insideHeatTemp))
            + " °C"
        )
        print(
            "Central Heating Temperature: "
            + str(self.getTemperatureFromByte(homeState.ondolHeatTemp))
            + " °C"
        )
        print()
        print(
            "Heating Timer Interval: Every "
            + str(homeState.repeatReserveHour)
            + " hour(s)"
        )
        print(
            "Heating Timer Duration: "
            + str(homeState.repeatReserveMinute)
            + " minute(s)"
        )
        print()
        print("24Hour Schedule (00-08h): " + bin(homeState.hour24ReserveTime1))
        print("24Hour Schedule (09-16h): " + bin(homeState.hour24ReserveTime2))
        print("24Hour Schedule (17-24h): " + bin(homeState.hour24ReserveTime3))
        print()
        print("Simple Reserve Set Time: " + str(homeState.simpleReserveSetTime))
        print("Simple Reserve Set Minute: " + str(homeState.simpleReserveSetMinute))
        print()
        print(
            "Operation Mode Flags: "
            + bin(homeState.operateMode)
            + (" (Active)" if homeState.operateMode & OperateMode.ACTIVE.value else "")
        )
        print()
        print("Temperature Control Supported Types: " + bin(homeState.tempControlType))
        if homeState.tempControlType & TempControlType.POINTINSIDE:
            print(" (POINTINSIDE)")
        if homeState.tempControlType & TempControlType.POINTONDOL:
            print(" (POINTONDOL)")
        if homeState.tempControlType & TempControlType.POINTWATER:
            print(" (POINTWATER)")
        if homeState.tempControlType & TempControlType.WATERMODE.value > 0:
            print(
                " (WATERMODE_"
                + str(homeState.tempControlType & TempControlType.WATERMODE.value)
                + ") = "
                + ["Unknown", "Stepped", "Temperature"][
                    (homeState.tempControlType & TempControlType.WATERMODE.value) - 1
                ]
                + " Controlled"
            )
        print()

        print(
            "Hot Water Temperature Supported Range: "
            + str(self.getTemperatureFromByte(homeState.hotwaterMin))
            + " °C - "
            + str(self.getTemperatureFromByte(homeState.hotwaterMax))
            + " °C"
        )
        print(
            "Central Heating Temperature Supported Range: "
            + str(self.getTemperatureFromByte(homeState.ondolHeatMin))
            + " °C - "
            + str(self.getTemperatureFromByte(homeState.ondolHeatMax))
            + " °C"
        )
        print(
            "Room Temperature Supported Range: "
            + str(self.getTemperatureFromByte(homeState.insideHeatMin))
            + " °C - "
            + str(self.getTemperatureFromByte(homeState.insideHeatMax))
            + " °C"
        )
        print()
        print("Reserved 09: " + str(homeState.reserve09))
        print("Reserved 10: " + str(homeState.reserve10))

    def getTemperatureByte(self, temperature):
        return int(2.0 * temperature)

    def getTemperatureFromByte(self, temperatureByte):
        return float((temperatureByte >> 1) + (0.5 if temperatureByte & 1 else 0))

    def setOperationMode(
        self, homeState, operateMode, value01, value02, value03, value04, value05
    ):

        commandListSequence = 0
        commandListCommand = 131
        commandListDataLength = 21
        commandListCount = 0

        sendData = bytearray(
            [
                commandListSequence,
                commandListCommand,
                commandListDataLength,
                commandListCount,
            ]
        )
        sendData.extend(homeState.deviceid)

        commandSequence = 1
        sendData.extend(
            [
                commandSequence,
                operateMode.value,
                value01,
                value02,
                value03,
                value04,
                value05,
            ]
        )

        self.connection.sendall(sendData)

    # ------ Set OperationMode convenience methods --------- #

    def setPowerOff(self, homeState):
        return self.setOperationMode(homeState, OperateMode.POWER_OFF, 1, 0, 0, 0, 0)

    def setPowerOn(self, homeState):
        return self.setOperationMode(homeState, OperateMode.POWER_ON, 1, 0, 0, 0, 0)

    def setGoOutOff(self, homeState):
        return self.setOperationMode(homeState, OperateMode.GOOUT_OFF, 1, 0, 0, 0, 0)

    def setGoOutOn(self, homeState):
        return self.setOperationMode(homeState, OperateMode.GOOUT_ON, 1, 0, 0, 0, 0)

    def setInsideHeat(self, homeState, temperature):
        if temperature < self.getTemperatureFromByte(
            homeState.insideHeatMin
        ) or temperature > self.getTemperatureFromByte(homeState.insideHeatMax):
            raise ValueError(
                "Temperature specified is outside the boiler's supported range."
            )
        return self.setOperationMode(
            homeState,
            OperateMode.INSIDE_HEAT,
            1,
            0,
            0,
            0,
            self.getTemperatureByte(temperature),
        )

    def setOndolHeat(self, homeState, temperature):
        if temperature < self.getTemperatureFromByte(
            homeState.ondolHeatMin
        ) or temperature > self.getTemperatureFromByte(homeState.ondolHeatMax):
            raise ValueError(
                "Temperature specified is outside the boiler's supported range."
            )
        return self.setOperationMode(
            homeState,
            OperateMode.ONDOL_HEAT,
            1,
            0,
            0,
            0,
            self.getTemperatureByte(temperature),
        )

    def setRepeatReserve(self, homeState, hourInterval, durationMinutes):
        return self.setOperationMode(
            homeState,
            OperateMode.REPEAT_RESERVE,
            1,
            0,
            0,
            hourInterval,
            durationMinutes,
        )

    def setCircleReserve(self, homeState, schedule1, schedule2, schedule3):
        return self.setOperationMode(
            homeState, OperateMode.CIRCLE_RESERVE, 1, 0, schedule1, schedule2, schedule3
        )

    def setHotWaterOn(self, homeState):
        return self.setOperationMode(homeState, OperateMode.HOTWATER_ON, 1, 0, 0, 0, 0)

    def setHotWaterOff(self, homeState):
        return self.setOperationMode(homeState, OperateMode.HOTWATER_OFF, 1, 0, 0, 0, 0)

    def setHotWaterHeat(self, homeState, temperature):
        if temperature < self.getTemperatureFromByte(
            homeState.hotwaterMin
        ) or temperature > self.getTemperatureFromByte(homeState.hotwaterMax):
            raise ValueError(
                "Temperature specified is outside the boiler's supported range."
            )
        return self.setOperationMode(
            homeState,
            OperateMode.WATER_SET_TEMP,
            1,
            0,
            0,
            0,
            self.getTemperatureByte(temperature),
        )

    def setQuickHotWater(self, homeState):
        return self.setOperationMode(
            homeState, OperateMode.QUICK_HOTWATER, 1, 0, 0, 0, 0
        )

    def setHeatLevel(self, homeState, heatLevel):
        return self.setOperationMode(
            homeState, OperateMode.HEAT_LEVEL, 1, 0, 0, 0, heatLevel.value
        )
