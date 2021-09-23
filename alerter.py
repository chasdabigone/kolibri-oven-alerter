# Download the helper library from https://www.twilio.com/docs/python/install
import os
import time
import json, yaml
from twilio.rest import Client
from pytezos import pytezos


# Load config
filename = 'alert_config.yaml'
with open(filename) as f:
    
    config = yaml.load(f, Loader=yaml.Loader) # Assume tickers in yaml file are in uppercase
    

oven = pytezos.using(config['Tezos Node'])
oven = oven.contract(config['Oven Address'])
minter = pytezos.using(config['Tezos Node'])
minter = minter.contract('KT1Ty2uAmF5JxWyeGrVpk17MEyzVB8cXs8aJ')

def get_oven():
    global ovenRatio
    global alertRatio
    global harbingerPrice
    global liqPrice
    #fetch harbinger oracle price
    harbinger = pytezos.using(config['Tezos Node'])
    harbinger = harbinger.contract('KT1Jr5t9UvGiqkvvsuUbPJHaYx24NzdUwNW9')
    harbingerPrice = harbinger.storage['oracleData']['XTZ-USD']()[5]
    harbingerPrice = (harbingerPrice / 1e6)

    #fetch oven data
    ovenBalance = oven.context.get_balance() / 1e6
    ovenBorrowed = oven.storage['borrowedTokens']() / 1e18
    ovenCurrentFee = oven.storage['stabilityFeeTokens']() / 1e18
    ovenInterest = oven.storage['interestIndex']() / 1e18
    collateralizationRatio = minter.storage['collateralizationPercentage']() / 1e20

    #calculate oven stuff
    ovenCollateralValue = ovenBalance * harbingerPrice
    ovenLiquidationAmount = ovenCollateralValue / collateralizationRatio
    ovenRatio = ovenCollateralValue / (ovenBorrowed + ovenCurrentFee)

    
    liqPrice = harbingerPrice * collateralizationRatio / ovenRatio
    alertRatio = config['Alert Percentage'] / 100

get_oven()

    

def send_alert():
    # Find your Account SID and Auth Token at twilio.com/console
    # and set the environment variables. See http://twil.io/secure
    client = Client(config['Twilio SID'], config['Twilio Auth Token'])

    message = client.messages \
                    .create(
                         body="Alert! XTZ Price is " + str(round(harbingerPrice, 2)) + " and your liquidation price is " + str(round(liqPrice, 2)) + ". Your current collateralization is " + str(int(round(ovenRatio * 100, 0))) + "%",
                         from_=config['Twilio Phone Number'],
                         to=config['Recipient Phone Number']
                     )

def oven_loop():
    while ovenRatio > alertRatio:
        
        get_oven()
        print ("oven ratio is " + str(round(ovenRatio*100)) + "% ... safe. Refreshing in " + str(config['Refresh Rate (seconds)']) + " seconds")
        time.sleep(config['Refresh Rate (seconds)'])
    else:
        print ("oven ratio is under alert ratio. ALERTING")
        send_alert()
        if config['Continuous Alert'] is True:
            print ("refreshing in " + str(config['Refresh Rate (seconds)']) + " seconds")
            time.sleep(config['Refresh Rate (seconds)'])
            oven_loop()

oven_loop()






