from quart import Quart, render_template, request, jsonify, websocket
import aiohttp
import asyncio
from socketCommunication import TCPClient
import json
import threading

app = Quart(__name__)

# 글로벌 변수 초기화
temperature = "N/A"
humidity = "N/A"
light_value = "N/A"
gas_status = "Normal"
rgb_color = "#FFFFFF"

# Arduino 서버 주소
arduino_ip = '192.168.0.8'
arduino_port = 80
arduino_base_url = f'http://{arduino_ip}:{arduino_port}'

# TCP 클라이언트 초기화
tcp_client = TCPClient(server_host='192.168.0.2', server_port=12345)
clients = []

def send_sensor_data():
    """센서 데이터를 TCP를 통해 전송하는 함수"""
    message = f"Temperature: {temperature}°C, Humidity: {humidity}%, Light: {light_value}, Gas: {gas_status}"
    return message

async def fetch_sensor_data(session, endpoint):
    try:
        async with session.get(f'{arduino_base_url}/{endpoint}') as response:
            if response.status == 200:
                return await response.json()
            return None
    except Exception as e:
        print(f"Error fetching {endpoint}: {e}")
        return None

async def read_sensors():
    global temperature, humidity, light_value, gas_status
    async with aiohttp.ClientSession() as session:
        while True:
            tasks = [
                fetch_sensor_data(session, 'temperature'),
                fetch_sensor_data(session, 'humidity'),
                fetch_sensor_data(session, 'light'),
                fetch_sensor_data(session, 'gas')
            ]
            results = await asyncio.gather(*tasks)

            prev_gas_status = gas_status

            if results[0]:
                temperature = results[0]['temperature']
            if results[1]:
                humidity = results[1]['humidity']
            if results[2]:
                light_value = results[2]['light_value']
            if results[3]:
                handling_gas(results[3]['gas_status'])

            # Gas 상태가 변경되었을 때 TCP로 전송
            if prev_gas_status != gas_status:
                tcp_client.sendmsg({'gas_status': gas_status})

            data = {
                'temperature': temperature,
                'humidity': humidity,
                'light_value': light_value,
                'gas_status': gas_status,
                'rgb_color': rgb_color
            }
            for client in clients:
                await client.send_json(data)

            await asyncio.sleep(1.5)

def handling_gas(response):
    global gas_status
    if response == "Gas Leak Detected":
        gas_status = "Alert!!"
    elif response == "No more gas":
        gas_status = "Normal"

@app.route('/')
async def index():
    return await render_template('index.html', temperature=temperature, humidity=humidity, 
                               light_value=light_value, gas_status=gas_status, rgb_color=rgb_color)

@app.route('/set_rgb', methods=['POST'])
async def set_rgb():
    global rgb_color
    data = await request.get_json()
    r = data['r']
    g = data['g']
    b = data['b']
    rgb_command = {'r': r, 'g': g, 'b': b}

    async with aiohttp.ClientSession() as session:
        async with session.post(f'{arduino_base_url}/set_rgb', json=rgb_command) as response:
            if response.status == 200:
                result = await response.json()
                if result.get('success'):
                    rgb_color = f'#{int(r):02x}{int(g):02x}{int(b):02x}'
                    
                    # RGB 값이 변경될 때 TCP로 전송
                    tcp_client.sendmsg({'rgb_color': rgb_color})
                    
                    data = {'color': rgb_color}
                    for client in clients:
                        await client.send_json(data)
                    return jsonify(success=True, color=rgb_color)

    return jsonify(success=False)

@app.before_serving
async def startup():
    # TCP 클라이언트 시작
    if tcp_client.start():
        tcp_client.start_periodic_send(send_sensor_data, 1.0)
    app.sensor_task = asyncio.create_task(read_sensors())

@app.after_serving
async def shutdown():
    app.sensor_task.cancel()
    await app.sensor_task
    tcp_client.close()

@app.websocket('/ws')
async def ws():
    clients.append(websocket._get_current_object())
    try:
        while True:
            await websocket.receive()
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        clients.remove(websocket._get_current_object())

if __name__ == '__main__':
    from hypercorn.config import Config
    from hypercorn.asyncio import serve

    config = Config()
    config.bind = ["192.168.0.2:5000"]
    asyncio.run(serve(app, config))