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

def main():
    """메인 함수"""
    # 프로세스 이름 설정 (Windows only)
    if platform.system() == 'Windows':
        import ctypes
        ctypes.windll.kernel32.SetConsoleTitleW("TRUST_endpoint")
    
    # 시스템 정보 수집
    print("시스템 정보를 수집합니다...")
    collected_info = collect_info()
    for line in collected_info:
        print(line)
    
    # 정보 저장 여부 확인
    save_choice = input("\n수집 정보를 저장할까요? (Y/N): ").lower()
    if save_choice == 'y':
        save_info(collected_info)
    
if __name__ == "__main__":
    main()