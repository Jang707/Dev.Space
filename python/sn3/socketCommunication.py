import socket
import time
import threading
import logging
from typing import Optional, Callable, Any
import json

# 로깅 설정 추가
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TCPClient:
    def __init__(self, server_host: str = '192.168.0.2', server_port: int = 12345, 
                 reconnect_attempts: int = 3, reconnect_delay: float = 5.0):
        self.server_host = server_host
        self.server_port = server_port
        self.client_socket: Optional[socket.socket] = None
        self.is_connected = False
        self.stop_thread = False
        self.send_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        # [예외처리 보강 1] 재연결 관련 설정 추가
        self.reconnect_attempts = reconnect_attempts
        self.reconnect_delay = reconnect_delay
        self.connection_timeout = 10.0  # 연결 타임아웃 설정

        logger.info(f"Initializing client for {server_host}:{server_port}")

    def connect(self) -> bool:
        """
        서버에 연결을 시도합니다.
        
        [예외처리 보강 2] 
        - 소켓 생성 실패 처리
        - 연결 타임아웃 처리
        - 상세한 에러 로깅
        """
        try:
            # 기존 소켓이 있다면 정리
            if self.client_socket:
                self.client_socket.close()
            
            # 새로운 소켓 생성
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.settimeout(self.connection_timeout)
            
            logger.info(f"Attempting to connect to {self.server_host}:{self.server_port}")
            self.client_socket.connect((self.server_host, self.server_port))
            
            # [예외처리 보강 3] 연결 성공 후 keepalive 설정
            self.client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            self.is_connected = True
            
            logger.info("Successfully connected to server")
            return True
            
        except socket.timeout:
            logger.error("Connection attempt timed out")
            self.is_connected = False
            return False
        except socket.error as e:
            logger.error(f"Socket error during connection: {e}")
            self.is_connected = False
            return False
        except Exception as e:
            logger.error(f"Unexpected error during connection: {e}")
            self.is_connected = False
            return False

    def start(self) -> bool:
        """
        클라이언트를 시작하고 초기 핸드셰이크를 수행합니다.
        
        [예외처리 보강 4]
        - 핸드셰이크 타임아웃 처리
        - 재시도 로직 구현
        """
        for attempt in range(self.reconnect_attempts):
            try:
                if self.connect():
                    # 핸드셰이크 시도
                    logger.info("Initiating handshake")
                    self.client_socket.send("RASPI4_HELLO".encode())
                    
                    # 응답 대기
                    response = self.client_socket.recv(1024).decode()
                    if response == "PC_HELLO":
                        logger.info("Handshake successful")
                        return True
                    else:
                        logger.warning(f"Invalid handshake response: {response}")
                
                # 실패 시 재시도 전 대기
                if attempt < self.reconnect_attempts - 1:
                    logger.info(f"Retrying connection in {self.reconnect_delay} seconds...")
                    time.sleep(self.reconnect_delay)
                
            except socket.timeout:
                logger.error("Handshake timed out")
            except Exception as e:
                logger.error(f"Error during start: {e}")
        
        logger.error("All connection attempts failed")
        return False

    def start_periodic_send(self, data_callback: Callable[[], Any], interval: float = 1.0):
        """
        주기적으로 데이터를 전송하는 스레드를 시작합니다.
        
        [예외처리 보강 5]
        - 데이터 직렬화 오류 처리
        - 전송 실패 시 재연결 로직
        - 스레드 안전성 강화
        """
        def send_thread():
            consecutive_failures = 0
            while not self.stop_thread:
                try:
                    if self.is_connected:
                        data = data_callback()
                        if data:
                            # 데이터 직렬화 시도
                            try:
                                if isinstance(data, str):
                                    encoded_data = data.encode()
                                else:
                                    encoded_data = json.dumps(data).encode()
                            except (TypeError, json.JSONEncodeError) as e:
                                logger.error(f"Data serialization error: {e}")
                                continue

                            # 데이터 전송
                            with self._lock:
                                self.client_socket.send(encoded_data)
                            consecutive_failures = 0
                            
                    time.sleep(interval)
                    
                except (socket.error, ConnectionError) as e:
                    consecutive_failures += 1
                    logger.error(f"Connection error in send thread: {e}")
                    
                    # [예외처리 보강 6] 연속 실패 횟수에 따른 처리
                    if consecutive_failures >= 3:
                        logger.warning("Multiple consecutive failures, attempting to reconnect...")
                        self.reconnect()
                        consecutive_failures = 0
                        
                except Exception as e:
                    logger.error(f"Unexpected error in send thread: {e}")
                    time.sleep(interval)

        # 기존 스레드 정리
        self.stop_thread = False
        if self.send_thread and self.send_thread.is_alive():
            self.stop_thread = True
            self.send_thread.join()
            
        # 새 스레드 시작
        self.send_thread = threading.Thread(target=send_thread)
        self.send_thread.daemon = True
        self.send_thread.start()

    def stop_periodic_send(self):
        """
        [예외처리 보강 7] 스레드 종료 처리 개선
        """
        self.stop_thread = True
        if self.send_thread:
            try:
                self.send_thread.join(timeout=5.0)  # 5초 타임아웃 설정
                if self.send_thread.is_alive():
                    logger.warning("Send thread did not terminate properly")
            except Exception as e:
                logger.error(f"Error stopping send thread: {e}")

    def sendmsg(self, message: Any):
        """
        단일 메시지를 전송합니다.
        
        [예외처리 보강 8]
        - 메시지 직렬화 처리
        - 전송 실패 처리
        """
        if not self.is_connected:
            logger.error("Cannot send message: Not connected")
            return

        try:
            with self._lock:
                if isinstance(message, str):
                    encoded_message = message.encode()
                else:
                    encoded_message = json.dumps(message).encode()
                    
                logger.debug(f"Sending: {message}")
                self.client_socket.send(encoded_message)
                
        except (TypeError, json.JSONEncodeError) as e:
            logger.error(f"Message serialization error: {e}")
        except socket.error as e:
            logger.error(f"Socket error while sending message: {e}")
            self.reconnect()
        except Exception as e:
            logger.error(f"Unexpected error while sending message: {e}")

    def reconnect(self):
        """
        [예외처리 보강 9] 재연결 로직 개선
        """
        logger.info("Attempting to reconnect...")
        self.is_connected = False
        
        if self.client_socket:
            try:
                self.client_socket.close()
            except Exception as e:
                logger.error(f"Error closing socket: {e}")

        for attempt in range(self.reconnect_attempts):
            if self.stop_thread:
                logger.info("Reconnection cancelled: stop flag set")
                break
                
            if self.connect() and self.start():
                logger.info("Reconnection successful")
                return
                
            logger.warning(f"Reconnection attempt {attempt + 1}/{self.reconnect_attempts} failed")
            time.sleep(self.reconnect_delay)
        
        logger.error("All reconnection attempts failed")

    def close(self):
        """
        [예외처리 보강 10] 종료 처리 개선
        """
        logger.info("Closing client connection...")
        self.stop_periodic_send()
        
        if self.client_socket:
            try:
                self.client_socket.shutdown(socket.SHUT_RDWR)
            except Exception as e:
                logger.debug(f"Socket shutdown error: {e}")
            
            try:
                self.client_socket.close()
            except Exception as e:
                logger.error(f"Error closing socket: {e}")
                
        self.is_connected = False
        logger.info("Client connection closed")

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