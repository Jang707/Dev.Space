import os
import time
import serial.tools.list_ports

def setup_pico():  # Removed 'self' since this is a standalone script
    """Raspberry Pi Pico 설정"""
    try:
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

            # Get the absolute paths
            script_dir = os.path.dirname(os.path.abspath(__file__))
            target_path = "D:/jang_git_space/Dev.Space/python/sn3/pico/main.py"
            
            # Get relative path from script to target
            relative_path = os.path.relpath(target_path, script_dir)
            print(f"Relative path from script to main.py: {relative_path}")
            
            # Convert back to absolute path to verify
            main_py_path = os.path.abspath(relative_path)
            print(f"Absolute path to main.py: {main_py_path}")
            
            if not os.path.exists(main_py_path):
                raise Exception(f"main.py not found at {main_py_path}")
                
            # Upload file from windows os
            upload_result = os.system(f'python -m ampy.cli --port {pico_port} put "{main_py_path}"')
            if upload_result != 0:
                raise Exception("Failed to upload main.py")
                
            # Run file on pico
            run_result = os.system(f'python -m ampy.cli --port {pico_port} run main.py')
            if run_result != 0:
                raise Exception("Failed to run main.py at raspberry pi pico")
                
            print("Raspberry pi pico successfully configured and running")
            return True
            
        except Exception as e:
            print(f"Failed to execute ampy commands : {e}")
            return False
            
    except Exception as e:
        print(f"Pico 설정 실패: {e}")
        raise

if __name__ == "__main__":
    setup_pico()