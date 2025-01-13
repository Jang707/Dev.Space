import subprocess
import os
import time
import threading
import signal
import sys
import requests
import serial.tools.list_ports

class AutomationManager:
    def __init__(self):
        self.flask_port = 5000
        self.server_process = None
        self.stop_event = threading.Event()


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

    def start_server(self):
        """시나리오4 서버 시작"""
        try:
            project_dir = r"D:\Dev.Space\python\sn4"
            server_path = os.path.join(project_dir, "scenario4_pc_server.py")
            
            if os.name == 'nt':
                # Windows에서 새 프로세스 그룹 생성
                self.server_process = subprocess.Popen(
                    ["poetry", "run", "python", server_path],
                    cwd=project_dir,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW,
                    stderr=subprocess.PIPE,
                    stdout=subprocess.PIPE
                )
            else:
                # Unix 계열에서 새 프로세스 그룹 생성
                self.server_process = subprocess.Popen(
                    ["poetry", "run", "python", server_path],
                    cwd=project_dir,
                    preexec_fn=os.setsid,  # 새 프로세스 그룹 생성
                    stderr=subprocess.PIPE,
                    stdout=subprocess.PIPE
                )
            time.sleep(2)
            
            if self.server_process.poll() is None:
                print("서버가 성공적으로 시작되었습니다.")
            else:
                stderr_output = self.server_process.stderr.read().decode('utf-8')
                stdout_output = self.server_process.stdout.read().decode('utf-8')
                error_msg = f"서버 시작 실패\n표준 출력: {stdout_output}\n에러 출력: {stderr_output}"
                raise RuntimeError(error_msg)
                
        except Exception as e:
            print(f"서버 시작 실패: {e}")
            raise

    def check_server(self):
        """서버 상태 확인"""
        max_retries = 5
        retry_delay = 2
    
        for attempt in range(max_retries):
            try:
                response = requests.get(f"http://192.168.0.2:{self.flask_port}/", timeout=5)
                if response.status_code == 200:
                    print("서버가 정상적으로 실행 중입니다.")
                    print(f"웹 인터페이스 접속 주소: http://192.168.0.2:{self.flask_port}")
                    return True
                else:
                    print(f"서버 응답 코드: {response.status_code}")
            except requests.exceptions.RequestException as e:
                print(f"시도 {attempt + 1}/{max_retries}: 서버 연결 대기 중...")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    print(f"서버 연결 실패: {e}")
                    return False

    def setup_pico(self):
        """Raspberry Pi Pico 설정"""
        try:
            pico_main = "D:\Dev.Space\python\sn4\pico\main.py"
            pico_port = None
            ports = serial.tools.list_ports.comports()
            print("Looking for Raspberry pi pico...")
            
            # 1. 포트 상세 정보 출력 추가
            for port in ports:
                print(f"Found port: {port.device} - {port.description} - {port.hwid}")
                if "2E8A:0005" in port.hwid:
                    print(f"Found Pico on port : {port}")
                    pico_port = port.device
                    break

            if not pico_port:
                raise Exception("Pico 장치를 찾을 수 없습니다.")
            
            # 2. 포트 사용 가능 여부 확인
            try:
                with serial.Serial(pico_port, 115200, timeout=1) as ser:
                    print(f"Port {pico_port} is available")
            except serial.SerialException as e:
                print(f"Port {pico_port} is in use or inaccessible: {e}")
                raise

            # 3. 대기 시간 증가
            time.sleep(2)
            
            # 4. ampy 명령 실행 전 상세 로깅 추가
            print(f"Uploading {pico_main} to {pico_port}")
            result = os.system(f"python -m ampy.cli --port {pico_port} put {pico_main}")
            
            if result != 0:
                raise Exception(f"ampy command failed with exit code: {result}")
            
            print("Raspberry pi pico successfully configured and running")
            return True
                
        except Exception as e:
            print(f"Pico 설정 실패: {e}")
            raise

    def cleanup(self):
        """정리 작업 수행"""
        print("정리 작업 시작...")
        # 포트 사용 프로세스 종료
        self.check_and_kill_port(self.flask_port)
        
        if self.server_process:
            if os.name == 'nt':
                # 프로세스 트리 전체를 종료
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(self.server_process.pid)],
                            stderr=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL)
                
                # 추가로 Hypercorn 프로세스들도 명시적으로 종료
                subprocess.run(["taskkill", "/F", "/IM", "hypercorn.exe"],
                            stderr=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL)
            else:
                # Unix 계열에서는 프로세스 그룹 전체에 시그널 전송
                os.killpg(os.getpgid(self.server_process.pid), signal.SIGTERM)
                time.sleep(2)  # 정상 종료 대기
                os.killpg(os.getpgid(self.server_process.pid), signal.SIGKILL)  # 강제 종료
                
        print("정리 작업 완료")

    def check_and_kill_port(self, port):
        """특정 포트를 사용하는 프로세스 종료"""
        if os.name == 'nt':
            try:
                # 포트를 사용하는 프로세스 찾기
                result = subprocess.run(
                    f"netstat -ano | findstr :{port}",
                    shell=True,
                    capture_output=True,
                    text=True
                )
                
                if result.stdout:
                    # PID 추출 및 프로세스 종료
                    for line in result.stdout.split('\n'):
                        if f":{port}" in line:
                            pid = line.strip().split()[-1]
                            subprocess.run(
                                ["taskkill", "/F", "/PID", pid],
                                stderr=subprocess.DEVNULL,
                                stdout=subprocess.DEVNULL
                            )
            except Exception as e:
                print(f"포트 정리 중 오류 발생: {e}")

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
    manager = AutomationManager()
    setup_signal_handlers(manager.cleanup)
    
    try:
        #print("모니터링 서버 시작 중...")
        #manager.start_monitoring_server()
        #time.sleep(5)

        print("WeMos 코드 업로드 중...")
        manager.upload_wemos_code()
        time.sleep(2)

        print("서버 시작 중...")
        manager.start_server()
        time.sleep(5)

        if not manager.check_server():
            raise Exception("서버 시작 확인 실패")
        
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