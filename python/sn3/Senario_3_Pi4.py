from flask import Flask, request, render_template, jsonify
import RPi.GPIO as GPIO
import time
from RPLCD.i2c import CharLCD
import serial
from threading import Thread, Event
import socketCommunication
import json

myIP='192.168.0.4'
SERVER_IP = '192.168.0.2'
SERVER_PORT = 12345

# TCP 클라이언트 초기화
tcp_client = socketCommunication.TCPClient(SERVER_IP, SERVER_PORT)

#### below is TRU-5 = LCD 제어
ser = serial.Serial('/dev/serial0', 9600, timeout=1)
lcd = CharLCD(i2c_expander='PCF8574', address=0x27, port=1, cols=16, rows=2, dotsize=8)
lcd.clear()
connection_status = False # if flask server is connected to client, change to "True"

temperature = None
humidity = None
stop_event = Event()

def lcd_control(temperature, humidity):
    global connection_status
    lcd.clear()
    if connection_status:
        lcd.write_string("Online\n")
    else:
        lcd.write_string("Offline\n")
    lcd.write_string(f"Temp:{temperature}C Humid:{humidity}%")

#### 라즈베리파이 피코에게 온습도 측정 센서 데이터 요청 through UART
def uartRequestToPico():
    global temperature, humidity
    while not stop_event.is_set():
        try:
            if ser.in_waiting > 0:
                # 데이터 읽기
                data = ser.readline().decode('utf-8').strip()
                if data:
                    temperature, humidity = data.split(',')
                    print("Temperature: ", temperature)
                    print("Humidity: ", humidity)
                    lcd_control(temperature, humidity)
        except Exception as e:
            print("Error: ", e)
        time.sleep(2)

uart_thread = Thread(target=uartRequestToPico)
uart_thread.start()

#### below is TRU-28. 플라스크 활용 웹 인터페이스
servoPin = 17
SERVO_MAX_DUTY = 12
SERVO_MIN_DUTY = 3
cur_pos = 90

GPIO.setmode(GPIO.BCM)
GPIO.setup(servoPin, GPIO.OUT)

servo = GPIO.PWM(servoPin, 50)
servo.start(0)

app = Flask(__name__)

def servo_control(degree, delay):
    if degree > 180:
        degree = 180

    duty = SERVO_MIN_DUTY + (degree * (SERVO_MAX_DUTY - SERVO_MIN_DUTY) / 180.0)
    # print("Degree: {} to {}(Duty)".format(degree, duty))
    servo.ChangeDutyCycle(duty)
    time.sleep(delay)
    servo.ChangeDutyCycle(0)

@app.route('/sg90_control')
def sg90_control():
    global cur_pos
    servo_control(cur_pos, 0.1)
    return render_template('remote_monitor.html', degree=cur_pos)

@app.route('/sg90_control_act', methods=['GET'])
def sg90_control_act():
    if request.method == 'GET':
        global cur_pos
        degree = ''
        servo = request.args["servo"]

        if servo == 'L':
            cur_pos = cur_pos - 10
            if cur_pos < 0:
                cur_pos = 0
        else:
            cur_pos = cur_pos + 10
            if cur_pos > 180:
                cur_pos = 180

        servo_control(cur_pos, 0.1)
        return render_template('remote_monitor.html', degree=cur_pos)

@app.route('/monitor')
def monitor():
    global temperature, humidity
    return render_template('remote_monitor.html', temperature=temperature, humidity=humidity)

@app.route('/get_data', methods=['GET'])
def get_data():
    global temperature, humidity
    return jsonify({'temperature': temperature, 'humidity': humidity})

def get_sensor_data():
    """소켓으로 전송할 센서 데이터를 포맷팅합니다."""
    global temperature, humidity, cur_pos
    data = {
        'temperature': temperature,
        'humidity': humidity,
        'servo_position': cur_pos
    }
    return json.dumps(data)

if __name__ == '__main__':
    try:
        # TCP 클라이언트 시작
        if tcp_client.start():
            # 주기적 데이터 전송 시작 (2초 간격)
            # 전송데이터는 get_sensor_data 를 참조.
            tcp_client.start_periodic_send(get_sensor_data, 2.0)
        
        # Flask 서버 시작
        app.run(debug=True, port=10002, host=myIP)
    except Exception as e:
        print(f"error : {e}")
    
    finally:
        stop_event.set()
        uart_thread.join()
        tcp_client.close()
        GPIO.cleanup()