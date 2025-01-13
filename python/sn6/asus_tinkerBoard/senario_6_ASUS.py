import io
import logging
import socketserver
from threading import Condition, Thread
from http import server
import cv2

PAGE = """\
<html>
<head>
<title>TinkerBoard - Streamer with Face Detection</title>
</head>
<body>
<h1></h1>
<img src="stream.mjpg" width="640" height="480" />
</body>
</html>
"""

class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = Condition()
        print("StreamingOutput initialized.")

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()
        #print("Frame written to output buffer.")

class StreamingHandler(server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(301)
            self.send_header('Location', '/index.html')
            self.end_headers()
            print("Redirected to /index.html")
        elif self.path == '/index.html':
            content = PAGE.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
            print("Served /index.html")
        elif self.path == '/stream.mjpg':
            self.send_response(200)
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            print("Started streaming video at /stream.mjpg")
            try:
                while True:
                    with output.condition:
                        output.condition.wait()
                        frame = output.frame
                    self.wfile.write(b'--FRAME\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', len(frame))
                    self.end_headers()
                    self.wfile.write(frame)
                    self.wfile.write(b'\r\n')
                    #print("Sent a frame.")
            except Exception as e:
                logging.warning(
                    'Removed streaming client %s: %s',
                    self.client_address, str(e))
                print(f"Streaming client {self.client_address} removed: {str(e)}")
        else:
            self.send_error(404)
            self.end_headers()
            print(f"Path {self.path} not found (404).")

class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True
    def __init__(self, server_address, RequestHandlerClass):
        super().__init__(server_address, RequestHandlerClass)
        print("Streaming server initialized.")

# OpenCV 얼굴 검출기 로드
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

def process_frame(frame):
    #print("Processing frame...")
    # BGR에서 그레이스케일로 변환
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # 얼굴 검출
    faces = face_cascade.detectMultiScale(gray, 1.1, 4)
    
    # 검출된 얼굴에 사각형 그리기
    for (x, y, w, h) in faces:
        cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
    
    #print(f"Detected {len(faces)} face(s).")
    return frame

def stream_processor(camera, output):
    while True:
        ret, frame = camera.read()
        if not ret:
            print("Failed to capture frame.")
            continue
        #print("Captured a frame.")
        processed_frame = process_frame(frame)
        _, processed_jpeg = cv2.imencode('.jpg', processed_frame)
        output.write(processed_jpeg.tobytes())

if __name__ == "__main__":
    camera = cv2.VideoCapture(5)
    if not camera.isOpened():
        #print("Cannot open camera")
        exit()
    #print("Camera opened successfully.")
    
    output = StreamingOutput()
    
    processor_thread = Thread(target=stream_processor, args=(camera, output))
    processor_thread.daemon = True
    processor_thread.start()
    print("Stream processing thread started.")

    try:
        address = ('', 8000)
        server = StreamingServer(address, StreamingHandler)
        print("Starting server at http://localhost:8000")
        server.serve_forever()
    finally:
        camera.release()
        print("Camera released.")
