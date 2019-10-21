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

class OperateMode(enum.Enum):
 POWEROFF = 1
 POWERON = 2
 GOOUTOFF = 3
 GOOUTON = 4
 INSIDEHEAT = 5
 ONDOLHEAT = 6
 REPEATRESERVE = 7
 CIRCLERESERVE = 8
 SIMPLERESERVE = 9
 HOTWATERON = 10
 HOTWATEROFF = 11
 WATERSETTEMP = 12
 QUICKHOTWATER = 13
 HEATTYPE = 14
 HEATING = 128

class ModeState(enum.Enum):
 POWEROFF = 1
 GOOUTON = 2
 INSIDEHEAT = 3
 ONDOLHEAT = 4
 SIMPLERESERVE = 5
 CIRCLERESERVE = 6
 HOTWATERON = 8

class HeatType(enum.Enum):
 LOW = 1
 MEDIUM = 2
 HIGH = 3
 
class TempControlType(enum.IntFlag):
 Unknown1 = enum.auto()
 Unknown2 = enum.auto()
 Unknown3 = enum.auto()
 Unknown4 = enum.auto()
 ONDOLHEAT = enum.auto()
 INSIDEHEAT = enum.auto()
 Unknown7 = enum.auto()
 Unknown8 = enum.auto()

class NavienSmartControl:

 # This prevents the requests module from creating its own user-agent.
 stealthyHeaders = {'User-Agent': None }

 # The Navien server.
 navienServer = 'ukst.naviensmartcontrol.com'
 navienWebServer = 'https://' + navienServer
 navienServerSocketPort = 6001
 
 def __init__(self, userID, passwd):
  self.userID = userID
  self.passwd = passwd
  self.connection = None

 def login(self):
  # Login.
  response = requests.post(NavienSmartControl.navienWebServer + '/mobile_login_check.asp', headers=NavienSmartControl.stealthyHeaders, data={'UserID': self.userID, 'Passwd': self.passwd, 'BundleVersion': '8', 'AutoLogin': '1', 'smartphoneID': '2'})

  # If an error occurs this will raise it, otherwise it returns the encodedUserID (this is just the BASE64 UserID typically).
  return self.handleResponse(response)

 # This is the list of boiler controllers or "gateways". Note how no login state is required.
 def gatewayList(self, encodedUserID):
  # Get the list of connected devices.
  response = requests.post(NavienSmartControl.navienWebServer + '/mobile_gateway_list.asp', headers=NavienSmartControl.stealthyHeaders, data={'UserID': encodedUserID, 'Ticket':'0'})

  # The server replies with a pipe separated response.
  return self.handleResponse(response)

 def handleResponse(self, response):

  # The server replies with a pipe separated response.
  response_status = response.text.split('|')

  # The first value is either a status code or sometimes a raw result.
  response_status_code = response_status[0]

  if response_status_code == '0':
   raise Exception('Error: Controller not connected to the Internet server; please check your Wi-Fi network and wait until the connection to the Internet server is restored automatically.')
  elif response_status_code == '1':
   raise Exception('Error: Login details incorrect. Please note, these are case-sensitive.')
  elif response_status_code == '2':
   raise Exception('Error: The ID you have chosen is already in use.')
  elif response_status_code == '3':
   return response_status[1]
  elif response_status_code == '4':
   raise Exception('Error: Invalid ID.')
  elif response_status_code == '9':
   raise Exception('Error: The Navien TOK account you have chosen is already in use by other users. Try again later.')
  elif response_status_code == '201':
   raise Exception('Error: The software is updated automatically and a continuous internet connection is required for this. If the router is not on continually, updates may be missed.')
  elif response_status_code == '202':
   if len(response_status) == 2:
    raise Exception('Error: Service inspection. Please wait until the inspection is done and try again. (Inspection hour:' + response_status[1] + ')')
   else:
    raise Exception('Error: Service inspection. Please wait until the inspection is done and try again.')
  elif response_status_code == '203':
   raise Exception('Error: Shutting down the service. Thank you for using this service. Closing the current program.')
  elif response_status_code == '210':
   raise Exception('Error: This version is too old.')
  elif response_status_code == '999':
   raise Exception('Error: Sorry. Please try again later.')
  else:
   return response_status
 
 def connect(self, controllerMACAddress):

  # Construct a socket object.
  self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

  # Connect to the socket server.
  self.connection.connect((NavienSmartControl.navienServer, NavienSmartControl.navienServerSocketPort))

  # Request the boiler status.
  self.connection.sendall((self.userID + '$' + 'iPhone1.0' + '$' + controllerMACAddress + '\n').encode())

  # Receive the boiler status.
  data = self.connection.recv(1024)

  # Return the parsed home state data.
  return self.parseHomeState(data)

 def parseHomeState(self, data):

  # The data is returned with a fixed header for the first 42 bytes.
  homeStateColumns = collections.namedtuple('homeState', ['serialnum','code','hwRev','swRev','netType','controlType','boilerModelType','roomCnt','smsFg','errorCode','hotWaterSetTemp','heatType','optionUseFg','modeState','insideTemp','heatSetTemp','ondolSetTemp','repeatReserveSetTime','repeatReserveSetMinute','circleReserveSetTime1','circleReserveSetTime2','circleReserveSetTime3','simpleReserveSetTime','simpleReserveSetMinute','operateMode','tempControlType','hotwaterMin','hotwaterMax','ondolMin','ondolMax','insideMin','insideMax','reserve09', 'reserve10'])
  homeState = homeStateColumns._make(struct.unpack('          8s        B      B       B        B          B               B              B        B         H              B             B            B            B           B            B              B               B                      B                        B                          B                           B                       B                      B                B              B               B             B            B          B            B         B           B              B', data[:42]))

  # If the roomCnt > 1 then the remaining data will be room state information.
  if len(data) > 42:
   print('Warning : Extra roomState data found but not implemented in this version.')
 
  # These are hardcoded values to watch out for.
  if data == binascii.unhexlify('444444444400000000000000000000') or data == binascii.unhexlify('04040404040404040404'):
   raise Exception('An error occurs in the process of retrieving data. Please restart for use')

  # Return the resulting parsed data.
  return homeState

 def printHomeState(self, homeState):
  print('Serial Number: ' + ':'.join('%02x' % b for b in homeState.serialnum))
  print('Code?: ' + str(homeState.code))
  print('Hardware Revision: V' + str(homeState.hwRev))
  print('Software Version: V' + str(homeState.swRev) + '.0')
  print('Network Type: ' + str(homeState.netType))
  print('Controller Type?: ' + str(homeState.controlType))
  print('Boiler Model Type: ' + str(homeState.boilerModelType))
  print('Room Controllers: ' + str(homeState.roomCnt))
  print('smsFg?: ' + str(homeState.smsFg))
  print('Error: ' + ('No Error' if homeState.errorCode == 0 else homeState.errorCode))
  print('Hot Water Set Temperature: ' + str(self.getTemperatureFromByte(homeState.hotWaterSetTemp)) + ' °C')
  print('Heat Intensity Type: ' + [ 'Unknown', 'Low', 'Medium', 'High' ][homeState.heatType])
  print('Option Use Flags: ' + bin(homeState.optionUseFg) + (' (Hot Water System)' if not homeState.optionUseFg & 32 else ''))

  print('Mode State: ', end = '')
  if homeState.modeState == ModeState.POWEROFF.value:
   print('Powered Off')
  elif homeState.modeState == ModeState.GOOUTON.value:
   print('Holiday Mode')
  elif homeState.modeState == ModeState.INSIDEHEAT.value:
   print('Room Temperature Control')
  elif homeState.modeState == ModeState.ONDOLHEAT.value:
   print('Central Heating Control')
  elif homeState.modeState == ModeState.SIMPLERESERVE.value:
   print('Heating Inteval')
  elif homeState.modeState == ModeState.CIRCLERESERVE.value:
   print('24 Hour Program')
  elif homeState.modeState == ModeState.HOTWATERON.value:
   print('Hot Water Only')
  else:
   print(str(homeState.modeState))

  print('Current Room Temperature: ' + str(self.getTemperatureFromByte(homeState.insideTemp)) + ' °C')
  print('Room Heating Set Temperature: ' + str(self.getTemperatureFromByte(homeState.heatSetTemp)) + ' °C')
  print('Central Heating Temperature: ' + str(self.getTemperatureFromByte(homeState.ondolSetTemp)) + ' °C')
  print()
  print('Heating Timer Interval: Every ' + str(homeState.repeatReserveSetTime) + ' hour(s)')
  print('Heating Timer Duration: ' + str(homeState.repeatReserveSetMinute) + ' minute(s)')
  print()
  print('Heating Schedule (00-08h): ' + bin(homeState.circleReserveSetTime1))
  print('Heating Schedule (09-16h): ' + bin(homeState.circleReserveSetTime2))
  print('Heating Schedule (17-24h): ' + bin(homeState.circleReserveSetTime3))
  print()
  print('simpleReserveSetTime: ' + str(homeState.simpleReserveSetTime))
  print('simpleReserveSetMinute: ' + str(homeState.simpleReserveSetMinute))
  print()
  print('Operation Mode Flags: ' + bin(homeState.operateMode) + (' (Heating)' if homeState.operateMode & OperateMode.HEATING.value else ''))
  print()
  print('Temperature Control Supported Types: ' + bin(homeState.tempControlType))
  if TempControlType.Unknown1 & homeState.tempControlType: print(' (Unknown1)')
  if TempControlType.Unknown2 & homeState.tempControlType: print(' (Unknown2)')
  if TempControlType.Unknown3 & homeState.tempControlType: print(' (Unknown3)')
  if TempControlType.Unknown4 & homeState.tempControlType: print(' (Unknown4)')
  if TempControlType.ONDOLHEAT & homeState.tempControlType: print(' (ONDOLHEAT)')
  if TempControlType.INSIDEHEAT & homeState.tempControlType: print(' (INSIDEHEAT)')
  if TempControlType.Unknown7 & homeState.tempControlType: print(' (Unknown7)')
  if TempControlType.Unknown8 & homeState.tempControlType: print(' (Unknown8)')
  print()
  print('Hot Water Temperature Supported Range: ' + str(self.getTemperatureFromByte(homeState.hotwaterMin)) + ' °C - ' + str(self.getTemperatureFromByte(homeState.hotwaterMax)) + ' °C')
  print('Central Heating Temperature Supported Range: ' + str(self.getTemperatureFromByte(homeState.ondolMin)) + ' °C - ' + str(self.getTemperatureFromByte(homeState.ondolMax)) + ' °C')
  print('Room Temperature Supported Range: ' + str(self.getTemperatureFromByte(homeState.insideMin)) + ' °C - ' + str(self.getTemperatureFromByte(homeState.insideMax)) + ' °C')
  print()
  print('Reserved 09: ' + str(homeState.reserve09))
  print('Reserved 10: ' + str(homeState.reserve10))

 def getTemperatureByte(self, temperature):
  return int(2.0 * temperature)

 def getTemperatureFromByte(self, temperatureByte):
  return float((temperatureByte >> 1) + (0.5 if temperatureByte & 1 else 0))

 def setOperationMode(self, homeState, operateMode, value01, value02, value03, value04, value05):

  commandListSequence = 0
  commandListCommand = 131
  commandListDataLength = 21
  commandListCount = 0

  sendData = bytearray([commandListSequence, commandListCommand, commandListDataLength, commandListCount])
  sendData.extend(homeState.serialnum)

  commandSequence = 1
  sendData.extend([commandSequence, operateMode.value, value01, value02, value03, value04, value05]);

  self.connection.sendall(sendData)

 # ------ Set OperationMode convenience methods --------- #

 def setPowerOff(self, homeState):
  return self.setOperationMode(homeState, OperateMode.POWEROFF, 1, 0, 0, 0, 0)

 def setPowerOn(self, homeState):
  return self.setOperationMode(homeState, OperateMode.POWERON, 1, 0, 0, 0, 0)

 def setGoOutOff(self, homeState):
  return self.setOperationMode(homeState, OperateMode.GOOUTOFF, 1, 0, 0, 0, 0)

 def setGoOutOn(self, homeState):
  return self.setOperationMode(homeState, OperateMode.GOOUTON, 1, 0, 0, 0, 0)

 def setInsideHeat(self, homeState, temperature):
  if (temperature < homeState.insideMin or temperature > homeState.insideMax): raise ValueError('Temperature specified is outside the boiler\'s supported range.')
  return self.setOperationMode(homeState, OperateMode.INSIDEHEAT, 1, 0, 0, 0, self.getTemperatureByte(temperature))

 def setOndolHeat(self, homeState, temperature):
  if (temperature < homeState.ondolMin or temperature > homeState.ondolMax): raise ValueError('Temperature specified is outside the boiler\'s supported range.')
  return self.setOperationMode(homeState, OperateMode.ONDOLHEAT, 1, 0, 0, 0, self.getTemperatureByte(temperature))

 def setRepeatReserve(self, homeState, hourInterval, durationMinutes):
  return self.setOperationMode(homeState, OperateMode.REPEATRESERVE, 1, 0, 0, hourInterval, durationMinutes)

 def setCircleReserve(self, homeState, schedule1, schedule2, schedule3):
  return self.setOperationMode(homeState, OperateMode.CIRCLERESERVE, 1, 0, schedule1, schedule2, schedule3)

 def setHotWaterOn(self, homeState):
  return self.setOperationMode(homeState, OperateMode.HOTWATERON, 1, 0, 0, 0, 0)

 def setHotWaterOff(self, homeState):
  return self.setOperationMode(homeState, OperateMode.HOTWATEROFF, 1, 0, 0, 0, 0)

 def setHotWaterHeat(self, homeState, temperature):
  if (temperature < homeState.hotwaterMin or temperature > homeState.hotwaterMax): raise ValueError('Temperature specified is outside the boiler\'s supported range.')
  return self.setOperationMode(homeState, OperateMode.WATERSETTEMP, 1, 0, 0, 0, self.getTemperatureByte(temperature))

 def setQuickHotWater(self, homeState):
  return self.setOperationMode(homeState, OperateMode.QUICKHOTWATER, 1, 0, 0, 0, 0)

 def setHeatType(self, homeState, heatType):
  return self.setOperationMode(homeState, OperateMode.HEATTYPE, 1, 0, 0, 0, heatType.value)