import socket
import datetime
import time
from threading import Thread
from typing import Callable, Optional

class TCPServer:
    def __init__(self, host: str = '192.168.0.2', port: int = 12345):
        self.host = host
        self.port = port
        self.server_socket = None
        self.is_running = False
        self.server_thread: Optional[Thread] = None
        self.data_callback: Optional[Callable[[str], None]] = None
        self._log_to_callback("[Server] Initializing server on {host}:{port}")
    
    def _log_to_callback(self, message: str) -> None:
        """로그 메시지를 callback을 통해 GUI로 전송"""
        if self.data_callback:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            formatted_message = f"[{timestamp}] {message}"
            self.data_callback(formatted_message)
    
    def set_callback(self, callback: Callable[[str], None]) -> None:
        self.data_callback = callback
        self._log_to_callback("[Server] Callback function registered")

    def setup_server(self) -> bool:
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen()
            self._log_to_callback(f"[Server] Server is listening on {self.host}:{self.port}")
            return True
        except Exception as e:
            self._log_to_callback(f"[Server] Error setting up server: {e}")
            return False

    def handle_client(self, client_socket: socket.socket, client_address: tuple) -> None:
        try:
            self._log_to_callback(f"[Server] Connected by {client_address}")
            
            # Handshake
            data = client_socket.recv(1024).decode()
            if data == "RASPI4_HELLO":
                self._log_to_callback("[Server] Received handshake from Raspberry Pi 4")
                client_socket.send("PC_HELLO".encode())

                # 데이터 수신 대기
                while self.is_running:
                    data = client_socket.recv(1024).decode()
                    if not data:
                        self._log_to_callback("[Server] Connection closed by client")
                        break
                    
                    self._log_to_callback(f"[Server] Received: {data}")

        except socket.error as e:
            self._log_to_callback(f"[Server] Socket error while handling client: {e}")
        except Exception as e:
            self._log_to_callback(f"[Server] Error while handling client: {e}")
        finally:
            client_socket.close()
            self._log_to_callback("[Server] Client connection closed")

    def server_loop(self) -> None:
        if not self.setup_server():
            return

        while self.is_running:
            try:
                self._log_to_callback("[Server] Waiting for connection...")
                client_socket, client_address = self.server_socket.accept()
                client_thread = Thread(target=self.handle_client, 
                                    args=(client_socket, client_address))
                client_thread.daemon = True
                client_thread.start()
            except socket.error as e:
                if self.is_running:
                    self._log_to_callback(f"[Server] Socket error in main loop: {e}")
            except Exception as e:
                if self.is_running:
                    self._log_to_callback(f"[Server] Error in main loop: {e}")

    def start(self) -> bool:
        if self.is_running:
            self._log_to_callback("[Server] Server is already running")
            return False

        self.is_running = True
        self.server_thread = Thread(target=self.server_loop)
        self.server_thread.daemon = True
        self.server_thread.start()
        self._log_to_callback("[Server] Server started")
        return True

    def stop(self) -> None:
        self._log_to_callback("[Server] Stopping server...")
        self.is_running = False
        
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception as e:
                self._log_to_callback(f"[Server] Error while closing server socket: {e}")
        
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=5.0)
            
        self._log_to_callback("[Server] Server stopped")

if __name__ == "__main__":
    def print_callback(data: str) -> None:
        print(f"Callback received: {data}")

    server = TCPServer()
    server.set_callback(print_callback)
    
    try:
        server.start()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()