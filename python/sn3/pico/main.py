from machine import Pin, UART
from PicoDHT22 import PicoDHT22
from utime import sleep

# DHT11 센서 초기화 (GPIO 6)
dht11 = PicoDHT22(Pin(6), dht11=True)

# UART 초기화 (GPIO 0: TX, GPIO 1: RX)
uart = UART(0, 
           baudrate=9600,
           tx=Pin(0),
           rx=Pin(1),
           bits=8,
           parity=None,
           stop=1)

def format_sensor_data(temp, humid):
    """센서 데이터를 포맷팅하고 인코딩"""
    if temp is None or humid is None:
        return None
    # 명확한 구분자와 줄바꿈으로 데이터 포맷
    data = f"{temp:.1f},{humid:.1f}\n"
    return data.encode('utf-8')

def main():
    while True:
        try:
            # 센서 읽기
            temp, humid = dht11.read()
            
            # 데이터 포맷팅 및 전송
            data = format_sensor_data(temp, humid)
            if data:
                uart.write(data)
                print(f"Sent: {temp:.1f}°C, {humid:.1f}%")
            else:
                # 센서 에러 시 특수 메시지 전송
                error_msg = "ERROR,ERROR\n".encode('utf-8')
                uart.write(error_msg)
                print("Sensor Error")
            
            # 다음 읽기 전 대기
            sleep(2)
            
        except Exception as e:
            print(f"Error: {e}")
            sleep(2)

if __name__ == "__main__":
    main()