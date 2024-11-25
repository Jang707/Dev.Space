import socket
import time
import threading

class TCPClient:
    def __init__(self, server_host='192.168.0.2', server_port=12345):
        self.server_host = server_host
        self.server_port = server_port
        self.client_socket = None
        self.is_connected = False
        self.stop_thread = False
        self.send_thread = None
        self._lock = threading.Lock()
        print(f"[Client] Initializing client for {server_host}:{server_port}")

    def connect(self):
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((self.server_host, self.server_port))
            print(f"[Client] Connected to server {self.server_host}:{self.server_port}")
            self.is_connected = True
            return True
        except socket.error as e:
            print(f"[Client] Connection error: {e}")
            self.is_connected = False
            return False
        except Exception as e:
            print(f"[Client] Unexpected error while connecting: {e}")
            self.is_connected = False
            return False

    def start(self):
        try:
            if self.connect():
                # Handshake
                print("[Client] Sending handshake")
                self.client_socket.send("RASPI4_HELLO".encode())
                
                response = self.client_socket.recv(1024).decode()
                if response == "PC_HELLO":
                    print("[Client] Handshake successful")
                    return True
                else:
                    print("[Client] Invalid handshake response")
                    return False
        except Exception as e:
            print(f"[Client] Error during start: {e}")
            return False
    
    def start_periodic_send(self, data_callback, interval=1.0):
        """
        주기적으로 데이터를 전송하는 스레드를 시작합니다.
        :param data_callback: 전송할 데이터를 반환하는 콜백 함수
        :param interval: 전송 주기 (초)
        """
        def send_thread():
            while not self.stop_thread:
                try:
                    if self.is_connected:
                        data = data_callback()
                        if data:
                            with self._lock:
                                self.sendmsg(data)
                    time.sleep(interval)
                except Exception as e:
                    print(f"[Client] Error in send thread: {e}")
                    self.reconnect()

        self.stop_thread = False
        self.send_thread = threading.Thread(target=send_thread)
        self.send_thread.daemon = True
        self.send_thread.start()

    def stop_periodic_send(self):
        """주기적 전송을 중지합니다."""
        self.stop_thread = True
        if self.send_thread:
            self.send_thread.join()

    def sendmsg(self, message):
        """
        메시지를 전송합니다.
        :param message: 전송할 메시지 (문자열)
        """
        try:
            if self.is_connected:
                print(f"[Client] Sending: {message}")
                self.client_socket.send(str(message).encode())
        except Exception as e:
            print(f"[Client] Error sending message: {e}")
            self.reconnect()

    def reconnect(self):
        """연결이 끊어졌을 때 재연결을 시도합니다."""
        print("[Client] Attempting to reconnect...")
        self.is_connected = False
        if self.client_socket:
            self.client_socket.close()
        
        while not self.is_connected and not self.stop_thread:
            if self.connect() and self.start():
                print("[Client] Reconnection successful")
                break
            time.sleep(5)

    def close(self):
        """클라이언트를 종료합니다."""
        self.stop_periodic_send()
        if self.client_socket:
            self.client_socket.close()
            self.is_connected = False
        print("[Client] Client socket closed")

if __name__ == "__main__":
    # 테스트용 예제
    def get_test_data():
        return f"Test data: {time.time()}"

    client = TCPClient()
    if client.start():
        client.start_periodic_send(get_test_data, 1.0)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            client.close()