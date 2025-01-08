from pymodbus.client import ModbusTcpClient
import time
import signal
import sys
import threading

class PLCCommunication:
    def __init__(self, host='192.168.0.201', port=20010):
        """PLC 통신을 위한 초기화"""
        self.client = ModbusTcpClient(
            host=host,
            port=port,
            timeout=3,
            retries=2,
        )
        self.running = True
        self.stop_event = threading.Event()
        
    def connect(self):
        """PLC와 연결"""
        connected = self.client.connect()
        if connected:
            print("PLC 연결 성공")
            time.sleep(1)
        return connected
        
    def disconnect(self):
        """PLC 연결 해제"""
        if self.client:
            try:
                # M300 ON으로 설정 후 연결 해제
                self.control_m_device(300, True)
                self.client.close()
                print("PLC 연결 해제 완료")
            except Exception as e:
                print(f"연결 해제 중 오류 발생: {e}")
        
    def read_d_register(self, address):
        """D 레지스터 읽기"""
        try:
            result = self.client.read_holding_registers(address, count=1)
            if result is None or (hasattr(result, 'isError') and result.isError()):
                print(f"Error reading D{address}")
                return None
            return result.registers[0]
        except Exception as e:
            print(f"Error reading D register: {e}")
            return None

    def control_m_device(self, address, value):
        """M 디바이스 제어"""
        try:
            result = self.client.write_coil(address+8192, value)
            if result is None or (hasattr(result, 'isError') and result.isError()):
                print(f"Error controlling M{address:02d}")
                return False
            time.sleep(0.1)
            return True
        except Exception as e:
            print(f"Error controlling M device: {e}")
            return False

    def stop(self):
        """PLC 통신 중지"""
        self.running = False
        self.stop_event.set()

def signal_handler(signum, frame):
    """시그널 핸들러"""
    print("\n종료 신호를 받았습니다. 프로그램을 종료합니다...")
    if 'plc' in globals():
        plc.stop()

def check_termination():
    """종료 신호 확인"""
    if sys.stdin.readable():
        line = sys.stdin.readline().strip()
        if line == "rs202300219928scenarioDONE":
            return True
    return False

def main():
    global plc
    plc = PLCCommunication()
    
    # 시그널 핸들러 설정
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    if sys.platform == 'win32':
        signal.signal(signal.SIGBREAK, signal_handler)

    try:
        # PLC 연결
        if plc.connect():
            print("M300 ON으로 설정")
            plc.control_m_device(300, True)
            
            # 프로그램 실행 유지
            while plc.running:
                if check_termination():
                    print("종료 신호를 받았습니다.")
                    break
                time.sleep(1)
    
    except Exception as e:
        print(f"오류 발생: {e}")
    
    finally:
        # 안전한 종료 수행
        plc.disconnect()
        print("프로그램이 안전하게 종료되었습니다.")

if __name__ == "__main__":
    main()