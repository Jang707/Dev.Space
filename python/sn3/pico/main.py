from machine import Pin, UART
from PicoDHT22 import PicoDHT22 
# you must have PicoDHT22 library file. This is not pre-installed library.
from utime import sleep

dht11=PicoDHT22(Pin(6), dht11=True)
uart = UART(0, baudrate=9600, tx=Pin(0), rx=Pin(1))

while True:
    T,H = dht11.read()
    if T is None:
        print("Sensor Error")
    else:
        print("{} C, Humidity {} %".format(T,H))
        uart.write(f"{T},{H}")
    sleep(2)