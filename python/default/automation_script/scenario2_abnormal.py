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
import socketCommunication

class AutomationManager:
    def __init__(self, pi4_ip, pi4_username, pi4_password):
        self.pi4_ip = pi4_ip
        self.pi4_username = pi4_username
        self.pi4_password = pi4_password
        self.ssh = None
        self.monitoring_process = None
        self.stop_event = threading.Event()

        
    def connect_ssh(self):
        """SSH 연결 설정"""
        try:
            print("SSH 연결을 시도합니다.")
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh.connect(self.pi4_ip, username=self.pi4_username, password=self.pi4_password)
        except Exception as e:
            print(f"ssh 연결 실패 : {e}")

    def kill_existing_process(self):
        """ 기존에 실행중인 Python 프로세스 종료"""
        try:
            stdin, stdout, stderr = self.ssh.exec_command(
                f"pkill python"
            )
            time.sleep(2)
        except Exception as e:
            print(f"Error killing existing process : {e}")

    def run_pi4(self):
        """Raspberry Pi 4 실행"""
        try:
            print("Pi4에 command 입력을 시작합니다.")
            command = (
                "source /home/devops_r4/senario_2/senario_2_Pi4_venv/bin/activate &&"
                "python /home/devops_r4/Dev.Space/python/sn2/Senario_2_Pi4_abnormal.py"
            )
            print("Command 입력 완료.")

            transport = self.ssh.get_transport()
            channel = transport.open_session()
            channel.exec_command(command)

            while not self.stop_event.is_set():
                if channel.exit_status_ready():
                    break
                time.sleep(1)

        except Exception as e:
            print(f"Pi 4 실행 중 오류 발생: {e}")
            self.stop_event.set()

    def setup_pi4(self):
        """Raspberry Pi 4 설정 및 실행"""
        try:
            print("ssh command 실행 시작")
            self.pi4_thread = threading.Thread(target=self.run_pi4)
            self.pi4_thread.daemon = True   #메인 스레드 종료시 같이 종료되도록 설정
            self.pi4_thread.start()
            # 시작 대기
            time.sleep(3)
            print("Pi4 스레드가 시작되었습니다.")

        except Exception as e:
            print(f"Raspberry Pi 4 설정 실패 : {e}")
            raise

    def setup_pico(self):
        """Raspberry Pi Pico 설정"""
        try:
            pico_main = "D:\Dev.Space\python\sn2\pico\\abnormal\main.py"
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
        # 기존 프로세스 종료
        self.kill_existing_process()
        self.stop_event.set()
            
        if self.monitoring_process:
            if os.name == 'nt':
                subprocess.run(["taskkill", "/F", "/PID", str(self.monitoring_process.pid)],
                             stderr=subprocess.DEVNULL,
                             stdout=subprocess.DEVNULL)
            else:
                self.monitoring_process.terminate()
            
        if self.ssh:
            self.ssh.close()
        
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
    PI4_IP = "192.168.0.4"
    PI4_USERNAME = "devops_r4"
    PI4_PASSWORD = "dbspt!23"
    
    # 시그널 핸들러 설정
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    manager = AutomationManager(PI4_IP, PI4_USERNAME, PI4_PASSWORD)
    tcp_client = socketCommunication.TCPClient('192.168.0.2', 12345)
    
    try:

        print("Raspberry Pi 4에 연결 중...")
        manager.connect_ssh()
        time.sleep(2)
        print("Raspberry Pi 4 설정 시작 중...")
        manager.setup_pi4()
        time.sleep(5)
        print("Raspberry Pi Pico 설정 중...")
        manager.setup_pico()
        
        print("\n모든 서비스가 시작되었습니다. 종료하려면 Ctrl+C를 누르세요...\n")
        
        
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