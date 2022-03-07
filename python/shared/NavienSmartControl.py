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
    WWSDFLAG = 0x01
    COMMERCIAL_LOCK = 0x02
    HOTWATER_POSSIBILITY = 0x04
    RECIRCULATION_POSSIBILITY = 0x08


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


class DayOfWeek(enum.Enum):
    UN_KNOWN = 0
    SUN = 1
    MON = 2
    TUE = 3
    WED = 4
    THU = 5
    FRI = 6
    SAT = 7


class ControlSorting(enum.Enum):
    INFO = 1
    CONTROL = 2


class DeviceControl(enum.Enum):
    POWER = 1
    HEAT = 2
    WATER_TEMPERATURE = 3
    HEATTING_WATER_TEMPERATURE = 4
    ON_DEMAND = 5
    WEEKLY = 6
    RECIRCULATION_TEMPERATURE = 7


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

    # Connect to the binary API service
    def connect(self, gatewayID):

        # Construct a socket object.
        self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Connect to the socket server.
        self.connection.connect(
            (NavienSmartControl.navienServer, NavienSmartControl.navienServerSocketPort)
        )

        # Send the initial connection details
        self.connection.sendall(
            (self.userID + "$" + "iPhone1.0" + "$" + gatewayID).encode()
        )

        # Receive the status.
        data = self.connection.recv(1024)

        # Return the parsed data.
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
            retval = self.parseTrendMYResponse(commonResponseData, data)
        elif commonResponseData.controlType == ControlType.TREND_YEAR.value:
            retval = self.parseTrendMYResponse(commonResponseData, data)
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

        # Load each of the 7 daily sets of day sequences
        daySequenceResponseColumns = collections.namedtuple(
            "response", ["hour", "minute", "isOnOFF"]
        )

        daySequences = AutoVivification()
        for i in range(7):
            i2 = i * 32
            i3 = i2 + 43
            # Note Python 2.x doesn't convert these properly, so need to explicitly unpack them
            daySequences[i]["dayOfWeek"] = self.bigHexToInt(data[i3])
            weeklyTotalCount = self.bigHexToInt(data[i2 + 44])
            for i4 in range(weeklyTotalCount):
                i5 = i4 * 3
                daySequence = daySequenceResponseColumns._make(
                    struct.unpack("B B B", data[i2 + 45 + i5 : i2 + 45 + i5 + 3])
                )
                daySequences[i]["daySequence"][str(i4)] = daySequence._asdict()
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
        if len(data) > 39:
            trendSampleResponseColumns = collections.namedtuple(
                "response",
                [
                    "controllerVersion",
                    "pannelVersion",
                    "deviceSorting",
                    "deviceCount",
                    "currentChannel",
                    "deviceNumber",
                    "modelInfo",
                    "totalOperatedTime",
                    "totalGasAccumulateSum",
                    "totalHotWaterAccumulateSum",
                    "totalCHOperatedTime",
                    "totalDHWUsageTime",
                ],
            )
            trendSampleResponseData = trendSampleResponseColumns._make(
                struct.unpack("2s 2s B B B B 3s 4s 4s 4s 4s 4s", data[12:43])
            )
        else:
            trendSampleResponseColumns = collections.namedtuple(
                "response",
                [
                    "controllerVersion",
                    "pannelVersion",
                    "deviceSorting",
                    "deviceCount",
                    "currentChannel",
                    "deviceNumber",
                    "modelInfo",
                    "totalOperatedTime",
                    "totalGasAccumulateSum",
                    "totalHotWaterAccumulateSum",
                    "totalCHOperatedTime",
                ],
            )
            trendSampleResponseData = trendSampleResponseColumns._make(
                struct.unpack("2s 2s B B B B 3s 4s 4s 4s 4s", data[12:39])
            )
        return trendSampleResponseData._asdict()

    # Parse trend month or year response
    def parseTrendMYResponse(self, commonResponseData, data):
        trendSampleMYResponseColumns = collections.namedtuple(
            "response",
            [
                "controllerVersion",
                "pannelVersion",
                "deviceSorting",
                "deviceCount",
                "currentChannel",
                "deviceNumber",
                "totalDaySequence",
            ],
        )
        trendSampleMYResponseData = trendSampleMYResponseColumns._make(
            struct.unpack("2s 2s B B B B B", data[12:21])
        )

        # Read the trend sequence data
        trendSequenceColumns = collections.namedtuple(
            "response",
            [
                "modelInfo",
                "gasAccumulatedUse",
                "hotWaterAccumulatedUse",
                "hotWaterOperatedCount",
                "onDemandUseCount",
                "heatAccumulatedUse",
                "outdoorAirMaxTemperature",
                "outdoorAirMinTemperature",
                "dHWAccumulatedUse",
            ],
        )

        trendSequences = AutoVivification()
        # loops 31 times for month and 24 times for year
        for i in range(trendSampleMYResponseData.totalDaySequence):
            i2 = i * 22
            trendSequences[i]["dMIndex"] = data[i2 + 21]
            trendData = trendSequenceColumns._make(
                struct.unpack("3s 4s 4s 2s 2s 2s B B 2s", data[i2 + 22 : i2 + 43])
            )
            trendSequences[i]["trendData"] = trendData._asdict()

        tmpTrendSequences = {"trendSequences": trendSequences}
        return dict(trendSampleMYResponseData._asdict(), **tmpTrendSequences)

    # Parse error code response
    def parseErrorCodeResponse(self, commonResponseData, data):
        print("Run away!")

    # ----- Convenience methods for printing response data in human readable form ----- #

    # Print Channel Information response data
    def printChannelInformation(self, channelInformation):
        for chan in range(1, len(channelInformation) + 1):
            print("Channel:" + str(chan))
            # for name, value in channelInformation[str(chan)]._asdict().items():
            #    print('\t' + name + '->' + str(value))
            print(
                "\tDevice Model Type: "
                + DeviceSorting(channelInformation[str(chan)].deviceSorting).name
            )
            print("\tDevice Count: " + str(channelInformation[str(chan)].deviceCount))
            print(
                "\tTemp Flag: "
                + TemperatureType(channelInformation[str(chan)].deviceTempFlag).name
            )
            print(
                "\tMinimum Setting Water Temperature: "
                + str(channelInformation[str(chan)].minimumSettingWaterTemperature)
            )
            print(
                "\tMaximum Setting Water Temperature: "
                + str(channelInformation[str(chan)].maximumSettingWaterTemperature)
            )
            print(
                "\tHeating Minimum Setting Water Temperature: "
                + str(
                    channelInformation[str(chan)].heatingMinimumSettingWaterTemperature
                )
            )
            print(
                "\tHeating Maximum Setting Water Temperature: "
                + str(
                    channelInformation[str(chan)].heatingMaximumSettingWaterTemperature
                )
            )
            print(
                "\tUse On Demand: "
                + OnDemandFlag(channelInformation[str(chan)].useOnDemand).name
            )
            print(
                "\tHeating Control: "
                + HeatingControl(channelInformation[str(chan)].heatingControl).name
            )
            # Do some different stuff with the wwsdFlag value
            print(
                "\twwsdFlag: "
                + WWSDFlag(
                    (channelInformation[str(chan)].wwsdFlag & WWSDMask.WWSDFLAG.value)
                    > 0
                ).name
            )
            print(
                "\tcommercialLock: "
                + CommercialLockFlag(
                    (
                        channelInformation[str(chan)].wwsdFlag
                        & WWSDMask.COMMERCIAL_LOCK.value
                    )
                    > 0
                ).name
            )
            print(
                "\thotwaterPossibility: "
                + NFBWaterFlag(
                    (
                        channelInformation[str(chan)].wwsdFlag
                        & WWSDMask.HOTWATER_POSSIBILITY.value
                    )
                    > 0
                ).name
            )
            print(
                "\trecirculationPossibility: "
                + RecirculationFlag(
                    (
                        channelInformation[str(chan)].wwsdFlag
                        & WWSDMask.RECIRCULATION_POSSIBILITY.value
                    )
                    > 0
                ).name
            )
            print(
                "\tHigh Temperature: "
                + HighTemperature(channelInformation[str(chan)].highTemperature).name
            )
            print(
                "\tUse Warm Water: "
                + OnOFFFlag(channelInformation[str(chan)].useWarmWater).name
            )
            # These values are ony populated with firmware version > 1500
            if hasattr(
                channelInformation[str(chan)], "minimumSettingRecirculationTemperature"
            ):
                print(
                    "\tMinimum Recirculation Temperature: "
                    + channelInformation[
                        str(chan)
                    ].minimumSettingRecirculationTemperature
                )
                print(
                    "\tMaximum Recirculation Temperature: "
                    + channelInformation[
                        str(chan)
                    ].maximumSettingRecirculationTemperature
                )

    # Print State response data
    def printState(self, stateData, temperatureType):
        # print(json.dumps(stateData, indent=2, default=str))
        print(
            "Controller Version: "
            + str(self.bigHexToInt(stateData["controllerVersion"]))
        )
        print("Panel Version: " + str(self.bigHexToInt(stateData["pannelVersion"])))
        print("Device Model Type: " + DeviceSorting(stateData["deviceSorting"]).name)
        print("Device Count: " + str(stateData["deviceCount"]))
        print("Current Channel: " + str(stateData["currentChannel"]))
        print("Device Number: " + str(stateData["deviceNumber"]))
        errorCD = self.bigHexToInt(stateData["errorCD"])
        if errorCD == 0:
            errorCD = "Normal"
        print("Error Code: " + str(errorCD))
        print("Operation Device Number: " + str(stateData["operationDeviceNumber"]))
        print(
            "Average Calorimeter: " + str(stateData["averageCalorimeter"] / 2.0) + " %"
        )
        if temperatureType == TemperatureType.CELSIUS.value:
            if stateData["deviceSorting"] in [
                DeviceSorting.NFC.value,
                DeviceSorting.NCB_H.value,
                DeviceSorting.NFB.value,
                DeviceSorting.NVW.value,
            ]:
                GIUFactor = 100
            else:
                GIUFactor = 10
            # This needs to be summed for cascaded units
            print(
                "Current Gas Usage: "
                + str((self.bigHexToInt(stateData["gasInstantUse"]) * GIUFactor) / 10.0)
                + " kcal"
            )
            # This needs to be summed for cascaded units
            print(
                "Total Gas Usage: "
                + str(self.bigHexToInt(stateData["gasAccumulatedUse"]) / 10.0)
                + " m"
                + u"\u00b3"
            )
            # only print these if DHW is in use
            if stateData["deviceSorting"] in [
                DeviceSorting.NPE.value,
                DeviceSorting.NPN.value,
                DeviceSorting.NPE2.value,
                DeviceSorting.NCB.value,
                DeviceSorting.NFC.value,
                DeviceSorting.NCB_H.value,
                DeviceSorting.CAS_NPE.value,
                DeviceSorting.CAS_NPN.value,
                DeviceSorting.CAS_NPE2.value,
                DeviceSorting.NFB.value,
                DeviceSorting.NVW.value,
                DeviceSorting.CAS_NFB.value,
                DeviceSorting.CAS_NVW.value,
            ]:
                print(
                    "Hot Water Setting Temperature: "
                    + str(stateData["hotWaterSettingTemperature"] / 2.0)
                    + " "
                    + u"\u00b0"
                    + "C"
                )
                if str(DeviceSorting(stateData["deviceSorting"]).name).startswith(
                    "CAS_"
                ):
                    print(
                        "Hot Water Average Temperature: "
                        + str(stateData["hotWaterAverageTemperature"] / 2.0)
                        + " "
                        + u"\u00b0"
                        + "C"
                    )
                    print(
                        "Inlet Average Temperature: "
                        + str(stateData["inletAverageTemperature"] / 2.0)
                        + " "
                        + u"\u00b0"
                        + "C"
                    )
                print(
                    "Hot Water Current Temperature: "
                    + str(stateData["hotWaterCurrentTemperature"] / 2.0)
                    + " "
                    + u"\u00b0"
                    + "C"
                )
                print(
                    "Hot Water Flow Rate: "
                    + str(self.bigHexToInt(stateData["hotWaterFlowRate"]) / 10.0)
                    + " LPM"
                )
                print(
                    "Inlet Temperature: "
                    + str(stateData["hotWaterTemperature"] / 2.0)
                    + " "
                    + u"\u00b0"
                    + "C"
                )
                if "recirculationSettingTemperature" in stateData:
                    print(
                        "Recirculation Setting Temperature: "
                        + str(stateData["recirculationSettingTemperature"] / 2.0)
                        + " "
                        + u"\u00b0"
                        + "C"
                    )
                    print(
                        "Recirculation Current Temperature: "
                        + str(stateData["recirculationCurrentTemperature"] / 2.0)
                        + " "
                        + u"\u00b0"
                        + "C"
                    )
            # Only print these if CH is in use
            if stateData["deviceSorting"] in [
                DeviceSorting.NHB.value,
                DeviceSorting.CAS_NHB.value,
                DeviceSorting.NFB.value,
                DeviceSorting.NVW.value,
                DeviceSorting.CAS_NFB.value,
                DeviceSorting.CAS_NVW.value,
                DeviceSorting.NCB.value,
                DeviceSorting.NFC.value,
                DeviceSorting.NCB_H.value,
            ]:
                # Don't show the setting for cascaded devices, as it isn't applicable
                print(
                    "Heat Setting Temperature: "
                    + str(stateData["heatSettingTemperature"] / 2.0)
                    + " "
                    + u"\u00b0"
                    + "C"
                )
                if str(DeviceSorting(stateData["deviceSorting"]).name).startswith(
                    "CAS_"
                ):
                    print(
                        "Supply Average Temperature: "
                        + str(stateData["supplyAverageTemperature"] / 2.0)
                        + " "
                        + u"\u00b0"
                        + "C"
                    )
                    print(
                        "Return Average Temperature: "
                        + str(stateData["returnAverageTemperature"] / 2.0)
                        + " "
                        + u"\u00b0"
                        + "C"
                    )
                print(
                    "Current Supply Water Temperature: "
                    + str(stateData["currentWorkingFluidTemperature"] / 2.0)
                    + " "
                    + u"\u00b0"
                    + "C"
                )
                print(
                    "Current Return Water Temperature: "
                    + str(stateData["currentReturnWaterTemperature"] / 2.0)
                    + " "
                    + u"\u00b0"
                    + "C"
                )
        elif temperatureType == TemperatureType.FAHRENHEIT.value:
            if stateData["deviceSorting"] in [
                DeviceSorting.NFC.value,
                DeviceSorting.NCB_H.value,
                DeviceSorting.NFB.value,
                DeviceSorting.NVW.value,
            ]:
                GIUFactor = 10
            else:
                GIUFactor = 1
            # This needs to be summed for cascaded units
            print(
                "Current Gas Usage: "
                + str(self.bigHexToInt(stateData["gasInstantUse"]) * GIUFactor * 3.968)
                + " BTU"
            )
            # This needs to be summed for cascaded units
            print(
                "Total Gas Usage: "
                + str(
                    (self.bigHexToInt(stateData["gasAccumulatedUse"]) * 35.314667)
                    / 10.0
                )
                + " ft"
                + u"\u00b3"
            )
            # only print these if DHW is in use
            if stateData["deviceSorting"] in [
                DeviceSorting.NPE.value,
                DeviceSorting.NPN.value,
                DeviceSorting.NPE2.value,
                DeviceSorting.NCB.value,
                DeviceSorting.NFC.value,
                DeviceSorting.NCB_H.value,
                DeviceSorting.CAS_NPE.value,
                DeviceSorting.CAS_NPN.value,
                DeviceSorting.CAS_NPE2.value,
                DeviceSorting.NFB.value,
                DeviceSorting.NVW.value,
                DeviceSorting.CAS_NFB.value,
                DeviceSorting.CAS_NVW.value,
            ]:
                print(
                    "Hot Water Setting Temperature: "
                    + str(stateData["hotWaterSettingTemperature"])
                    + " "
                    + u"\u00b0"
                    + "F"
                )
                if str(DeviceSorting(stateData["deviceSorting"]).name).startswith(
                    "CAS_"
                ):
                    print(
                        "Hot Water Average Temperature: "
                        + str(stateData["hotWaterAverageTemperature"])
                        + " "
                        + u"\u00b0"
                        + "F"
                    )
                    print(
                        "Inlet Average Temperature: "
                        + str(stateData["inletAverageTemperature"])
                        + " "
                        + u"\u00b0"
                        + "F"
                    )
                print(
                    "Hot Water Current Temperature: "
                    + str(stateData["hotWaterCurrentTemperature"])
                    + " "
                    + u"\u00b0"
                    + "F"
                )
                print(
                    "Hot Water Flow Rate: "
                    + str(
                        (self.bigHexToInt(stateData["hotWaterFlowRate"]) / 3.785) / 10.0
                    )
                    + " GPM"
                )
                print(
                    "Inlet Temperature: "
                    + str(stateData["hotWaterTemperature"])
                    + " "
                    + u"\u00b0"
                    + "F"
                )
                if "recirculationSettingTemperature" in stateData:
                    print(
                        "Recirculation Setting Temperature: "
                        + str(stateData["recirculationSettingTemperature"])
                        + " "
                        + u"\u00b0"
                        + "F"
                    )
                    print(
                        "Recirculation Current Temperature: "
                        + str(stateData["recirculationCurrentTemperature"])
                        + " "
                        + u"\u00b0"
                        + "F"
                    )
            # Only print these if CH is in use
            if stateData["deviceSorting"] in [
                DeviceSorting.NHB.value,
                DeviceSorting.CAS_NHB.value,
                DeviceSorting.NFB.value,
                DeviceSorting.NVW.value,
                DeviceSorting.CAS_NFB.value,
                DeviceSorting.CAS_NVW.value,
                DeviceSorting.NCB.value,
                DeviceSorting.NFC.value,
                DeviceSorting.NCB_H.value,
            ]:
                # Don't show the setting for cascaded devices, as it isn't applicable
                print(
                    "Heat Setting Temperature: "
                    + str(stateData["heatSettingTemperature"])
                    + " "
                    + u"\u00b0"
                    + "F"
                )
                if str(DeviceSorting(stateData["deviceSorting"]).name).startswith(
                    "CAS_"
                ):
                    print(
                        "Supply Average Temperature: "
                        + str(stateData["supplyAverageTemperature"])
                        + " "
                        + u"\u00b0"
                        + "F"
                    )
                    print(
                        "Return Average Temperature: "
                        + str(stateData["returnAverageTemperature"])
                        + " "
                        + u"\u00b0"
                        + "F"
                    )
                print(
                    "Current Supply Water Temperature: "
                    + str(stateData["currentWorkingFluidTemperature"])
                    + " "
                    + u"\u00b0"
                    + "F"
                )
                print(
                    "Current Return Water Temperature: "
                    + str(stateData["currentReturnWaterTemperature"])
                    + " "
                    + u"\u00b0"
                    + "F"
                )
        else:
            raise Exception("Error: Invalid temperatureType")

        print("Power Status: " + OnOFFFlag(stateData["powerStatus"]).name)
        print("Heat Status: " + OnOFFFlag(stateData["heatStatus"]).name)
        print("Use On Demand: " + OnDemandFlag(stateData["useOnDemand"]).name)
        print("Weekly Control: " + OnOFFFlag(stateData["weeklyControl"]).name)
        # Print the daySequences
        print("Day Sequences")
        for i in range(7):
            print("\t" + DayOfWeek(stateData["daySequences"][i]["dayOfWeek"]).name)
            if "daySequence" in stateData["daySequences"][i]:
                for j in stateData["daySequences"][i]["daySequence"]:
                    print(
                        "\t\tHour: "
                        + stateData["daySequences"][i]["daySequence"][j]["hour"]
                        + ", Minute: "
                        + stateData["daySequences"][i]["daySequence"][j]["minute"]
                        + ", "
                        + OnOFFFlag(
                            stateData["daySequences"][i]["daySequence"][j]["isOnOFF"]
                        ).name
                    )
            else:
                print("\t\tNone")

    # Print the trend sample response data
    def printTrendSample(self, trendSampleData, temperatureType):
        # print(json.dumps(trendSampleData, indent=2, default=str))
        print(
            "Controller Version: "
            + str(self.bigHexToInt(trendSampleData["controllerVersion"]))
        )
        print(
            "Panel Version: " + str(self.bigHexToInt(trendSampleData["pannelVersion"]))
        )
        print(
            "Device Model Type: " + DeviceSorting(trendSampleData["deviceSorting"]).name
        )
        print("Device Count: " + str(trendSampleData["deviceCount"]))
        print("Current Channel: " + str(trendSampleData["currentChannel"]))
        print("Device Number: " + str(trendSampleData["deviceNumber"]))
        print("Model Info: " + str(self.bigHexToInt(trendSampleData["modelInfo"])))
        print(
            "Total Operated Time: "
            + str(self.bigHexToInt(trendSampleData["totalOperatedTime"]))
        )
        # totalGasAccumulateSum needs to be converted based on the metric or imperial setting
        if temperatureType == TemperatureType.CELSIUS.value:
            print(
                "Total Gas Accumulated Sum: "
                + str(self.bigHexToInt(trendSampleData["totalGasAccumulateSum"]) / 10.0)
                + " m"
                + u"\u00b3"
            )
        else:
            print(
                "Total Gas Accumulated Sum: "
                + str(
                    (
                        self.bigHexToInt(trendSampleData["totalGasAccumulateSum"])
                        * 35.314667
                    )
                    / 10.0
                )
                + " ft"
                + u"\u00b3"
            )
        print(
            "Total Hot Water Accumulated Sum: "
            + str(self.bigHexToInt(trendSampleData["totalHotWaterAccumulateSum"]))
        )
        print(
            "Total Central Heating Operated Time: "
            + str(self.bigHexToInt(trendSampleData["totalCHOperatedTime"]))
        )
        if "totalDHWUsageTime" in trendSampleData:
            print(
                "Total Domestic Hot Water Usage Time: "
                + str(self.bigHexToInt(trendSampleData["totalDHWUsageTime"]))
            )

    # print the trend month or year response data
    def printTrendMY(self, trendMYData, temperatureType):
        # print(json.dumps(trendMYData, indent=2, default=str))
        print(
            "Controller Version: "
            + str(self.bigHexToInt(trendMYData["controllerVersion"]))
        )
        print("Panel Version: " + str(self.bigHexToInt(trendMYData["pannelVersion"])))
        print("Device Model Type: " + DeviceSorting(trendMYData["deviceSorting"]).name)
        print("Device Count: " + str(trendMYData["deviceCount"]))
        print("Current Channel: " + str(trendMYData["currentChannel"]))
        print("Device Number: " + str(trendMYData["deviceNumber"]))
        # Print the trend data
        for i in range(trendMYData["totalDaySequence"]):
            print(
                "\tIndex: "
                + str(self.bigHexToInt(trendMYData["trendSequences"][i]["dMIndex"]))
            )
            print(
                "\t\tModel Info: "
                + str(
                    self.bigHexToInt(
                        trendMYData["trendSequences"][i]["trendData"]["modelInfo"]
                    )
                )
            )
            print(
                "\t\tHot Water Operated Count: "
                + str(
                    self.bigHexToInt(
                        trendMYData["trendSequences"][i]["trendData"][
                            "hotWaterOperatedCount"
                        ]
                    )
                )
            )
            print(
                "\t\tOn Demand Use Count: "
                + str(
                    self.bigHexToInt(
                        trendMYData["trendSequences"][i]["trendData"][
                            "onDemandUseCount"
                        ]
                    )
                )
            )
            print(
                "\t\tHeat Accumulated Use: "
                + str(
                    self.bigHexToInt(
                        trendMYData["trendSequences"][i]["trendData"][
                            "heatAccumulatedUse"
                        ]
                    )
                )
            )
            print(
                "\t\tDomestic Hot Water Accumulated Use: "
                + str(
                    self.bigHexToInt(
                        trendMYData["trendSequences"][i]["trendData"][
                            "dHWAccumulatedUse"
                        ]
                    )
                )
            )
            if temperatureType == TemperatureType.CELSIUS.value:
                print(
                    "\t\tTotal Gas Usage: "
                    + str(
                        self.bigHexToInt(
                            trendMYData["trendSequences"][i]["trendData"][
                                "gasAccumulatedUse"
                            ]
                        )
                        / 10.0
                    )
                    + " m"
                    + u"\u00b3"
                )
                print(
                    "\t\tHot water Accumulated Use: "
                    + str(
                        self.bigHexToInt(
                            trendMYData["trendSequences"][i]["trendData"][
                                "hotWaterAccumulatedUse"
                            ]
                        )
                        / 10.0
                    )
                    + " L"
                )
                print(
                    "\t\tOutdoor Air Max Temperature: "
                    + str(
                        trendMYData["trendSequences"][i]["trendData"][
                            "outdoorAirMaxTemperature"
                        ]
                        / 2.0
                    )
                    + " "
                    + u"\u00b0"
                    + "C"
                )
                print(
                    "\t\tOutdoor Air Min Temperature: "
                    + str(
                        trendMYData["trendSequences"][i]["trendData"][
                            "outdoorAirMinTemperature"
                        ]
                        / 2.0
                    )
                    + " "
                    + u"\u00b0"
                    + "C"
                )
            elif temperatureType == TemperatureType.FAHRENHEIT.value:
                print(
                    "\t\tTotal Gas Usage: "
                    + str(
                        (
                            self.bigHexToInt(
                                trendMYData["trendSequences"][i]["trendData"][
                                    "gasAccumulatedUse"
                                ]
                            )
                            * 35.314667
                        )
                        / 10.0
                    )
                    + " ft"
                    + u"\u00b3"
                )
                print(
                    "\t\tHot water Accumulated Use: "
                    + str(
                        (
                            self.bigHexToInt(
                                trendMYData["trendSequences"][i]["trendData"][
                                    "hotWaterAccumulatedUse"
                                ]
                            )
                            / 3.785
                        )
                        / 10.0
                    )
                    + " G"
                )
                print(
                    "\t\tOutdoor Air Max Temperature: "
                    + str(
                        trendMYData["trendSequences"][i]["trendData"][
                            "outdoorAirMaxTemperature"
                        ]
                    )
                    + " "
                    + u"\u00b0"
                    + "F"
                )
                print(
                    "\t\tOutdoor Air Min Temperature: "
                    + str(
                        trendMYData["trendSequences"][i]["trendData"][
                            "outdoorAirMinTemperature"
                        ]
                    )
                    + " "
                    + u"\u00b0"
                    + "F"
                )
            else:
                raise Exception("Error: Invalid temperatureType")

    # Convert from a list of big endian hex byte array or string to an integer
    def bigHexToInt(self, hex):
        if isinstance(hex, str):
            hex = bytearray(hex)
        if isinstance(hex, int):
            # This is already an int, just return it
            return hex
        bigEndianStr = "".join("%02x" % b for b in hex)
        littleHex = bytearray.fromhex(bigEndianStr)
        littleHex.reverse()
        littleHexStr = "".join("%02x" % b for b in littleHex)
        return int(littleHexStr, 16)

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
            ControlSorting.INFO.value,
            ControlType.STATE.value,
            0x00,
            0x00,
            self.initWeeklyDay(),
        )

    # Send channel information request (we already get this when we log in)
    def sendChannelInfoRequest(self, gatewayID, currentControlChannel, deviceNumber):
        return self.sendRequest(
            gatewayID,
            currentControlChannel,
            deviceNumber,
            ControlSorting.INFO.value,
            ControlType.CHANNEL_INFORMATION.value,
            0x00,
            0x00,
            self.initWeeklyDay(),
        )

    # Send trend sample request
    def sendTrendSampleRequest(self, gatewayID, currentControlChannel, deviceNumber):
        return self.sendRequest(
            gatewayID,
            currentControlChannel,
            deviceNumber,
            ControlSorting.INFO.value,
            ControlType.TREND_SAMPLE.value,
            0x00,
            0x00,
            self.initWeeklyDay(),
        )

    # Send trend month request
    def sendTrendMonthRequest(self, gatewayID, currentControlChannel, deviceNumber):
        return self.sendRequest(
            gatewayID,
            currentControlChannel,
            deviceNumber,
            ControlSorting.INFO.value,
            ControlType.TREND_MONTH.value,
            0x00,
            0x00,
            self.initWeeklyDay(),
        )

    # Send trend year request
    def sendTrendYearRequest(self, gatewayID, currentControlChannel, deviceNumber):
        return self.sendRequest(
            gatewayID,
            currentControlChannel,
            deviceNumber,
            ControlSorting.INFO.value,
            ControlType.TREND_YEAR.value,
            0x00,
            0x00,
            self.initWeeklyDay(),
        )

    # Send device power control request
    def sendPowerControlRequest(
        self, gatewayID, currentControlChannel, deviceNumber, powerState
    ):
        return self.sendRequest(
            gatewayID,
            currentControlChannel,
            deviceNumber,
            ControlSorting.CONTROL.value,
            ControlType.UNKNOWN.value,
            DeviceControl.POWER.value,
            OnOFFFlag(powerState).value,
            self.initWeeklyDay(),
        )

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

    # The following needs to be reviewed and revised once the core control functions are all added
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
