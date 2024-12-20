from quart import Quart, render_template, request, jsonify, websocket
import aiohttp
import asyncio

app = Quart(__name__)

# 글로벌 변수 초기화
temperature = "N/A"
humidity = "N/A"
light_value = "N/A"
gas_status = "Normal"
rgb_color = "#FFFFFF"

# Arduino 서버 주소
arduino_ip = '192.168.0.8'  # Arduino UNO의 IP 주소
arduino_port = 80  # Arduino UNO의 포트 번호
arduino_base_url = f'http://{arduino_ip}:{arduino_port}'

clients = []

# 에러 처리
async def fetch_sensor_data(session, endpoint):
    try:
        async with session.get(f'{arduino_base_url}/{endpoint}') as response:
            if response.status == 200:
                return await response.json()
            else:
                print(f"Error fetching {endpoint}: Status {response.status}")
                return None
    except Exception as e:
        print(f"Exception while fetching {endpoint}: {e}")
        return None
async def fetch_sensor_data(session, endpoint):
    async with session.get(f'{arduino_base_url}/{endpoint}') as response:
        if response.status == 200:
            return await response.json()
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

            if results[0]:
                temperature = results[0]['temperature']
            if results[1]:
                humidity = results[1]['humidity']
            if results[2]:
                light_value = results[2]['light_value']
            if results[3]:
                handling_gas(results[3]['gas_status'])

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
    return await render_template('index.html', temperature=temperature, humidity=humidity, light_value=light_value,
                                 gas_status=gas_status, rgb_color=rgb_color)

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
                    data = {'color': rgb_color}
                    for client in clients:
                        await client.send_json(data)
                    return jsonify(success=True, color=rgb_color)

    return jsonify(success=False)

@app.before_serving
async def startup():
    app.sensor_task = asyncio.create_task(read_sensors())

@app.after_serving
async def shutdown():
    app.sensor_task.cancel()
    await app.sensor_task

@app.websocket('/ws')
async def ws():
    clients.append(websocket._get_current_object())
    try:
        while True:
            await websocket.receive()
    except:
        pass
    finally:
        clients.remove(websocket._get_current_object())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)