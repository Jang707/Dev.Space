# blink.py
import machine
import utime

led = machine.Pin(25, machine.Pin.OUT)

while True:
    led.toggle()
    utime.sleep(1)