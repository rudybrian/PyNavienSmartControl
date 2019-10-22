#!/usr/bin/env python

# Support Python3 in Python2.
from __future__ import print_function

# The NavienSmartControl code is in a library.
from shared.NavienSmartControl import NavienSmartControl, ModeState, OperateMode, HeatLevel

# The credentials are loaded from a separate file.
import json

# We support command line arguments.
import argparse

# We use the system package for interaction with the OS.
import sys

# This script's version.
version = 0.1

# Check the user is invoking us directly rather than from a module.
if __name__ == '__main__':
 
 # Output program banner.
 print('--------------')
 print('Navien-API V' + str(version))
 print('--------------')
 print()

 # Get an initialised parser object.
 parser = argparse.ArgumentParser(description='Control a Navien boiler.', prefix_chars='-/')
 parser.add_argument('/roomtemp', '-roomtemp', type=float, help='Set the indoor room temperature to this value.')
 parser.add_argument('/heatingtemp', '-heatingtemp', type=float, help='Set the central heating temperature to this value.')
 parser.add_argument('/hotwatertemp', '-hotwatertemp', type=float, help='Set the hot water temperature to this value.')
 parser.add_argument('/heatlevel', '-heatlevel', type=int, choices={1,2,3}, help='Set the boiler\'s heat level.')
 parser.add_argument('/status', '-status', action='store_true', help='Show the boiler\'s simple status.')
 parser.add_argument('/summary', '-summary', action='store_true', help='Show the boiler\'s extended status.')
 parser.add_argument('/mode', '-mode', choices={'PowerOff', 'PowerOn', 'HolidayOn', 'HolidayOff', 'SummerOn', 'SummerOff', 'QuickHotWater'}, help='Set the boiler\'s mode.')

 # The following function provides arguments for calling functions when command line switches are used.
 args = parser.parse_args()
 
 # Were arguments specified?
 if len(sys.argv)==1:
  parser.print_help(sys.stderr)
 
 # Yes, there was. 
 else:

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

   # Connect to the socket.
   homeState = navienSmartControl.connect(gatewayList[0])

   # We can provide a full summary.
   if args.summary:
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

    # Print out the current status.
    navienSmartControl.printHomeState(homeState)
    print()

   # We provide a quick status.
   if args.status:

    print('Current Mode: ', end = '')
    if homeState.currentMode == ModeState.POWER_OFF.value:
     print('Powered Off')
    elif homeState.currentMode == ModeState.GOOUT_ON.value:
     print('Holiday Mode')
    elif homeState.currentMode == ModeState.INSIDE_HEAT.value:
     print('Room Temperature Control')
    elif homeState.currentMode == ModeState.ONDOL_HEAT.value:
     print('Central Heating Control')
    elif homeState.currentMode == ModeState.SIMPLE_RESERVE.value:
     print('Heating Inteval')
    elif homeState.currentMode == ModeState.CIRCLE_RESERVE.value:
     print('24 Hour Program')
    elif homeState.currentMode == ModeState.HOTWATER_ON.value:
     print('Hot Water Only')
    else:
     print(str(homeState.currentMode))
    print('Current Operation: ' + ('Active' if homeState.operateMode & OperateMode.ACTIVE.value else 'Inactive'))
    print()

    print('Room Temperature : ' + str(navienSmartControl.getTemperatureFromByte(homeState.currentInsideTemp))+ ' °C')
    print()

    if homeState.currentMode == ModeState.INSIDE_HEAT.value:
     print('Inside Heating Temperature: ' + str(navienSmartControl.getTemperatureFromByte(homeState.insideHeatTemp)) + ' °C')
    elif homeState.currentMode == ModeState.ONDOL_HEAT.value:
     print('Central Heating Temperature: ' + str(navienSmartControl.getTemperatureFromByte(homeState.ondolHeatTemp)) + ' °C')

    print('Hot Water Set Temperature : ' + str(navienSmartControl.getTemperatureFromByte(homeState.hotWaterSetTemp)) + ' °C')

   # Change the mode.
   if args.mode:

    # Various allowed mode toggles.
    if args.mode == 'PowerOff':
     navienSmartControl.setPowerOff(homeState)
    elif args.mode == 'PowerOn':
     navienSmartControl.setPowerOn(homeState)
    elif args.mode == 'HolidayOn':
     navienSmartControl.setGoOutOn(homeState)
    elif args.mode == 'HolidayOff':
     navienSmartControl.setGoOutOff(homeState)
    elif args.mode == 'SummerOn':
     navienSmartControl.setHotWaterOn(homeState)
    elif args.mode == 'SummerOff':
     navienSmartControl.setHotWaterOff(homeState)
    elif args.mode == 'QuickHotWater':
     navienSmartControl.setQuickHotWater(homeState)

    # Update user.
    print('Mode now set to ' + str(args.mode) + '.')

   # Change the heat level.
   if args.heatlevel:
    navienSmartControl.setHeatLevel(homeState, HeatLevel(args.heatlevel))
    print('Heat level now set to ' + str(HeatLevel(args.heatlevel)) + '.')

   # Change the room temperature.
   if args.roomtemp:
    navienSmartControl.setInsideHeat(homeState, args.roomtemp)
    print('Indoor temperature now set to ' + str(args.roomtemp) + '°C.')

   # Change the central heating system's temperature.
   if args.heatingtemp:
    navienSmartControl.setOndolHeat(homeState, args.heatingtemp)
    print('Central heating temperature now set to ' + str(args.heatingtemp) + '°C.')

   # Change the room temperature.
   if args.hotwatertemp:
    navienSmartControl.setHotWaterHeat(homeState, args.hotwatertemp)
    print('Hot water temperature now set to ' + str(args.hotwatertemp) + '°C.')

  else:
   raise ValueError('Bad gateway list returned.')