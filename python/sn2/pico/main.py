# 라즈베리파이와 연결된 블루투스 MAC 주소-> C8:FD:19:91:14:F8import machine
import machine
import uasyncio as asyncio
from machine import Pin, UART, ADC, SPI
from ssd1306 import SSD1306_SPI

# OLED 설정
spi = SPI(0, baudrate=100000, mosi=Pin(19), sck=Pin(18))
oled = SSD1306_SPI(128, 32, spi, Pin(17), Pin(20), Pin(16))

# ADC 설정 (가변저항기)
pot = ADC(28)

# UART 설정
bt_uart = UART(1, baudrate=9600, tx=Pin(4), rx=Pin(5))

# Bluetooth UART 설정
uart = UART(0, baudrate=9600, tx=Pin(0), rx=Pin(1))

alert_flag = False

# OLED 출력 함수
def display_oled(line1, line2):
    oled.fill(0)
    oled.text(line1, 40, 10)
    oled.text(line2, 40, 20)
    oled.show()

def format_sensor_data(adc_value):
    """ 센서 데이터를 포맷팅하고 인코딩"""
    if adc_value is None :
        return None
    data = f"{adc_value}\n"
    return data.encode('utf-8')

# ADC 읽기 및 OLED 출력
async def read_adc():
    global alert_flag
    while True:
        adc_value = pot.read_u16()
        data = format_sensor_data(adc_value)
        if alert_flag:
            display_oled("Alert!!","Alert!!")
        else:
            display_oled("Poten:", str(adc_value))
            uart.write(data)
        await asyncio.sleep(0.1)

# Bluetooth 통신 처리
async def bluetooth_communication():
    global alert_flag
    while True:
        if bt_uart.any():
            data_received = bt_uart.read().decode('utf-8').strip()
            if data_received == "alert":
                alert_flag = True
                display_oled("Alert!!","Alert!!")
                bt_uart.write("Alert mode activated\n")
            elif data_received == "monitor":
                alert_flag = False
                bt_uart.write("Monitor mode activated\n")
        await asyncio.sleep(0.1)

# UART 통신 처리
async def uart_communication():
    global alert_flag
    while True:
        if uart.any():
            data_received = uart.read().decode('utf-8').strip()
            if data_received == "alert":
                alert_flag = True
                display_oled("Alert!!","Alert!!")
                uart.write("Alert mode activated\n")
        await asyncio.sleep(0.1)

# 메인 함수
async def main():
    await asyncio.gather(
        read_adc(),
        bluetooth_communication(),
        uart_communication()
    )

# 비동기 실행
asyncio.run(main())