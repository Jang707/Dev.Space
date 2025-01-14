import sys
import platform
import psutil
import datetime
import subprocess
import os

def collect_info():
    """시스템 정보를 수집하는 함수"""
    info = []
    
    # OS 정보 수집
    info.append("=== OS 정보 ===")
    os_info = platform.uname()
    info.append(f"시스템: {os_info.system}")
    info.append(f"노드 이름: {os_info.node}")
    info.append(f"릴리스: {os_info.release}")
    info.append(f"버전: {os_info.version}")
    info.append(f"머신: {os_info.machine}")
    info.append(f"프로세서: {os_info.processor}")
    
    # 실행 중인 프로세스 정보 수집
    info.append("\n=== 실행 중인 프로세스 목록 ===")
    for proc in psutil.process_iter(['pid', 'name', 'status']):
        try:
            info.append(f"PID: {proc.info['pid']:<6} | 이름: {proc.info['name']:<30} | 상태: {proc.info['status']}")
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    
    # Windows 서비스 정보 수집
    if platform.system() == 'Windows':
        info.append("\n=== 실행 중인 서비스 목록 ===")
        for service in psutil.win_service_iter():
            try:
                name = service.name()
                display_name = service.display_name() if service.display_name() else "알 수 없음"
                status = service.status() if service.status() else "알 수 없음"
                if status == "running":
                    info.append(f"이름: {name:<30} | 표시명: {display_name}")
            except Exception:
                continue
    
    return info

def save_info(info_list):
    """수집된 정보를 파일로 저장하는 함수"""
    today = datetime.datetime.now().strftime("%Y%m%d")
    filename = f"trust_collect_{today}.txt"
    
    with open(filename, 'w', encoding='utf-8') as f:
        for line in info_list:
            f.write(line + '\n')
    print(f"정보가 {filename}에 저장되었습니다.")

def get_resource_path(relative_path):
    """PyInstaller와 일반 실행 모두에서 작동하는 경로 생성 함수"""
    try:
        base_path = sys._MEIPASS  # PyInstaller로 생성된 실행 파일 경로
    except AttributeError:
        base_path = os.path.abspath(".")
    resolved_path = os.path.join(base_path, relative_path)
    print(f"디버그: 리소스 경로 = {resolved_path}")
    return resolved_path

def run_scenario(scenario_num, mode):
    """시나리오 실행 함수"""
    mode_str = 'auto' if mode == '1' else 'abnormal'
    scenario_file = f"scenario{scenario_num}_{mode_str}.py"
    scenario_path = get_resource_path(scenario_file)
    
    print(f"디버그: 실행할 시나리오 파일 = {scenario_path}")
    if os.path.exists(scenario_path):
        try:
            print(f"시나리오 {scenario_file} 실행 중...")
            subprocess.run([sys.argv[0], scenario_path], check=True)
            input("시나리오 실행이 완료되었습니다. 아무 키나 눌러서 종료하세요...")
            sys.exit(0)
        except subprocess.CalledProcessError as e:
            print(f"시나리오 실행 중 오류가 발생했습니다: {e}")
            input("아무 키나 눌러서 종료하세요...")
            sys.exit(1)
    else:
        print(f"오류: {scenario_file}을 찾을 수 없습니다.")
        input("아무 키나 눌러서 종료하세요...")
        sys.exit(1)

def main():
    """메인 함수"""
    # 프로세스 이름 설정 (Windows only)
    if platform.system() == 'Windows':
        import ctypes
        ctypes.windll.kernel32.SetConsoleTitleW("Trust_Agent")
    
    # 시스템 정보 수집
    print("시스템 정보를 수집합니다...")
    collected_info = collect_info()
    for line in collected_info:
        print(line)
    
    # 정보 저장 여부 확인
    save_choice = input("\n수집 정보를 저장할까요? (Y/N): ").lower()
    if save_choice == 'y':
        save_info(collected_info)
    
    # 시나리오 선택
    while True:
        scenario = input("\n실행할 시나리오를 입력해주세요 (1-8): ")
        if scenario.isdigit() and 1 <= int(scenario) <= 8:
            break
        print("1부터 8까지의 숫자를 입력해주세요.")
    
    # 모드 선택
    while True:
        mode = input("\nNormal (1), Abnormal (2) 중 원하는 기능의 숫자를 입력해주세요: ")
        if mode in ['1', '2']:
            break
        print("1 또는 2를 입력해주세요.")
    
    # 선택된 시나리오 실행
    run_scenario(scenario, mode)

if __name__ == "__main__":
    main()