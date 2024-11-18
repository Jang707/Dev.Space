import socket
import time

class TCPClient:
    def __init__(self, server_host='192.168.0.2', server_port=12345):
        self.server_host = server_host
        self.server_port = server_port
        self.client_socket = None
        print(f"[Client] Initializing client for {server_host}:{server_port}")

    def connect(self):
        try:
            # 소켓 생성
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # 서버 연결
            self.client_socket.connect((self.server_host, self.server_port))
            print(f"[Client] Connected to server {self.server_host}:{self.server_port}")
            return True
        except socket.error as e:
            print(f"[Client] Connection error: {e}")
            return False
        except Exception as e:
            print(f"[Client] Unexpected error while connecting: {e}")
            return False

    def start(self):
        try:
            while True:  # 연결 재시도 루프
                if self.connect():
                    try:
                        # Handshake
                        print("[Client] Sending handshake")
                        self.client_socket.send("RASPI4_HELLO".encode())
                        
                        response = self.client_socket.recv(1024).decode()
                        if response == "PC_HELLO":
                            print("[Client] Handshake successful")
                            
                            # 5초 카운트다운 전송
                            for i in range(5, 0, -1):
                                message = f"{i} seconds left"
                                print(f"[Client] Sending: {message}")
                                self.client_socket.send(message.encode())
                                time.sleep(1)
                            
                            print("[Client] Countdown complete")
                            break  # 정상적으로 완료되면 루프 종료
                        else:
                            print("[Client] Invalid handshake response")
                            
                    except socket.error as e:
                        print(f"[Client] Socket error during communication: {e}")
                    except Exception as e:
                        print(f"[Client] Error during communication: {e}")
                    finally:
                        self.client_socket.close()
                        print("[Client] Connection closed")
                
                print("[Client] Retrying in 5 seconds...")
                time.sleep(5)

        except KeyboardInterrupt:
            print("\n[Client] Client shutting down...")
        except Exception as e:
            print(f"[Client] Unexpected error: {e}")
        finally:
            if self.client_socket:
                self.client_socket.close()
                print("[Client] Client socket closed")

if __name__ == "__main__":
    client = TCPClient()
    client.start()
