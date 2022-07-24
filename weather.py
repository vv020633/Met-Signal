#!/usr/bin/python3

import http.client
import json
import os
import phue
import pprint
import time

from phue import Bridge
from datetime import datetime


#API ID and secret to speak to the metoffer API. This will be your own values
client_id = os.environ.get('METOFFICE_CLIENT_ID')
client_secret = os.environ.get('METOFFICE_CLIENT_SECRET')
latitude = '51.3142851'
longitude = '-0.5505251'

auto_brightness_value = 15

precipitation_values = {'hue' : 55000, 'saturation': 254, 'transitiontime': 30}
snow_values = {'hue' : 40000, 'saturation': 200, 'transitiontime': 30}
heavyrain_values = {'hue' : 50000, 'saturation': 254, 'transitiontime': 5}
heavysnow_values = {'hue' : 47500, 'saturation': 254, 'transitiontime': 5}

hot_value = {'hue' : 1000, 'saturation': 254,}
warm_value = {'hue' : 10000, 'saturation': 254,}
fair_value = {'hue' : 30000, 'saturation': 254,}
cold_value = {'hue' : 40000, 'saturation': 200}
freezing_value = {'hue' : 47500, 'saturation': 254}


#If the threshold crosses 50 percent, then we expect it is likely for it to rain or snow
probabilityOfPrecipitationThreshold = 50
probabilityOfHeavyRainThreshold = 50
ProbabilityOfSnowThreshold = 50
ProbabilityOfHeavySnowThreshold = 50

# weather is freezing if minTemp is below 0
# weather is cold if minTemp is  > 0 and below 10
# weather is fair if mintemp > 10 and below 20
#weather is warm if maxTemp > 20 and below 25
#weather is hot if maxTemp >=25

def classifyTemperature(minTemperature, maxTemperature):
    if minTemperature <= 0:
        return "Freezing"
    elif minTemperature < 10:
        return "Cold"
    # to define anything more than cold, we look at the maximum temperature within the day
    elif maxTemperature >= 10 and maxTemperature < 20:
        return "Fair"
    elif maxTemperature >= 20 and maxTemperature < 25:
        return "Warm"
    elif maxTemperature >= 25:
        return "Hot"

#Call the weather API and get the weather for the next few hours
def determineWeather():
   
    conn = http.client.HTTPSConnection("api-metoffice.apiconnect.ibmcloud.com")
    headers = {
        'x-ibm-client-id': client_id,
        'x-ibm-client-secret': client_secret,
        'accept': "application/json"
    }
    

    conn.request("GET",
                 "/metoffice/production/v0/forecasts/point/daily?excludeParameterMetadata=false&includeLocationName=true&latitude={}&longitude={}".format(
                     latitude, longitude), headers=headers)

    res = conn.getresponse()
    data = res.read()

    weather = json.loads(data.decode("utf-8"))
    
    # print(weather)
    
    precipitation = False
    snow = False
    heavyRain = False
    heavySnow = False
    minTemperature = None
    maxTemperature = None
    timeForecast=[]
    
    timeForecast = weather['features'][0]['properties']['timeSeries']

    for key, value in timeForecast[2].items():
        
        if key == 'dayProbabilityOfPrecipitation':
            probabilityOfPrecipitation = value
            if probabilityOfPrecipitation >= probabilityOfPrecipitationThreshold:
                precipitation = True
        if key == 'dayProbabilityOfHeavyRain':
            dayProbabilityOfHeavyRain = value
            if dayProbabilityOfHeavyRain >= probabilityOfHeavyRainThreshold:
                heavyRain = True
        if key == 'dayProbabilityOfHeavySnow':
            dayProbabilityOfHeavySnow = value
            if dayProbabilityOfHeavySnow >= ProbabilityOfHeavySnowThreshold:
                heavySnow = True

        if key == 'dayProbabilityOfSnow':
            dayProbabilityOfSnow = value
            if dayProbabilityOfSnow >= ProbabilityOfSnowThreshold:
                snow = True
        
        if key == 'dayMaxFeelsLikeTemp':
            temperature = value
        
            if (not minTemperature or temperature < minTemperature ):
                minTemperature = temperature

            if (not maxTemperature or temperature > maxTemperature ):
                maxTemperature = temperature

    temperatureCode = classifyTemperature(minTemperature, maxTemperature)
    return {"precipitation": precipitation, "snow": snow,  "heavyRain": heavyRain, "heavySnow": heavySnow, "temperatureCode": temperatureCode }

def setupWeatherFlow(weather):

    if weather['temperatureCode'] == "Hot":
        setLamp(hot_value)
    elif weather['temperatureCode'] == "Warm":
        setLamp(warm_value)
    elif weather['temperatureCode'] == "Fair":
        setLamp(fair_value)
    elif weather['temperatureCode'] == "Cold":
        setLamp(cold_value)
    elif weather['temperatureCode'] == "Freezing":
        setLamp(freezing_value)

    if weather["precipitation"]:
        
        if weather["heavySnow"]:
             pulseLight(heavysnow_values) 

        elif weather["heavyRain"]:
            pulseLight(heavyrain_values) 

        elif weather["snow"]:
            pulseLight(snow_values) 

        else:
            pulseLight(precipitation_values)
    
    else:
        if weather['temperatureCode'] == "Hot":
            setLight(hot_value)
        elif weather['temperatureCode'] == "Warm":
            setLight(warm_value)
        elif weather['temperatureCode'] == "Fair":
            setLight(fair_value)
        elif weather['temperatureCode'] == "Cold":
            setLight(cold_value)
        elif weather['temperatureCode'] == "Freezing":
            setLight(freezing_value)

def bridgeConnect():
    try:
        bridge_ip_addr = os.environ.get('BRIDGE_IP_ADDRESS')
        bridge = Bridge(bridge_ip_addr)

        bridge.connect()
    except:
        print('Unable to connect to Bridge. Please double-check your connectivity to the Bridge')
    light_names = bridge.get_light_objects('id') 
       
    
    # print(light_names)
    return light_names   

def pulseLight(weather_values):    #Pass in the dictionary of the relevant weather type

    light_names = bridgeConnect()
    
    transitiontime = weather_values['transitiontime']
    hue_value = weather_values['hue']
    saturation_value = weather_values['saturation']
    pulse_start = time.time()

    while True:

        light_names[1].transitiontime = transitiontime
        light_names[1].on = True
        light_names[1].hue = hue_value
        light_names[1].saturation = saturation_value
        light_names[1].brightness = auto_brightness_value

        time.sleep(4)
        light_names[1].transitiontime = transitiontime
        light_names[1].on = False

        time.sleep(4)

        if  time.time() - pulse_start >= five_mins:
            # lightsOff(light_names)
            break
        # User takes control of lights, then end the script        
        elif light_names[1].brightness > auto_brightness_value:
            break

        else:
            continue

#Set the Lamp to a certain color based on the weather input
def setLamp(weather_values):
    
    light_names = bridgeConnect()
    hue_value = weather_values['hue']
    saturation_value = weather_values['saturation']
    light_names[3].on = True
    light_names[3].hue = hue_value
    light_names[3].saturation = saturation_value
    light_names[3].brightness = auto_brightness_value


#Set the Light to a certain color based on the weather input
def setLight(weather_values):
    
    light_names = bridgeConnect()
    hue_value = weather_values['hue']
    saturation_value = weather_values['saturation']
    light_names[1].on = True
    light_names[1].hue = hue_value
    light_names[1].saturation = saturation_value
    light_names[1].brightness = auto_brightness_value 

def getCurrentTime():

    current_time=time.localtime()        
    current_time_hour = int(current_time.tm_hour)
    current_time_min = int(current_time.tm_min)
    return current_time_min, current_time_hour

def lightsOff(lights):
    lights[1].on = False
    lights[3].on = False

current_time_min, current_time_hour = getCurrentTime()       
five_mins = 300 #5 minutes in seconds
on_switch_count = 0
weather = determineWeather()

while current_time_hour < 9: #This script runs until 9:00 AM

    #Set lights to default 0 brightness
    light_names = bridgeConnect()
    #User manual override
    if on_switch_count >= 2:
        break

    current_time_min, current_time_hour = getCurrentTime() 
    # print(str(current_time_hour) + ' : ' +str(current_time_min) )
    if current_time_min == 30 or current_time_min == 59: # If its on the hour or half past the hour
        start_time = time.time() 
        setupWeatherFlow(weather)
        five_min_loop = True
        light_names = bridgeConnect()
         # User takes control of lights, then end the script        
        
        while five_min_loop == True:
            if time.time() - start_time >= five_mins:
                lightsOff(light_names)
                five_min_loop = False
                
 
            # User takes control of lights, then end the script        
            elif light_names[3].brightness > auto_brightness_value or light_names[1].brightness > auto_brightness_value:
                on_switch_count+=1
                five_min_loop = False  
            else:
                continue  
    # User takes control of lights, then end the script, but only if the brightness has been increased during the length of this script        
    elif light_names[3].on == True or light_names[1].on == True:
        
        if on_switch_count >=2 :
            if light_names[3].brightness > auto_brightness_value or light_names[1].brightness > auto_brightness_value:
                break
            else:
                continue
        # This is the case of the switch count has been increased once before, in which case we'll increase the switch count to end the script    
        elif on_switch_count == 1:
            on_switch_count+=1
            continue
        # The lights were initially on and then switched off due to this script, in which case the switch count is increased
        else:
            light_names[3].brightness = auto_brightness_value
            light_names[1].brightness = auto_brightness_value
            lightsOff(light_names)
            on_switch_count+=1
            continue
    else:
        continue
      

