#  Address of bluetooth module : 78:04:73:05:B8:71
from machine import UART, Pin

# Initialize UART
uart = UART(0, baudrate=9600, tx=Pin(0), rx=Pin(1))

def bluetooth_communication():
    while True:
        if uart.any():
            data_received = uart.read().decode('utf-8')  # decode the received data
            print("Received: ", data_received)
            uart.write("Echo: " + data_received)  # echo the received data back

bluetooth_communication()