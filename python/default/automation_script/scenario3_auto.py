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
    def __init__(self, pi4_ip, pi4_username, pi4_password):
        self.pi4_ip = pi4_ip
        self.pi4_username = pi4_username
        self.pi4_password = pi4_password
        self.ssh = None
        self.flask_port = 10002
        self.monitoring_process = None
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

    def start_monitoring_server(self):
        """PC에서 모니터링 서버 실행"""
        try:
            monitoring_server_path = r"D:\Dev.Space\rust\default\iced_gui"
            
            if not os.path.exists(monitoring_server_path):
                raise FileNotFoundError(f"경로를 찾을 수 없습니다: {monitoring_server_path}")
            
            if not os.path.exists(os.path.join(monitoring_server_path, "Cargo.toml")):
                raise FileNotFoundError(f"Cargo.toml 파일을 찾을 수 없습니다")
            
            print(f"Rust 서버 시작 중...")
            
            # 기존 프로세스 종료
            if os.name == 'nt':
                subprocess.run(["taskkill", "/F", "/IM", "cargo.exe"], 
                             stderr=subprocess.DEVNULL, 
                             stdout=subprocess.DEVNULL)
            
            self.monitoring_process = subprocess.Popen(
                ["cargo", "run"],
                cwd=monitoring_server_path,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            time.sleep(2)
            if self.monitoring_process.poll() is None:
                print("모니터링 서버가 성공적으로 시작되었습니다.")
            else:
                raise RuntimeError("모니터링 서버 시작 실패")
                
        except Exception as e:
            print(f"모니터링 서버 시작 실패: {e}")
            raise

    def run_flask_server(self):
        """Flask 서버를 별도 스레드에서 실행"""
        try:
            command = (
                "source /home/devops_r4/senario_3/senario_3_Pi4_venv/bin/activate && "
                "python /home/devops_r4/Dev.Space/python/sn3/Senario_3_Pi4.py"
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

    def check_flask_server(self):
        """Flask 서버 상태 확인"""
        max_retries = 5
        retry_delay = 2
    
        for attempt in range(max_retries):
            try:
                response = requests.get(
                    f"http://{self.pi4_ip}:{self.flask_port}/monitor",
                    timeout=5
                )
                if response.status_code == 200:
                    print("Flask 서버가 정상적으로 실행 중입니다.")
                    print(f"웹 인터페이스 접속 주소: http://{self.pi4_ip}:{self.flask_port}/monitor")
                    return True
                else:
                    print(f"Flask 서버 응답 코드: {response.status_code}")
            except requests.exceptions.RequestException as e:
                print(f"시도 {attempt + 1}/{max_retries}: 서버 연결 대기 중...")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    print(f"Flask 서버 연결 실패: {e}")
                    return False

    def setup_pico(self):
        """Raspberry Pi Pico 설정"""
        try:
            pico_main = "D:\Dev.Space\python\sn3\pico\main.py"
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

def setup_signal_handlers(cleanup_function):
    """시그널 핸들러 설정"""
    def signal_handler(signum, frame):
        print("\n종료신호를 받았습니다. 정리 작업을 시작합니다...")
        if cleanup_function:
            cleanup_function()
        sys.exit(0)
    # Windows 의 경우 CTRL_BREAK_EVENT 처리
    if os.name == 'nt':
        signal.signal(signal.SIGBREAK, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    # PID 출력 ( Rust 에서 이를 캡쳐함)
    print(f"PROCESS_ID:{os.getpid()}")
    sys.stdout.flush()

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
        
    manager = AutomationManager(PI4_IP, PI4_USERNAME, PI4_PASSWORD)
    # 시그널 핸들러 설정
    setup_signal_handlers(manager.cleanup)
    
    try:
        #print("모니터링 서버 시작 중...")
        # manager.start_monitoring_server()
        #print("서버 초기화 대기 중...")
        #time.sleep(5)

        print("Raspberry Pi 4에 연결 중...")
        manager.connect_ssh()
                
        print("Raspberry Pi 4 서버 시작 중...")
        manager.setup_pi4()
        print("Flask 서버 초기화 대기 중...")
        time.sleep(10)

        if not manager.check_flask_server():
            raise Exception("Flask 서버 시작 확인 실패")
        
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