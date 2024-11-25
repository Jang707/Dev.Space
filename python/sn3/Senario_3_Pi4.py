from flask import Flask, request, render_template, jsonify
import RPi.GPIO as GPIO
import time
from RPLCD.i2c import CharLCD
import serial
from threading import Thread, Event, Lock
import socketCommunication
import json
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

# 로깅 설정 개선
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ServoSpecs:
    """서보 모터 스펙 정의"""
    MIN_ANGLE: int = 0
    MAX_ANGLE: int = 180
    MIN_DUTY: float = 2.5  # 수정된 duty cycle 값
    MAX_DUTY: float = 12.5  # 수정된 duty cycle 값
    FREQUENCY: int = 50
    STEP_DELAY: float = 0.01  # 점진적 이동을 위한 딜레이

class ServoController:
    def __init__(self, pin: int, specs: Optional[ServoSpecs] = None):
        self.pin = pin
        self.specs = specs or ServoSpecs()
        self.current_angle = 90  # 초기 각도
        self.lock = Lock()
        self.initialized = False
        self.last_error_time = 0
        self.error_count = 0
        
        self._initialize_gpio()

    def _initialize_gpio(self) -> None:
        """GPIO 및 PWM 초기화"""
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup(self.pin, GPIO.OUT)
            
            self.pwm = GPIO.PWM(self.pin, self.specs.FREQUENCY)
            initial_duty = self._angle_to_duty(90)
            self.pwm.start(initial_duty)
            time.sleep(0.5)  # 초기화 안정화 대기
            self.pwm.ChangeDutyCycle(0)  # 떨림 방지
            
            self.initialized = True
            logger.info(f"Servo initialized on pin {self.pin} with {self.specs.FREQUENCY}Hz frequency")
        except Exception as e:
            logger.error(f"Failed to initialize servo: {e}")
            raise

    def _angle_to_duty(self, angle: float) -> float:
        """각도를 duty cycle로 변환"""
        # 각도 범위 제한
        angle = max(self.specs.MIN_ANGLE, min(self.specs.MAX_ANGLE, angle))
        
        # duty cycle 계산
        duty_range = self.specs.MAX_DUTY - self.specs.MIN_DUTY
        duty = self.specs.MIN_DUTY + (angle * duty_range / 180.0)
        return duty

    def _smooth_move(self, target_angle: int) -> bool:
        """점진적으로 서보 모터 이동"""
        start_angle = self.current_angle
        angle_diff = target_angle - start_angle
        
        if abs(angle_diff) <= 1:
            return self._direct_move(target_angle)

        steps = abs(angle_diff)
        angle_increment = 1 if angle_diff > 0 else -1

        try:
            for step in range(steps):
                current = start_angle + (step * angle_increment)
                if not self._direct_move(current):
                    return False
                time.sleep(self.specs.STEP_DELAY)
            
            # 최종 목표 각도로 이동
            return self._direct_move(target_angle)
        
        except Exception as e:
            logger.error(f"Smooth move failed: {e}")
            return False

    def _direct_move(self, angle: int) -> bool:
        """직접 서보 모터 제어"""
        try:
            duty = self._angle_to_duty(angle)
            self.pwm.ChangeDutyCycle(duty)
            time.sleep(0.1)  # 안정화 대기
            self.pwm.ChangeDutyCycle(0)  # 떨림 방지
            return True
        except Exception as e:
            logger.error(f"Direct move failed: {e}")
            return False

    def move_to(self, angle: int) -> bool:
        """서보 모터를 지정된 각도로 이동"""
        if not self.initialized:
            logger.error("Servo not initialized")
            return False

        with self.lock:
            try:
                logger.info(f"Moving servo from {self.current_angle} to {angle} degrees")
                
                if self._smooth_move(angle):
                    self.current_angle = angle
                    self.error_count = 0
                    logger.info(f"Servo successfully moved to {angle} degrees")
                    return True
                
                self.error_count += 1
                current_time = time.time()
                
                # 에러가 자주 발생하면 재초기화 시도
                if self.error_count >= 3 and (current_time - self.last_error_time) < 60:
                    logger.warning("Multiple servo errors detected, attempting reinitialization")
                    self._initialize_gpio()
                    self.error_count = 0
                
                self.last_error_time = current_time
                return False
                
            except Exception as e:
                logger.error(f"Servo control error: {e}")
                return False

    def get_current_angle(self) -> int:
        """현재 서보 모터 각도 반환"""
        with self.lock:
            return self.current_angle

    def cleanup(self) -> None:
        """서보 모터 정리"""
        try:
            if hasattr(self, 'pwm'):
                self.pwm.stop()
            GPIO.cleanup(self.pin)
            logger.info("Servo cleanup completed")
        except Exception as e:
            logger.error(f"Servo cleanup error: {e}")

class SensorData:
    def __init__(self):
        self.temperature: Optional[float] = None
        self.humidity: Optional[float] = None
        self.servo_position: int = 90
        self.lock = Lock()
        self.last_update = time.time()
    
    def update_sensor_data(self, temperature: Optional[float], humidity: Optional[float]) -> None:
        with self.lock:
            self.temperature = temperature
            self.humidity = humidity
            self.last_update = time.time()
    
    def update_servo_position(self, position: int) -> None:
        with self.lock:
            self.servo_position = position
            self.last_update = time.time()
    
    def get_data(self) -> Dict[str, Any]:
        with self.lock:
            return {
                'temperature': self.temperature,
                'humidity': self.humidity,
                'servo_position': self.servo_position,
                'last_update': self.last_update
            }

class LCDController:
    def __init__(self):
        try:
            self.lcd = CharLCD(i2c_expander='PCF8574', address=0x27, port=1, cols=16, rows=2, dotsize=8)
            self.lcd.clear()
            self.lock = Lock()
            self.connection_status = False
        except Exception as e:
            logger.error(f"Error initializing LCD: {e}")
            raise
    
    def update_display(self, temperature: Optional[float], humidity: Optional[float]):
        with self.lock:
            try:
                self.lcd.clear()
                status_str = "Online" if self.connection_status else "Offline"
                self.lcd.write_string(f"{status_str}\n")
                
                temp_str = f"{temperature}C" if temperature is not None else "N/A"
                humid_str = f"{humidity}%" if humidity is not None else "N/A"
                self.lcd.write_string(f"T:{temp_str} H:{humid_str}")
            except Exception as e:
                logger.error(f"Error updating LCD: {e}")

class SensorReader:
    def __init__(self, serial_port: str = '/dev/serial0', baud_rate: int = 9600):
        try:
            self.ser = serial.Serial(serial_port, baud_rate, timeout=1)
            self.stop_event = Event()
            self.lock = Lock()
        except Exception as e:
            logger.error(f"Error initializing serial port: {e}")
            raise
    
    def read_data(self) -> tuple[Optional[float], Optional[float]]:
        with self.lock:
            try:
                if self.ser.in_waiting > 0:
                    data = self.ser.readline().decode('utf-8').strip()
                    if data:
                        temp, humid = data.split(',')
                        return float(temp), float(humid)
            except Exception as e:
                logger.error(f"Error reading sensor data: {e}")
            return None, None

def create_app():
    app = Flask(__name__)
    sensor_data = SensorData()
    servo_controller = ServoController(17)  # GPIO 17 사용
    lcd_controller = LCDController()
    sensor_reader = SensorReader()
    
    # TCP 클라이언트 초기화
    tcp_client = socketCommunication.TCPClient('192.168.0.2', 12345)
    
    def sensor_thread():
        while not sensor_reader.stop_event.is_set():
            try:
                temp, humid = sensor_reader.read_data()
                sensor_data.update_sensor_data(temp, humid)     ######
                lcd_controller.update_display(temp, humid)
                time.sleep(2)
            except Exception as e:
                logger.error(f"Error in sensor thread: {e}")
    
    @app.route('/sg90_control')
    def sg90_control():
        try:
            current_pos = servo_controller.get_current_angle()
            success = servo_controller.move_to(current_pos)
            if not success:
                logger.error("Failed to control servo")
                return jsonify({'error': 'Servo control failed'}), 500
            return render_template('remote_monitor.html', degree=current_pos)
        except Exception as e:
            logger.error(f"Error in sg90_control: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/sg90_control_act', methods=['GET'])
    def sg90_control_act():
        if request.method == 'GET':
            try:
                current_pos = servo_controller.get_current_angle()
                servo_command = request.args.get("servo", "")
                
                if servo_command == 'L':
                    new_pos = max(0, current_pos - 10)
                elif servo_command == 'R':
                    new_pos = min(180, current_pos + 10)
                else:
                    return jsonify({'error': 'Invalid servo command'}), 400

                logger.info(f"Attempting to move servo from {current_pos} to {new_pos}")
                
                if servo_controller.move_to(new_pos):
                    sensor_data.update_servo_position(new_pos)
                    logger.info(f"Servo successfully moved to {new_pos}")
                    return render_template('remote_monitor.html', degree=new_pos)
                else:
                    logger.error("Servo movement failed")
                    return jsonify({'error': 'Servo movement failed'}), 500
                    
            except Exception as e:
                logger.error(f"Error in sg90_control_act: {e}")
                return jsonify({'error': str(e)}), 500
    
    @app.route('/monitor')
    def monitor():
        data = sensor_data.get_data()
        return render_template('remote_monitor.html', 
                             temperature=data['temperature'], 
                             humidity=data['humidity'])
    
    @app.route('/get_data', methods=['GET'])
    def get_data():
        return jsonify(sensor_data.get_data())
    
    # 센서 데이터 읽기 쓰레드 시작
    sensor_thread = Thread(target=sensor_thread, daemon=True)
    sensor_thread.start()
    
    # TCP 클라이언트 시작
    if tcp_client.start():
        tcp_client.start_periodic_send(sensor_data.get_data, 2.0)
    
    return app

if __name__ == '__main__':
    app = create_app()
    try:
        app.run(debug=False, port=10002, host='192.168.0.4')  # debug=False로 설정하여 reloader 비활성화
    except KeyboardInterrupt:
        logger.info("Application shutting down...")
    finally:
        logger.info("Cleaning up resources...")
        GPIO.cleanup()