import smbus
import serial
import threading
from time import sleep

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

def read_from_pico(ser):
    while True:
        if ser.in_waiting > 0:
            response = ser.readline().decode('utf-8').strip()
            print("Pico says:", response)

def main():
    # 라즈베리파이 피코와의 시리얼 통신 설정
    ser = serial.Serial('/dev/serial0',9600,timeout=1)
    ser.flush()
    print("Connected to Pico")
    # 피코로부터 데이터를 읽는 스레드 시작
    thread = threading.Thread(target=read_from_pico, args=(ser,))
    thread.daemon = True
    thread.start()
    bus = smbus.SMBus(1)  # or bus = smbus.SMBus(0) for older version boards
    Device_Address = 0x68  # MPU6050 device address

    MPU_Init(bus, Device_Address)

    print("Reading Data of Gyroscope and Accelerometer")

    # 초기 가속도계 및 자이로스코프 값 저장
    previous_acc_z = read_raw_data(bus, ACCEL_ZOUT_H, Device_Address)
    previous_gyro_x = read_raw_data(bus, GYRO_XOUT_H, Device_Address)
    previous_gyro_y = read_raw_data(bus, GYRO_YOUT_H, Device_Address)
    previous_gyro_z = read_raw_data(bus, GYRO_ZOUT_H, Device_Address)

    while True:
        # Read Accelerometer raw value
        acc_x = read_raw_data(bus, ACCEL_XOUT_H, Device_Address)
        acc_y = read_raw_data(bus, ACCEL_YOUT_H, Device_Address)
        acc_z = read_raw_data(bus, ACCEL_ZOUT_H, Device_Address)

        # Read Gyroscope raw value
        gyro_x = read_raw_data(bus, GYRO_XOUT_H, Device_Address)
        gyro_y = read_raw_data(bus, GYRO_YOUT_H, Device_Address)
        gyro_z = read_raw_data(bus, GYRO_ZOUT_H, Device_Address)

        # 가속도와 자이로스코프 데이터의 변화를 확인하여 센서가 빠르게 떨어지는지 감지
        acc_z_change = previous_acc_z - acc_z
        gyro_change = (abs(previous_gyro_x - gyro_x) + abs(previous_gyro_y - gyro_y) + abs(previous_gyro_z - gyro_z))

        # 가속도 Z축 값이 급격히 감소하고 자이로스코프 데이터도 변동이 있으면 피코에 경고 메시지 전송
        if acc_z_change > 3000 and gyro_change > 500:
            alert_message = "Alert!! \nsensor is dropped!"
            ser.write(('alert').encode('utf-8'))
            print(alert_message)
            if ser.in_waiting>0:
                line = ser.readline().decode('utf-8').rstrip()
                print("Pico says:",line)

        # 이전 값을 현재 값으로 업데이트
        previous_acc_z = acc_z
        previous_gyro_x = gyro_x
        previous_gyro_y = gyro_y
        previous_gyro_z = gyro_z

        # 센서 데이터 출력
        print(f"Gx={gyro_x / 131:.2f} °/s\tGy={gyro_y / 131:.2f} °/s\tGz={gyro_z / 131:.2f} °/s\tAx={acc_x / 16384:.2f} g\tAy={acc_y / 16384:.2f} g\tAz={acc_z / 16384:.2f} g")

        sleep(0.1)

if __name__ == "__main__":
    main()
