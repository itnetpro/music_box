# -*- encoding: utf-8 -*-
import RPi.GPIO as GPIO
from time import sleep
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(16, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)


while True:
    print GPIO.input(16)
    sleep(0.01)


"""
sudo apt-get update
sudo apt-get upgrade

sudo apt-get install build-essential git cmake libqt4-dev libphonon-dev python2.7-dev libxml2-dev libxslt1-dev qtmobility-dev python-pip moc libjpeg-dev vlc python-pyside










"""
