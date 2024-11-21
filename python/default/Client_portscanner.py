## Raspberry Pi 4 에서 동작시키는 코드입니다. PC 의 port listener 실행 전에 실행하셔야 합니다.
## 만약 정상적으로 동작하지 않는것 같다면 PC 와 연결된 케이블이 데이터 전송이 가능한 케이블인지를 확인해보시기 바랍니다.

import serial
import json
import glob
import time
from threading import Thread

class SerialClient:
    def __init__(self):
        self.port_mapping = {}
        self.connected = False
        self.running = True
        print("Client initialized")
    
    def save_port_mapping(self):
        try:
            with open('port_mapping.json', 'w') as f:
                json.dump(self.port_mapping, f)
            print(f"Port mapping saved: {self.port_mapping}")
        except Exception as e:
            print(f"Error saving port mapping: {e}")
    
    def try_handshake(self, port_name):
        print(f"\nTrying handshake on {port_name}")
        try:
            # 시리얼 포트 설정 추가
            ser = serial.Serial(
                port=port_name,
                baudrate=9600,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1
            )
            print(f"Serial port {port_name} opened successfully")
            
            # Handshake 대기
            start_time = time.time()
            while self.running and not self.connected and (time.time() - start_time < 5):
                if ser.in_waiting:
                    data = ser.readline().decode().strip()
                    print(f"Received data: '{data}'")
                    
                    if data == "PC_HELLO":
                        print(f"Received handshake on {port_name}")
                        response = "RASPI4_HELLO\n"
                        ser.write(response.encode())
                        print(f"Sent response: {response.strip()}")
                        
                        self.port_mapping[port_name] = "PC"
                        self.save_port_mapping()
                        self.connected = True
                        
                        # 5초 카운트다운 전송
                        print("Starting countdown")
                        for i in range(5, 0, -1):
                            message = f"{i} seconds left\n"
                            ser.write(message.encode())
                            print(f"Sent: {message.strip()}")
                            time.sleep(1)
                        
                        print("Countdown complete")
                        ser.close()
                        return True
                time.sleep(0.1)
            
            print(f"No handshake received on {port_name}")
            ser.close()
            return False
            
        except serial.SerialException as e:
            print(f"Serial error on {port_name}: {e}")
            return False
        except Exception as e:
            print(f"Unexpected error on {port_name}: {e}")
            return False
    
    def scan_ports(self):
        print("Starting port scanner")
        while self.running and not self.connected:
            #모든 사용가능한 포트 검색
            available_ports = []

            #USB Serial Port 검색
            usb_ports = glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*')
            if usb_ports:
                available_ports.extend(usb_ports)
                print("Found USB Ports:",usb_ports)
            # Hardware Serial Port 검색
            serial_ports = glob.glob('/dev/ttyS*') + glob.glob('/dev/ttyAMA*')
            if serial_ports:
                available_ports.extend(serial_ports)
                print("Found Serial Ports:",serial_ports)

            print(f"\nAll available ports: {available_ports}")

            #USB port를 우선적으로 시도
            for port in usb_ports:
                print(f"Trying USB Port:{port}")
                if self.try_handshake(port):
                    print(f"Successfully connected on USB port {port}")
                    return
            # USB port 연결 실패시 다른 시리얼 포트 시도
            for port in serial_ports:
                print(f"Trying Serial port: {port}")
                if self.try_handshake(port):
                    print(f"Successfully connected on Serial port {port}")
                    return
            print("No successful connection found, waiting before next scan...")
            time.sleep(2)
    
    def start(self):
        print("Starting client...")
        scan_thread = Thread(target=self.scan_ports)
        scan_thread.daemon = True
        scan_thread.start()
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.running = False
            print("\nClient shutting down...")

if __name__ == "__main__":
    print("=== Serial Port Client ===")
    client = SerialClient()
    client.start()