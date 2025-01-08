# 라즈베리파이와 연결된 블루투스 MAC 주소-> C8:FD:19:91:14:F8
import uasyncio as asyncio
from machine import UART, Pin, Timer, SPI, PWM
from ssd1306 import SSD1306_SPI
import json
import sys
import time

# Hardware Setup
pwm = PWM(Pin(15)) # LED = 15번
pwm.freq(1000) # PWM 주파수 설정.
duty = 0 # LED 밝기.
button_duty_up = Pin(14, Pin.IN, Pin.PULL_UP)
button_duty_down = Pin(13, Pin.IN, Pin.PULL_UP)
btn_stat = "None"

# Communication setup
uart_bluetooth = UART(1, baudrate=9600, tx=Pin(4), rx=Pin(5))   #Bluetooth UART
uart_usb = UART(0,baudrate=9600) # PC Connected UART

# Display Setup
spi = SPI(0, 100000, mosi=Pin(19), sck=Pin(18))
oled = SSD1306_SPI(128, 32, spi, Pin(17), Pin(20), Pin(16))
oled_text = 'None'
oled_bluetooth = False 

async def send_status_to_pc():
    """Send status updates to PC via USB"""
    global duty, btn_stat, oled_text
    while True:
        try:
        #Create status message
            status = {
                "pwm_duty": duty,
                "pwm_percent" : round(duty/255*100, 2),
                "button_status": btn_stat,
                "bluetooth_data": oled_text
            }
            uart_usb.write(b"TEST MESSAGE\r\n")

            # JSON 문자열로 변환한 후 CRLF 추가
            message = json.dumps(status) + "\r\n"
            uart_usb.write(message)
            print(f"{message.strip()}")
            time.sleep(1)
        except Exception as e:
            print("Error sending to PC: ", e)
        
        await asyncio.sleep(0.5)

async def bluetooth_communication():
    global oled_text, oled_bluetooth, duty
    while True:
        if uart_bluetooth.any():
            try:
                data_received = uart_bluetooth.read()
                if data_received is not None:
                    data_received = data_received.decode('utf-8').strip()  # decode the received data
                    uart_bluetooth.write(("Echo: " + data_received + "\n").encode())  # echo the received data back
                    oled_text=data_received
                    if oled_text == "up":
                        duty += 50
                    elif oled_text == "down":
                        duty -= 50
                    elif oled_text == "shut down":
                        duty = 0

                    oled_bluetooth = True # OLED 에 블루투스로 송신받는 데이터를 보이게 함.
            except UnicodeError:
                print("Received non-UTF-8 data")
        await asyncio.sleep(0.1)

#pwm 범위를 제한하기 위한 기능을 추가함.
async def pwm_led():
    global duty, pwm
    while True:
        duty=max(0,min(255,duty)) # 0~255 사이로 조정
        # 제곱을 하는 이유는 변화를 인식할 수 있게 하기 위함. 제곱을 안해버리면 너무 차이가 안난다.
        pwm.duty_u16(duty * duty)
        await asyncio.sleep(0.1)

async def button_monitor():
    global duty, oled_bluetooth, btn_stat
    while True:
        old_btn_stat = btn_stat
        if button_duty_up.value() == 0:
            btn_stat = "UP"
            duty = duty+10
            oled_bluetooth = False # OLED에 Button status 를 출력.
        elif button_duty_down.value() == 0:
            btn_stat = "DOWN"
            duty = duty-10
            oled_bluetooth = False # OLED에 Button status 를 출력.
        else:
            btn_stat = "None"
        await asyncio.sleep(0.1)
    
async def oled_display():
    global duty, oled_text, oled_bluetooth, btn_stat
    while True:
        duty_str = str(round(duty/255*100, 1))
        oled.fill(0)
        # oled (텍스트,수평,수직)
        oled.text("Duty:",40,10)
        oled.text(duty_str, 80, 10)
        # oled text 공간이 모자라서 2가지를 경우에 따라 나눠 써야한다.
        if oled_bluetooth:
            oled.text(oled_text,40,20)
        else :
            oled.text(btn_stat,40,20)
        oled.show()
        await asyncio.sleep_ms(10)
    
async def main():
    print("Starting main program")
    await asyncio.gather(
        bluetooth_communication(),
        pwm_led(),
        button_monitor(),
        oled_display(),
        send_status_to_pc()
    )

uart_usb.write(b"PICO INITIALIZED\r\n")
asyncio.run(main())