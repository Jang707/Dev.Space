import subprocess
import os
import time
import threading
import signal
import sys
import requests
import serial.tools.list_ports
import paramiko
from pathlib import Path
import threading


class AutomationManager:
    def __init__(self, asus_ip, asus_username, asus_password):
        self.asus_ip = asus_ip
        self.asus_username = asus_username
        self.asus_password = asus_password
        self.ssh = None
        self.stop_event = threading.Event()
        self.asus_thread = None

    def connect_ssh(self):
        """SSH 연결 설정"""
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(self.asus_ip, username=self.asus_username, password=self.asus_password)
    
    def setup_asus(self):
        """ASUS TinkerBoard 2 설정"""
        try:
            print("ssh command 실행 시작")
            self.asus_thread = threading.Thread(target=self.run_asus_scenario)
            self.asus_thread.daemon = True
            self.asus_thread.start()

            time.sleep(2)
            print("ASUS TinkerBoard 2 설정이 완료되었습니다.")
        except Exception as e :
            print(f"ASUS TinkerBoard 2 설정 실패: {e}")
            raise
    

    def run_asus_scenario(self):
        """ 별도의 스레드에서 ASUS TinkerBoard 2의 시나리오를 실행합니다."""
        try:
            command = (
                "python3 /home/linaro/senario_7/senario_7_ASUS_abnormal.py"
            )
            transport = self.ssh.get_transport()
            channel = transport.open_session()
            channel.exec_command(command)
            while not self.stop_event.is_set():
                if channel.exit_status_ready():
                    break
                time.sleep(1)

        except Exception as e:
            print(f"ASUS Scenario 실행 중 오류 발생 : {e}")
            self.stop_event.set()

    def kill_existing_process(self):
        """기존 실행중인 프로세스를 종료합니다."""
        try:
            stdin, stdout, stderr = self.ssh.exec_command(
                f"pkill -f 'python.*senario_7_ASUS.py'"
            ) 
        except Exception as e:
            print(f"Error killing existing process: {e}")

    def setup_pico(self):
        """Raspberry Pi Pico 설정"""
        try:
            pico_main = "D:\Dev.Space\python\sn7\pico\main.py"
            pico_port = None
            ports = serial.tools.list_ports.comports()
            print("Looking for Raspberry pi pico...")
            
            for port in ports:
                if "2E8A:0005" in port.hwid:
                    print(f"Found Pico on port : {port}")
                    pico_port = port.device
                    break

            if not pico_port:
                raise Exception("Pico 장치를 찾을 수 없습니다.")
            
            time.sleep(1)
            print(f"ampy put to : {pico_port}")
            os.system(f"python -m ampy.cli --port {pico_port} put {pico_main}")
            
            print("Raspberry pi pico successfully configured and running")
            return True
            
        except Exception as e:
            print(f"Pico 설정 실패: {e}")
            raise

    def cleanup(self):
        """정리 작업 수행"""
        print("정리 작업 시작...")
        self.stop_event.set()
        
        if self.asus_thread and self.asus_thread.is_alive():
            self.kill_existing_process()
            self.asus_thread.join(timeout=5)

        if self.ssh:
            self.ssh.close()
        
        print("정리 작업 완료")

def setup_signal_handlers(cleanup_function):
    def signal_handler(signum, frame):
        print("\n종료신호를 받았습니다. 정리 작업을 시작합니다...")
        if cleanup_function:
            cleanup_function()
        sys.exit(0)
    
    if os.name == 'nt':
        signal.signal(signal.SIGBREAK, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    print(f"PROCESS_ID:{os.getpid()}")
    sys.stdout.flush()

def check_termination():
    if sys.stdin.readable():
        line = sys.stdin.readline().strip()
        if line == "rs202300219928scenarioDONE":
            return True
    return False

def main():
    ASUS_IP = "192.168.0.9"
    ASUS_USERNAME = "linaro"
    ASUS_PASSWORD = "ai@t2023"
    manager = AutomationManager(ASUS_IP, ASUS_USERNAME, ASUS_PASSWORD)
    setup_signal_handlers(manager.cleanup)
    
    try:
        print("ASUS Tinker Board 2에 연결 중...")
        manager.connect_ssh()
        time.sleep(2)

        print("ASUS Tinker Board 2 서비스 시작 중...")
        manager.setup_asus()
        time.sleep(5)
        
        print("Raspberry Pi Pico 설정 중...")
        manager.setup_pico()
        
        print("\n모든 서비스가 시작되었습니다. 종료하려면 Ctrl+C를 누르세요...\n")
        
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