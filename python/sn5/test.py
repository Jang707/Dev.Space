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
        self.stop_event = threading.Event()
        self.monitoring_process = None
        
    def start_server(self):
        """시나리오5 시작"""
        try:
            project_dir = r"D:\Dev.Space\python\sn5"
            server_path = os.path.join(project_dir, "scenario5_normal.py")
            
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
                print("성공적으로 시작되었습니다.")
            else:
                stderr_output = self.server_process.stderr.read().decode('utf-8')
                stdout_output = self.server_process.stdout.read().decode('utf-8')
                error_msg = f"서버 시작 실패\n표준 출력: {stdout_output}\n에러 출력: {stderr_output}"
                raise RuntimeError(error_msg)
                
        except Exception as e:
            print(f"시작 실패: {e}")
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
        print("서버 시작 중...")
        manager.start_server()
        time.sleep(5)
        
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