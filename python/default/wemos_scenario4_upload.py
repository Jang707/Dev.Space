import subprocess

# Arduino CLI 경로
ARDUINO_CLI_PATH = "arduino-cli"

# 스케치 파일 위치 (.ino 파일)
SKETCH_PATH = "D:\\Dev.Space\\python\\sn4\\WeMosD1R1\\WeMosD1R1.ino"

# 보드 설정 (WeMos D1 R1 기준)
BOARD_TYPE = "esp8266:esp8266:d1"
PORT = "COM3"

# 1. 컴파일
def compile_sketch():
    compile_cmd = [
        ARDUINO_CLI_PATH,
        "compile",
        "--fqbn",
        BOARD_TYPE,
        SKETCH_PATH,
    ]
    print("컴파일 중...")
    result = subprocess.run(compile_cmd, capture_output=True, text=True, encoding="utf-8")
    if result.returncode == 0:
        print("컴파일 성공!")
    else:
        print(f"컴파일 실패:\n{result.stderr}")
        return False
    return True

# 2. 업로드
def upload_sketch():
    upload_cmd = [
        ARDUINO_CLI_PATH,
        "upload",
        "--fqbn",
        BOARD_TYPE,
        "--port",
        PORT,
        SKETCH_PATH,
    ]
    print("업로드 중...")
    result = subprocess.run(upload_cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print("업로드 성공!")
    else:
        print(f"업로드 실패:\n{result.stderr}")

# 실행
if __name__ == "__main__":
    if compile_sketch():
        upload_sketch()