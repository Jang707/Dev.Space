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


class ASUS_AutomationManager:
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
                "python3 /home/linaro/senario_7/senario_7_ASUS.py"
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

class RASPBERRY_AutomationManager:
    def __init__(self, pi4_ip, pi4_username, pi4_password):
        self.pi4_ip = pi4_ip
        self.pi4_username = pi4_username
        self.pi4_password = pi4_password
        self.ssh = None
        self.flask_port = 8000
        self.stop_event = threading.Event()
        self.flask_thread = None
        
    def connect_ssh(self):
        """SSH 연결 설정"""
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(self.pi4_ip, username=self.pi4_username, password=self.pi4_password)

    def kill_existing_flask(self):
        """기존 실행 중인 Flask 서버 프로세스 종료"""
        try:
            stdin, stdout, stderr = self.ssh.exec_command(
                f"pkill python"
            )
            time.sleep(2)
        except Exception as e:
            print(f"Error killing existing Flask process: {e}")

    def run_flask_server(self):
        """Flask 서버를 별도 스레드에서 실행"""
        try:
            command = (
                "source /home/devops_r4/senario_6/venv_senario_6_Pi4/bin/activate && "
                "python /home/devops_r4/senario_6/Senario_6_Pi4.py"
            )
            
            transport = self.ssh.get_transport()
            channel = transport.open_session()
            channel.exec_command(command)
            
            while not self.stop_event.is_set():
                if channel.exit_status_ready():
                    break
                time.sleep(1)
                
        except Exception as e:
            print(f"Flask 서버 실행 중 오류 발생: {e}")
            self.stop_event.set()

    def setup_pi4(self):
        """Raspberry Pi 4 설정 및 서버 실행"""
        try:
            self.kill_existing_flask()
            print("ssh command 실행 시작")
            
            # Flask 서버를 별도 스레드에서 실행
            self.flask_thread = threading.Thread(target=self.run_flask_server)
            self.flask_thread.daemon = True  # 메인 스레드 종료시 같이 종료되도록 설정
            self.flask_thread.start()
            
            # 서버 시작 대기
            time.sleep(5)
            print("Flask 서버 스레드가 시작되었습니다.")
            
        except Exception as e:
            print(f"Raspberry Pi 4 설정 실패: {e}")
            raise

    def cleanup(self):
        """연결 종료 및 정리"""
        print("정리 작업 시작...")
        self.stop_event.set()
        
        if self.flask_thread and self.flask_thread.is_alive():
            self.kill_existing_flask()
            self.flask_thread.join(timeout=5)
            
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

class WEMOS_AutomationManager :
    def upload_wemos_code(self):
        """WeMos 코드 업로드"""
        try:
            #upload_script_path = os.path.join("..", "wemos_scenario4_upload.py")
            upload_script_path = "D:\Dev.Space\python\default\wemos_scenario4_upload.py"
            result = subprocess.run(["python", upload_script_path], 
                                 capture_output=True, 
                                 text=True)
            if result.returncode != 0:
                raise Exception(f"WeMos 업로드 실패: {result.stderr}")
            print("WeMos 코드가 성공적으로 업로드되었습니다.")
        except Exception as e:
            print(f"WeMos 코드 업로드 실패: {e}")
            raise

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
    asus_manager = ASUS_AutomationManager(ASUS_IP, ASUS_USERNAME, ASUS_PASSWORD)
    setup_signal_handlers(asus_manager.cleanup)

    PI4_IP = "192.168.0.4"
    PI4_USERNAME = "devops_r4"
    PI4_PASSWORD = "dbspt!23"
    rasp_manager = RASPBERRY_AutomationManager(PI4_IP, PI4_USERNAME, PI4_PASSWORD)
    setup_signal_handlers(rasp_manager.cleanup)

    wemos_manager = WEMOS_AutomationManager()
    
    try:
        print("ASUS Tinker Board 2에 연결 중...")
        asus_manager.connect_ssh()
        time.sleep(2)

        print("ASUS Tinker Board 2 서비스 시작 중...")
        asus_manager.setup_asus()
        time.sleep(2)

        print("Raspberry Pi 4 에 연결 중...")
        rasp_manager.connect_ssh()
        time.sleep(2)

        print("Raspberry Pi 4 서버 시작 중...")
        rasp_manager.setup_pi4
        time.sleep(2)

        print("WeMos 코드 업로드 중...")
        wemos_manager.upload_wemos_code()
        time.sleep(2)
        
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
        asus_manager.cleanup()
        print("프로그램이 종료되었습니다.")

if __name__ == "__main__":
    main()