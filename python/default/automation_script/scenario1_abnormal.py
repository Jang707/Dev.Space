import paramiko
import time
import subprocess
import os
from pathlib import Path
import serial.tools.list_ports
import requests
import threading
import signal
import sys

class AutomationManager:
    def __init__(self):
        self.monitoring_process = None
        self.stop_event = threading.Event()

    def setup_pico(self):
        """Raspberry Pi Pico 설정"""
        try:
            pico_main = "D:\Dev.Space\python\sn1\\abnormal\main.py"
            pico_port = None
            ports = serial.tools.list_ports.comports()
            print("Looking for Raspberry pi pico...")
            # Finding Pico device
            for port in ports:
                if "2E8A:0005" in port.hwid:
                    print(f"Found Pico on port : {port}")
                    pico_port = port.device
                    break

            if not pico_port:
                raise Exception("Pico 장치를 찾을 수 없습니다.")
            
            #Execute ampy commands
            try:
                # Add small delay to ensure port is ready
                time.sleep(1)
                # put & run "main.py" to pico
                print(f"ampy put to : {pico_port}")
                os.system(f"python -m ampy.cli --port {pico_port} put {pico_main}")
                #print(f"now run : {pico_main}")
                #os.system(f"python -m ampy.cli --port {pico_port} run {pico_main}")
                
                print("Raspberry pi pico successfully configured and running")
                return True
            
            except Exception as e:
                print(f"Failed to execute ampy commands : {e}")
                return False
            
        except Exception as e:
            print(f"Pico 설정 실패: {e}")
            raise

    def cleanup(self):
        """연결 종료 및 정리"""
        print("정리 작업 시작...")
        self.stop_event.set()
            
        if self.monitoring_process:
            if os.name == 'nt':
                subprocess.run(["taskkill", "/F", "/PID", str(self.monitoring_process.pid)],
                             stderr=subprocess.DEVNULL,
                             stdout=subprocess.DEVNULL)
            else:
                self.monitoring_process.terminate()
        
        print("정리 작업 완료")

def signal_handler(signum, frame):
    print("\n종료 신호를 받았습니다. 프로그램을 종료합니다...")
    sys.exit(0)

def check_termination():
    """Termintaion Signal 체크"""
    if sys.stdin.readable():
        line = sys.stdin.readline().strip()
        if line == "rs202300219928scenarioDONE":
            return True
    return False

def main():
    
    # 시그널 핸들러 설정
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    manager = AutomationManager()

    try:
        # 포트 선점 문제로인해 Pico 설정을 먼저 진행합니다.
        print("Raspberry Pi Pico 설정 중...")
        manager.setup_pico()
        print("Raspberry Pi Pico 연결 해제 후 다시 연결해주세요.")
        time.sleep(10)
        
        print("\n모든 서비스가 시작되었습니다. 종료하려면 Ctrl+C를 누르세요...\n")
        print("Bluetooth 연결은 MAC Address: C8:FD:19:91:14:F8 과 연결하세요.")
        # 메인 루프
        while True:
            time.sleep(1)
            if check_termination():
                print("종료 신호를 받았습니다.")
                break
            
    except KeyboardInterrupt:
        print("\n사용자에 의해 프로그램이 종료됩니다...")
    except Exception as e:
        print(f"자동화 실행 중 오류 발생: {e}")
    finally:
        manager.cleanup()
        print("프로그램이 종료되었습니다.")

if __name__ == "__main__":
    main()