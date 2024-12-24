## This File isn't used. Just backup.
## Actual code is in ASUS TinkerBoard.
## Bluetooth module which is linked with ASUS TinkerBoard 2 has below serial number
## 6C:EC:EB:23:74:65

import serial
import spidev
import time
import sys
import mcp3208
import ASUS.GPIO as GPIO
import threading
import socketCommunication
from threading import Lock

class SensorData:
    def __init__(self):
        self.light_percentage = 0.0
        self.lock = Lock()
        
    def update_data(self, light_percentage):
        with self.lock:
            self.light_percentage = light_percentage
    
    def get_data(self):
        with self.lock:
            return {
                'light_percentage': f"{self.light_percentage:.2f}",
            }

# GPIO and Serial setup
channel = 0
led_pin = 21
serialB = serial.Serial("/dev/ttyS0", baudrate=9600, timeout=1.0)
bus, device = 5, 0
spi = spidev.SpiDev()
spi.open(bus, device)
spi.max_speed_hz = 1000000
adc = mcp3208.ADC(spi)
GPIO.setmode(GPIO.BOARD)
GPIO.setup(led_pin, GPIO.OUT)
pwm = GPIO.PWM(led_pin, 1000.0)  # 1000.0Hz
pwm.start(0.0)  # 0.0~100.0

def read_bluetooth():
    if serialB.in_waiting:
        return serialB.readline().decode().strip()
    return None

def main():
    # TCP 클라이언트 및 센서 데이터 객체 초기화
    sensor_data = SensorData()
    tcp_client = socketCommunication.TCPClient('192.168.0.2', 12345)
    
    # TCP 연결 시도
    if not tcp_client.start():
        print("Failed to establish TCP connection")
        return
        
    def get_sensor_data():
        """TCP 클라이언트가 호출할 콜백 함수"""
        return sensor_data.get_data()
    
    # 주기적 데이터 전송 시작 (2초 간격)
    tcp_client.start_periodic_send(get_sensor_data, 2.0)

    try:
        while True:
            sensorInput = adc.analogRead(channel)
            lightPercentage = sensorInput / 4095 * 100.0
            pwm.ChangeDutyCycle(lightPercentage)
            
            # 센서 데이터 업데이트
            sensor_data.update_data(lightPercentage)
            
            bluetooth_data = read_bluetooth()
            if bluetooth_data:
                print(f"Received Message From bluetooth: {bluetooth_data}")
                if "light" in bluetooth_data.lower():
                    serialB.write(f"Light percentage: {lightPercentage:.2f}%\n".encode())
            
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("Program terminated by user")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        tcp_client.close()
        spi.close()
        pwm.stop()
        GPIO.cleanup()
        serialB.close()
        print("Cleanup completed")

if __name__ == "__main__":
    main()