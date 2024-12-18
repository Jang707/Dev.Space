import sys
import subprocess
import signal
import os

def main():
    # 실행할 스크립트의 경로를 커맨드 라인 인자로 받음
    if len(sys.argv) < 2:
        print("Usage: python run_scenario.py <script_path>")
        sys.exit(1)
        
    script_path = sys.argv[1]
    
    # 스크립트 실행
    process = subprocess.Popen([sys.executable, script_path],
                             creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0)
    
    # 프로세스 ID를 파일에 저장
    with open("scenario_pid.txt", "w") as f:
        f.write(str(process.pid))
        
    # 프로세스가 종료될 때까지 대기
    process.wait()

if __name__ == "__main__":
    main()