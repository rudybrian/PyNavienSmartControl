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


class AutoVivification(dict):
    """Implementation of perl's autovivification feature."""

    def __getitem__(self, item):
        try:
            return dict.__getitem__(self, item)
        except KeyError:
            value = self[item] = type(self)()
            return value


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

    # HTTP response handler
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

        response_data = json.loads(response.text)

        try:
            response_data["data"]
            gateway_data = json.loads(response_data["data"])
        except NameError:
            raise Exception("Error: Unexpected JSON response to gateway list request.")

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
        stateResponseColumns = collections.namedtuple(
            "response",
            [
                "controllerVersion",
                "pannelVersion",
                "deviceSorting",
                "deviceCount",
                "currentChannel",
                "deviceNumber",
                "errorCD",
                "operationDeviceNumber",
                "averageCalorimeter",
                "gasInstantUse",
                "gasAccumulatedUse",
                "hotWaterSettingTemperature",
                "hotWaterCurrentTemperature",
                "hotWaterFlowRate",
                "hotWaterTemperature",
                "heatSettingTemperature",
                "currentWorkingFluidTemperature",
                "currentReturnWaterTemperature",
                "powerStatus",
                "heatStatus",
                "useOnDemand",
                "weeklyControl",
                "totalDaySequence",
            ],
        )
        stateResponseData = stateResponseColumns._make(
            struct.unpack(
                "2s 2s B B B B 2s B B 2s 4s B B 2s B B B B B B B B B", data[12:43]
            )
        )
        print(
            "controllerVersion: "
            + "".join("%02x" % b for b in stateResponseData.controllerVersion)
        )

        # Load each of the 7 daily sets of day sequences
        daySequenceResponseColumns = collections.namedtuple(
            "response", ["hour", "minute", "isOnOFF"]
        )

        daySequences = AutoVivification()
        for i in range(7):
            i2 = i * 32
            i3 = i2 + 43
            daySequences[str(i)]["dayOfWeek"] = data[i3]
            weeklyTotalCount = data[i2 + 44]
            for i4 in range(weeklyTotalCount):
                i5 = i4 * 3
                daySequences[str(i)]["daySequence"][
                    str(i4)
                ] = daySequenceResponseColumns._make(
                    struct.unpack("B B B", data[i2 + 45 + i5 : i2 + 45 + i5 + 3])
                )
        if len(data) > 271:
            stateResponseColumns2 = collections.namedtuple(
                "response",
                [
                    "hotWaterAverageTemperature",
                    "inletAverageTemperature",
                    "supplyAverageTemperature",
                    "returnAverageTemperature",
                    "recirculationSettingTemperature",
                    "recirculationCurrentTemperature",
                ],
            )
            stateResponseData2 = stateResponseColumns2._make(
                struct.unpack("B B B B B B", data[267:274])
            )
        else:
            stateResponseColumns2 = collections.namedtuple(
                "response",
                [
                    "hotWaterAverageTemperature",
                    "inletAverageTemperature",
                    "supplyAverageTemperature",
                    "returnAverageTemperature",
                ],
            )
            stateResponseData2 = stateResponseColumns2._make(
                struct.unpack("B B B B", data[267:272])
            )
        tmpDaySequences = {"daySequences": daySequences}
        result = dict(stateResponseData._asdict(), **tmpDaySequences)
        result.update(stateResponseData2._asdict())
        return result

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
            # These values are ony populated with firmware version > 1500
            if hasattr(
                channelInformation[chan], "minimumSettingRecirculationTemperature"
            ):
                print(
                    "\tMinimum Recirculation Temperature: "
                    + channelInformation[chan].minimumSettingRecirculationTemperature
                )
                print(
                    "\tMaximum Recirculation Temperature: "
                    + channelInformation[chan].maximumSettingRecirculationTemperature
                )

    # Print State response data
    def printState(self, stateData, temperatureType):
        print(json.dumps(stateData, indent=2, default=str))
        print(
            "Controller Version: "
            + "".join("%02x" % b for b in stateData["controllerVersion"])
        )
        print(
            "Panel Version: " + "".join("%02x" % b for b in stateData["pannelVersion"])
        )
        print("Device Model Type: " + DeviceSorting(stateData["deviceSorting"]).name)
        print("Device Count: " + str(stateData["deviceCount"]))
        print("Current Channel: " + str(stateData["currentChannel"]))
        print("Device Number: " + str(stateData["deviceNumber"]))
        errorCD = (stateData["errorCD"][0] & 0xFF) + (
            stateData["errorCD"][1] & 0xFF
        ) * 256
        if errorCD == 0:
            errorCD = "Normal"
        print("Error Code: " + str(errorCD))
        print("Operation Device Number: " + str(stateData["operationDeviceNumber"]))
        if temperatureType == TemperatureType.CELSIUS.value:
            print(
                "Average Calorimeter: "
                + str(stateData["averageCalorimeter"] / 2.0)
                + "%"
            )
            print(
                "Current Gas Usage: "
                + str((stateData["gasInstantUse"] * 100) / 10.0)
                + "kcal"
            )
            print(
                "Total Gas Usage: "
                + str(stateData["gasAccumulatedUse"] / 10.0)
                + "m\u00b2"
            )
            print(
                "Hot Water Setting Temperature: "
                + str(stateData["hotWaterSettingTemperature"] / 2.0)
                + u"\u00b0"
                + "C"
            )
            print(
                "Hot Water Current Temperature: "
                + str(stateData["hotWaterCurrentTemperature"] / 2.0)
                + u"\u00b0"
                + "C"
            )
            print(
                "Hot Water Flow Rate: "
                + str(stateData["hotWaterFlowRate"] / 10.0)
                + "LPM"
            )
            print(
                "Inlet Temperature: "
                + str(stateData["hotWaterTemperature"] / 2.0)
                + u"\u00b0"
                + "C"
            )
            print(
                "Current Working Fluid Temperature: "
                + str(stateData["currentWorkingFluidTemperature"] / 2.0)
                + u"\u00b0"
                + "C"
            )
            print(
                "Current Return Water Temperature: "
                + str(stateData["currentReturnWaterTemperature"] / 2.0)
                + u"\u00b0"
                + "C"
            )
        elif temperatureType == TemperatureType.FAHRENHEIT.value:
            print(
                "Average Calorimeter: "
                + str(stateData["averageCalorimeter"] / 2.0)
                + "%"
            )
        else:
            raise Exception("Error: Invalid temperatureType.")

    # leaving this here for reference, but will be removed
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

    # Send a request to the binary API
    def sendRequest(
        self,
        gatewayID,
        currentControlChannel,
        deviceNumber,
        controlSorting,
        infoItem,
        controlItem,
        controlValue,
        WeeklyDay,
    ):
        requestHeader = {
            "stx": 0x07,
            "did": 0x99,
            "reserve": 0x00,
            "cmd": 0xA6,
            "dataLength": 0x37,
            "dSid": 0x00,
        }
        sendData = bytearray(
            [
                requestHeader["stx"],
                requestHeader["did"],
                requestHeader["reserve"],
                requestHeader["cmd"],
                requestHeader["dataLength"],
                requestHeader["dSid"],
            ]
        )
        sendData.extend(gatewayID)
        sendData.extend(
            [
                0x01,  # commandCount
                currentControlChannel,
                deviceNumber,
                controlSorting,
                infoItem,
                controlItem,
                controlValue,
            ]
        )
        sendData.extend(
            [
                WeeklyDay["WeeklyDay"],
                WeeklyDay["WeeklyCount"],
                WeeklyDay["1_Hour"],
                WeeklyDay["1_Minute"],
                WeeklyDay["1_Flag"],
                WeeklyDay["2_Hour"],
                WeeklyDay["2_Minute"],
                WeeklyDay["2_Flag"],
                WeeklyDay["3_Hour"],
                WeeklyDay["3_Minute"],
                WeeklyDay["3_Flag"],
                WeeklyDay["4_Hour"],
                WeeklyDay["4_Minute"],
                WeeklyDay["4_Flag"],
                WeeklyDay["5_Hour"],
                WeeklyDay["5_Minute"],
                WeeklyDay["5_Flag"],
                WeeklyDay["6_Hour"],
                WeeklyDay["6_Minute"],
                WeeklyDay["6_Flag"],
                WeeklyDay["7_Hour"],
                WeeklyDay["7_Minute"],
                WeeklyDay["7_Flag"],
                WeeklyDay["8_Hour"],
                WeeklyDay["8_Minute"],
                WeeklyDay["8_Flag"],
                WeeklyDay["9_Hour"],
                WeeklyDay["9_Minute"],
                WeeklyDay["9_Flag"],
                WeeklyDay["10_Hour"],
                WeeklyDay["10_Minute"],
                WeeklyDay["10_Flag"],
            ]
        )

        # We should ensure that the socket is still connected, and abort if not
        self.connection.sendall(sendData)

        # Receive the status.
        data = self.connection.recv(1024)
        return self.parseResponse(data)

    # Helper function to initialize and populate the WeeklyDay dict
    def initWeeklyDay(self):
        weeklyDay = {}
        weeklyDay["WeeklyDay"] = 0x00
        weeklyDay["WeeklyCount"] = 0x00
        for i in range(1, 11):
            weeklyDay[str(i) + "_Hour"] = 0x00
            weeklyDay[str(i) + "_Minute"] = 0x00
            weeklyDay[str(i) + "_Flag"] = 0x00
        return weeklyDay

    # ----- Convenience methods for sending requests ----- #

    # Send state request
    def sendStateRequest(self, gatewayID, currentControlChannel, deviceNumber):
        return self.sendRequest(
            gatewayID,
            currentControlChannel,
            deviceNumber,
            0x01,
            ControlType.STATE.value,
            0x00,
            0x00,
            self.initWeeklyDay(),
        )

    # Send channel information request
    def sendChannelInfoRequest(self, gatewayID, currentControlChannel, deviceNumber):
        return

    # Send trend sample request
    def sendTrendSampleRequest(self, gatewayID, currentControlChannel, deviceNumber):
        return

    # Send trend month request
    def sendTrendMonthRequest(self, gatewayID, currentControlChannel, deviceNumber):
        return

    # Send trend year request
    def sendTrendYearRequest(self, gatewayID, currentControlChannel, deviceNumber):
        return

    # Send device power control request
    def sendPowerControlRequest(
        self, gatewayID, currentControlChannel, deviceNumber, powerState
    ):
        return

    # Send device heat control request
    def sendHeatControlRequest(
        self,
        gatewayID,
        currentControlChannel,
        deviceNumber,
        channelInformation,
        heatVal,
    ):
        return

    # Send device water temperature control request
    def sendWaterTempControlRequest(
        self,
        gatewayID,
        currentControlChannel,
        deviceNumber,
        channelInformation,
        heatVal,
    ):
        return

    # Send device heatting water temperature control request
    def sendHeattingWaterTempControlRequest(
        self,
        gatewayID,
        currentControlChannel,
        deviceNumber,
        channelInformation,
        heatVal,
    ):
        return

    # Send device on demand control request
    def sendOnDemandControlRequest(
        self,
        gatewayID,
        currentControlChannel,
        deviceNumber,
        channelInformation,
        onDemandState,
    ):
        return

    # Send device recirculation control request
    def sendRecirculationControlRequest(
        self,
        gatewayID,
        currentControlChannel,
        deviceNumber,
        channelInformation,
        recirculationState,
    ):
        return

    # Send request to set weekly schedule
    def sendDeviceControlWeeklyRequest(
        self, gatewayID, currentControlChannel, deviceNumber, WeeklyDay
    ):
        # sendRequest(self, gatewayID, currentControlChannel, deviceNumber, controlSorting, infoItem, controlItem, controlValue, WeeklyDay)
        return

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
