## PC 에서 동작시키는 코드입니다. 라즈베리파이 에서 먼저 port scanner 코드를 동작시킨 이후 실행해야합니다.

import serial
import serial.tools.list_ports
import json
import datetime
import time
from threading import Thread

class SerialServer:
    def __init__(self):
        self.port_mapping = {}
        self.connected_devices = {}
        self.running = True
        print("Server initialized")
    
    def save_port_mapping(self):
        try:
            with open('port_mapping.json', 'w') as f:
                json.dump(self.port_mapping, f)
            print(f"Port mapping saved: {self.port_mapping}")
        except Exception as e:
            print(f"Error saving port mapping: {e}")
    
    def handle_client(self, port_name):
        print(f"\nAttempting to handle client on {port_name}")
        try:
            # 시리얼 포트가 이미 사용 중인지 확인
            try:
                ser = serial.Serial(port_name)
                ser.close()
            except:
                print(f"Port {port_name} is already in use or inaccessible")
                return

        # 시리얼 포트 설정 및 열기
            ser = serial.Serial(
                port=port_name,
                baudrate=9600,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1
            )
        
            print(f"Serial port {port_name} opened successfully")
        
            # Handshake 시도
            print(f"Sending handshake to {port_name}")
            ser.write(b"PC_HELLO\n")
            ser.flush()  # 버퍼 비우기 추가
        
            # 응답 대기
            start_time = time.time()
            while time.time() - start_time < 5:  # 5초 동안 응답 대기
                if ser.in_waiting:
                    response = ser.readline().decode().strip()
                    print(f"Received response: '{response}'")
                
                    if response == "RASPI4_HELLO":
                        print(f"Handshake successful on {port_name}")
                        self.port_mapping[port_name] = "Raspi4"
                        self.save_port_mapping()
                    
                        # 데이터 수신 대기
                        while self.running:
                            if ser.in_waiting:
                                data = ser.readline().decode().strip()
                                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                print(f"[{timestamp}] Received from {port_name}: {data}")
                        break
                time.sleep(0.1)
        
            print(f"No response received from {port_name} after 5 seconds")
            ser.close()
            print(f"Connection closed for {port_name}")
        
        except serial.SerialException as e:
            print(f"Serial error on {port_name}: {e}")
        except Exception as e:
            print(f"Unexpected error on {port_name}: {e}")
    
    def scan_ports(self):
        print("Starting port scanner")
        while self.running:
            available_ports = [p.device for p in serial.tools.list_ports.comports()]
            print(f"\nAvailable ports: {available_ports}")
            
            # 새로운 포트 검사
            for port in available_ports:
                if port not in self.connected_devices:
                    print(f"New port found: {port}")
                    client_thread = Thread(target=self.handle_client, args=(port,))
                    client_thread.daemon = True
                    client_thread.start()
                    self.connected_devices[port] = client_thread
            
            # 연결 해제된 포트 정리
            disconnected_ports = [p for p in self.connected_devices.keys() 
                                if p not in available_ports]
            for port in disconnected_ports:
                print(f"Port disconnected: {port}")
                del self.connected_devices[port]
                if port in self.port_mapping:
                    del self.port_mapping[port]
            
            time.sleep(2)  # 스캔 간격 증가

    def start(self):
        print("Starting server...")
        scan_thread = Thread(target=self.scan_ports)
        scan_thread.daemon = True
        scan_thread.start()
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.running = False
            print("\nServer shutting down...")

if __name__ == "__main__":
    print("=== Serial Port Server ===")
    server = SerialServer()
    server.start()