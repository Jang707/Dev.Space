from pymodbus.client import ModbusTcpClient
import time

class PLCCommunication:
    def __init__(self, host='192.168.0.201', port=20010):
        """PLC 통신을 위한 초기화"""
        # 클라이언트 설정을 직접 지정
        self.client = ModbusTcpClient(
            host=host,
            port=port,
            timeout=3,  # 3초 타임아웃
            retries=2,  # 2회 재시도
        )
        
    def connect(self):
        """PLC와 연결"""
        connected = self.client.connect()
        if connected:
            print("PLC 연결 성공")
            time.sleep(0.1)  # 연결 후 잠시 대기
        return connected
        
    def disconnect(self):
        """PLC 연결 해제"""
        self.client.close()
        
    def read_d_register(self, address):
        """D 레지스터 읽기
        address: D 레지스터 주소 (예: D100의 경우 100 입력)
        """
        try:
            result = self.client.read_holding_registers(address, count=1)
            if result is None or (hasattr(result, 'isError') and result.isError()):
                print(f"Error reading D{address}")
                return None
            return result.registers[0]
        except Exception as e:
            print(f"Error reading D register: {e}")
            return None
            
    def control_x_device(self, address, value):
        """X 디바이스 제어
        address: X 디바이스 주소 (예: X00의 경우 0 입력)
        value: True(ON) 또는 False(OFF)
        """
        try:
            result = self.client.write_coil(address, value)
            if result is None or (hasattr(result, 'isError') and result.isError()):
                print(f"Error controlling X{address:02d}")
                return False
            time.sleep(0.1)  # 상태 변경 후 잠시 대기
            return True
        except Exception as e:
            print(f"Error controlling X device: {e}")
            return False

    def control_y_device(self, address, value):
        """Y 디바이스 제어
        address: Y 디바이스 주소 (예: Y00의 경우 0 입력)
        value: True(ON) 또는 False(OFF)
        """
        try:
            result = self.client.write_coil(address + 100, value)
            if result is None or (hasattr(result, 'isError') and result.isError()):
                print(f"Error controlling Y{address:02d}")
                return False
            time.sleep(0.1)  # 상태 변경 후 잠시 대기
            return True
        except Exception as e:
            print(f"Error controlling Y device: {e}")
            return False

def main():
    # PLC 통신 객체 생성
    plc = PLCCommunication()
    
    try:
        # PLC 연결
        if plc.connect():
            # 1. D100 레지스터 값 읽기
            d100_value = plc.read_d_register(100)
            print(f"D100 값: {d100_value}")
            
            # 2. X00 디바이스 제어 (5초간 ON)
            print("X00 ON으로 설정")
            if plc.control_x_device(0, True):
                time.sleep(5)
                print("X00 OFF로 설정")
                plc.control_x_device(0, False)
            
            # 3. Y00 디바이스 제어 예시
            print("Y00 ON으로 설정")
            if plc.control_y_device(0, True):
                time.sleep(2)
                print("Y00 OFF로 설정")
                plc.control_y_device(0, False)
    
    except Exception as e:
        print(f"Error occurred: {e}")
    
    finally:
        # PLC 연결 해제
        plc.disconnect()
        print("PLC 연결 해제")

if __name__ == "__main__":
    main()