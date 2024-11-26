### Version 0.1 ###

import paramiko
import time
import subprocess
import os
from pathlib import Path
import serial.tools.list_ports

class AutomationManager:
    def __init__(self, pi4_ip, pi4_username, pi4_password):
        self.pi4_ip = pi4_ip
        self.pi4_username = pi4_username
        self.pi4_password = pi4_password
        self.ssh = None
        
    def connect_ssh(self):
        """SSH 연결 설정"""
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(self.pi4_ip, username=self.pi4_username, password=self.pi4_password)
        
    def start_monitoring_server(self):
        """PC에서 모니터링 서버 실행"""
        try:
            # Rust 프로젝트 경로 설정
            monitoring_server_path = r"D:\jang_git_space\Dev.Space\rust\default\iced_gui"

            # 경로가 존재하는지 확인
            if not os.path.exists(monitoring_server_path):
                raise FileNotFoundError(f"경로를 찾을 수 없습니다: {monitoring_server_path}")
        
            # Cargo.toml 파일 존재 확인
            if not os.path.exists(os.path.join(monitoring_server_path, "Cargo.toml")):
                raise FileNotFoundError(f"Cargo.toml 파일을 찾을 수 없습니다: {monitoring_server_path}")
            
            print(f"Rust 서버 시작 중... (경로: {monitoring_server_path})")
        
            # GUI 프로세스 시작 (표준 출력 리디렉션 없이)
            process = subprocess.Popen(
                ["cargo", "run"],
                cwd=monitoring_server_path,
                # GUI 프로그램을 위한 Windows 특정 설정
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                # 표준 출력을 리디렉션하지 않음
                close_fds=False
            )
        
            # 프로세스 시작 대기
            time.sleep(2)
        
            # 프로세스 상태 확인
            if process.poll() is None:
                print("모니터링 서버가 성공적으로 시작되었습니다.")
            else:
                # 프로세스가 즉시 종료된 경우
                returncode = process.poll()
                raise RuntimeError(f"서버 시작 실패 (종료 코드: {returncode})")

        except Exception as e:
            print(f"모니터링 서버 시작 실패: {e}")
            raise
            
    def setup_pi4(self):
        """Raspberry Pi 4 설정 및 서버 실행"""
        try:
            stdin, stdout, stderr = self.ssh.exec_command(
                f"cd /home/devops_r4 && "
                f"source senario_3/senario_3_Pi4_venv/bin/activate && "
                f"python /Dev.Space/python/sn3/Senario_3_Pi4.py"
            )
            print("Raspberry Pi 4 서버가 시작되었습니다.")
        except Exception as e:
            print(f"Raspberry Pi 4 설정 실패: {e}")
            
    def setup_pico(self):
        """Raspberry Pi Pico 설정"""
        try:
            # Pico 디바이스 찾기
            pico_port = None
            ports = serial.tools.list_ports.comports()
            for port in ports:
                if "2E8A:0005" in port.hwid:  # Pico의 vendor:product ID
                    pico_port = port.device
                    break
        
            if pico_port:
                # 운영체제에 따른 마운트 경로 설정
                if os.name == 'posix':  # Linux/macOS
                    pico_path = Path("/media/username/RPI-RP2")  # 실제 마운트 경로로 수정
                elif os.name == 'nt':  # Windows
                    # Windows의 경우 사용 가능한 드라이브 중 RPI-RP2 레이블을 찾음
                    from win32api import GetLogicalDriveStrings
                    drives = GetLogicalDriveStrings().split('\000')[:-1]
                    for drive in drives:
                        if os.path.exists(os.path.join(drive, 'INFO_UF2.TXT')):
                            pico_path = Path(drive)
                            break
            
                if pico_path.exists():
                    # main.py 파일의 원본 경로 (프로젝트 내 실제 파일 위치로 수정)
                    source_path = Path("../../sn3/pico/main.py")
                    dest_path = pico_path / "main.py"

                    print(f"Copying {source_path} to {dest_path}")
                    subprocess.run(["cp" if os.name == 'posix' else "copy", 
                                str(source_path), str(dest_path)], 
                                check=True)
                
                    # Pico 리셋
                    with serial.Serial(pico_port, 1200) as ser:
                        ser.setDTR(False)
                        time.sleep(0.1)
                        ser.setDTR(True)
                
                    print("Raspberry Pi Pico 설정이 완료되었습니다.")
                else:
                    print(f"Pico 마운트 경로를 찾을 수 없습니다: {pico_path}")
            else:
                print("Raspberry Pi Pico를 찾을 수 없습니다.")
        except Exception as e:
            print(f"Pico 설정 실패: {e}")
            
    def check_flask_server(self):
        """Flask 서버 상태 확인"""
        try:
            import requests
            response = requests.get(f"http://{self.pi4_ip}:10002/monitor")
            if response.status_code == 200:
                print("Flask 서버가 정상적으로 실행 중입니다.")
                print(f"웹 인터페이스 접속 주소: http://{self.pi4_ip}:10002")
            else:
                print("Flask 서버 응답이 비정상적입니다.")
        except Exception as e:
            print(f"Flask 서버 연결 실패: {e}")
            
    def cleanup(self):
        """연결 종료 및 정리"""
        if self.ssh:
            self.ssh.close()

def main():
    # 설정값
    PI4_IP = "192.168.0.4"
    PI4_USERNAME = "devops_r4"
    PI4_PASSWORD = "dbspt!23"
    
    # 자동화 매니저 생성
    manager = AutomationManager(PI4_IP, PI4_USERNAME, PI4_PASSWORD)
    
    try:
        # 모니터링 서버 시작
        print("모니터링 서버 시작 중...")
        manager.start_monitoring_server()
        time.sleep(5)  # 서버 시작 대기

        # SSH 연결
        print("Raspberry Pi 4에 연결 중...")
        manager.connect_ssh()
                
        # Pi 4 설정 및 서버 시작
        print("Raspberry Pi 4 서버 시작 중...")
        manager.setup_pi4()
        time.sleep(5)  # 서버 시작 대기
        
        # Pico 설정
        print("Raspberry Pi Pico 설정 중...")
        manager.setup_pico()
        time.sleep(5)  # 설정 완료 대기       
        
    except Exception as e:
        print(f"자동화 실행 중 오류 발생: {e}")
    finally:
        manager.cleanup()

if __name__ == "__main__":
    main()