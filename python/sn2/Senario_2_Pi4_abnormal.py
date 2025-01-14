import smbus
import serial
import threading
from time import sleep
import socketCommunication
import json
import logging
from threading import Lock

logger = logging.getLogger(__name__)

# MPU6050의 datasheet에 나와있는 레지스터 주소 작성. (수정 불필요)
PWR_MGMT_1 = 0x6B
SMPLRT_DIV = 0x19
CONFIG = 0x1A
GYRO_CONFIG = 0x1B
INT_ENABLE = 0x38
ACCEL_XOUT_H = 0x3B
ACCEL_YOUT_H = 0x3D
ACCEL_ZOUT_H = 0x3F
GYRO_XOUT_H = 0x43
GYRO_YOUT_H = 0x45
GYRO_ZOUT_H = 0x47
# MPU6050 활성화 메소드
def MPU_Init(bus, Device_Address):
    # write to sample rate register
    bus.write_byte_data(Device_Address, SMPLRT_DIV, 7)
    # Write to power management register
    bus.write_byte_data(Device_Address, PWR_MGMT_1, 1)
    # Write to Configuration register
    bus.write_byte_data(Device_Address, CONFIG, 0)
    # Write to Gyro configuration register
    bus.write_byte_data(Device_Address, GYRO_CONFIG, 24)
    # Write to interrupt enable register
    bus.write_byte_data(Device_Address, INT_ENABLE, 1)

def read_raw_data(bus, addr, Device_Address):
    # Accelero and Gyro value are 16-bit
    high = bus.read_byte_data(Device_Address, addr)
    low = bus.read_byte_data(Device_Address, addr + 1)
    # concatenate higher and lower value
    value = ((high << 8) | low)
    # to get signed value from mpu6050
    if value > 32768:
        value = value - 65536
    return value

class SensorData:
    def __init__(self):
        self.gyro_x = 0.0
        self.gyro_y = 0.0
        self.gyro_z = 0.0
        self.acc_x = 0.0
        self.acc_y = 0.0
        self.acc_z = 0.0
        self.is_dropped = False
        self.lock = Lock()
        
    def update_data(self, gyro_x, gyro_y, gyro_z, acc_x, acc_y, acc_z, is_dropped):
        with self.lock:
            self.gyro_x = gyro_x / 131.0  # 변환 계수 적용
            self.gyro_y = gyro_y / 31.0
            self.gyro_z = gyro_z / 131.0
            self.acc_x = acc_x / 168.0
            self.acc_y = acc_y / 684.0
            self.acc_z = acc_z / 1684.0
            self.is_dropped = is_dropped
    
    def get_data(self):
        with self.lock:
            return {
                'gyro_x': f"{self.gyro_x:.2f}",
                'gyro_y': f"{self.gyro_y:.2f}",
                'gyro_z': f"{self.gyro_z:.2f}",
                'acc_x': f"{self.acc_x:.2f}",
                'acc_y': f"{self.acc_y:.2f}",
                'acc_z': f"{self.acc_z:.2f}",
                'is_dropped': self.is_dropped
            }

def read_from_pico(ser):
    while True:
        if ser.in_waiting > 0:
            response = ser.readline().decode('utf-8').strip()
            logger.info(f"[Serial] Pico says: {response}")
            print("Pico says:", response)


def main():
    sensor_data = SensorData()
    tcp_client = socketCommunication.TCPClient('192.168.0.2', 12345)
    
    # 시리얼 통신 설정
    ser = serial.Serial('/dev/serial0', 9600, timeout=1)
    ser.flush()
    logger.info("[Serial] Connected to Pico")
    print("Connected to Pico")
    
    # 피코 읽기 스레드 시작 (인자 수정)
    thread = threading.Thread(target=read_from_pico, args=(ser,))
    thread.daemon = True
    thread.start()
    
    bus = smbus.SMBus(1)
    Device_Address = 0x68

    MPU_Init(bus, Device_Address)
    print("Reading Data of Gyroscope and Accelerometer")

    # TCP 연결 시도 - 연결 실패시 프로그램 종료
    if not tcp_client.start():
        logger.error("Failed to establish TCP connection")
        return
        
    def get_sensor_data():
        """TCP 클라이언트가 호출할 콜백 함수"""
        return sensor_data.get_data()
    
    # 주기적 데이터 전송 시작 (2초 간격)
    tcp_client.start_periodic_send(get_sensor_data, 2.0)
    tcp_client.sendmsg("BLE Module MAC Address : C8:FD:19:91:14:F8")

    try:
        # 이전 값 초기화
        previous_acc_z = read_raw_data(bus, ACCEL_ZOUT_H, Device_Address)
        previous_gyro_x = read_raw_data(bus, GYRO_XOUT_H, Device_Address)
        previous_gyro_y = read_raw_data(bus, GYRO_YOUT_H, Device_Address)
        previous_gyro_z = read_raw_data(bus, GYRO_ZOUT_H, Device_Address)

        while True:
            # 센서 데이터 읽기
            acc_x = read_raw_data(bus, ACCEL_XOUT_H, Device_Address)
            acc_y = read_raw_data(bus, ACCEL_YOUT_H, Device_Address)
            acc_z = read_raw_data(bus, ACCEL_ZOUT_H, Device_Address)
            gyro_x = read_raw_data(bus, GYRO_XOUT_H, Device_Address)
            gyro_y = read_raw_data(bus, GYRO_YOUT_H, Device_Address)
            gyro_z = read_raw_data(bus, GYRO_ZOUT_H, Device_Address)

            # 낙하 감지
            acc_z_change = previous_acc_z - acc_z
            
            is_dropped = acc_z_change > 3000

            # SensorData 객체 업데이트
            sensor_data.update_data(
                gyro_x=gyro_x,
                gyro_y=gyro_y,
                gyro_z=gyro_z,
                acc_x=acc_x,
                acc_y=acc_y,
                acc_z=acc_z,
                is_dropped=is_dropped
            )

            # 낙하 감지시 Pico에 알림
            if is_dropped:
                ser.write('alert'.encode('utf-8'))
                print("Alert!! \nsensor is dropped!")
                if ser.in_waiting > 0:
                    line = ser.readline().decode('utf-8').rstrip()
                    print("Pico says:", line)

            # 이전 값 업데이트
            previous_acc_z = acc_z
            previous_gyro_x = gyro_x
            previous_gyro_y = gyro_y
            previous_gyro_z = gyro_z

            # 센서 데이터 출력
            print(f"Gx={gyro_x/131:.2f} °/s\tGy={gyro_y/131:.2f} °/s\tGz={gyro_z/131:.2f} °/s\t"
                  f"Ax={acc_x/16384:.2f} g\tAy={acc_y/16384:.2f} g\tAz={acc_z/16384:.2f} g")

            sleep(0.2)

    except KeyboardInterrupt:
        print("\nClosing connections...")
        tcp_client.close()
        ser.close()
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        tcp_client.close()
        ser.close()

if __name__ == "__main__":
    main()