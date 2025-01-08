#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <ArduinoJson.h>
#include <DHT.h>
#include <time.h>
#include <LiquidCrystal_I2C.h>

const char* ssid = "KIPLING_IF";
const char* password = "ai@t2023";
ESP8266WebServer server(80);
LiquidCrystal_I2C lcd(0x27, 20, 2);

#define DHTPIN D6
#define DHTTYPE DHT11
#define LIGHT_SENSOR A0
#define GAS_SENSOR D13
#define RED_PIN D7
#define GREEN_PIN D8
#define BLUE_PIN D9

DHT dht(DHTPIN, DHTTYPE);
bool gasLeakDetected = false;

void setup() {
  Serial.begin(115200);
  Serial1.begin(115200);
  
  lcd.init();
  lcd.backlight();
  lcd.setCursor(1,0);
  lcd.print("Arduino Start");
  lcd.setCursor(1,0);
  lcd.print("Listening...");

  pinMode(RED_PIN, OUTPUT);
  pinMode(GREEN_PIN, OUTPUT);
  pinMode(BLUE_PIN, OUTPUT);
  pinMode(GAS_SENSOR, INPUT);
  
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.println("Connecting to WiFi...");
  }
  Serial.println("Connected to WiFi");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());
  
  server.on("/temperature", HTTP_GET, handleTemperature);
  server.on("/humidity", HTTP_GET, handleHumidity);
  server.on("/light", HTTP_GET, handleLight);
  server.on("/gas", HTTP_GET, handleGas);
  server.on("/set_rgb", HTTP_POST, handleSetRGB);
  
  server.begin();
  Serial.println("HTTP server started");
  
  dht.begin();
  delay(2000);
  configTime(9 * 3600, 0, "pool.ntp.org", "time.nist.gov");
}

void loop() {
  static unsigned long lastReadTime = 0;
  unsigned long currentTime = millis();

  // 가스 센서 확인
  checkGasStatus();
  
  if (!gasLeakDetected) {  // 가스 누출이 없을 때만 정상 동작
    if (currentTime - lastReadTime > 2000) {
      float temperature = dht.readTemperature();
      float humidity = dht.readHumidity();
      if (!isnan(temperature) && !isnan(humidity)) {
        Serial.print("Temperature: ");
        Serial.println(temperature);
        Serial.print("Humidity: ");
        Serial.println(humidity)

        lastReadTime = currentTime;
        // LCD 업데이트
        lcd.clear();
        lcd.setCursor(0,0);
        lcd.print("Tmp:" + String(temperature));
        lcd.setCursor(0,1);
        lcd.print("Humid:" + String(humidity));
      } else {
        Serial.println(" 센서 읽기 실패 ");
      }
    }
  }

  server.handleClient();
  delay(10);
}

void checkGasStatus() {
  bool currentGasStatus = (digitalRead(GAS_SENSOR) == LOW);  // LOW일 때 가스 감지
  
  if (currentGasStatus && !gasLeakDetected) {
    // 가스가 처음 감지되었을 때
    gasLeakDetected = true;
    
    // LCD에 경고 표시
    lcd.clear();
    lcd.setCursor(0,0);
    lcd.print("WARNING!");
    lcd.setCursor(0,1);
    lcd.print("GAS LEAK DETECTED!");
    
    // LED를 빨간색으로 설정
    analogWrite(RED_PIN, 255);
    analogWrite(GREEN_PIN, 0);
    analogWrite(BLUE_PIN, 0);
    
    // 로그 전송
    sendDataToPico("ALERT: Gas Leak Detected!");
  }
  else if (!currentGasStatus && gasLeakDetected) {
    // 가스 누출이 해제되었을 때
    gasLeakDetected = false;
    
    // LED 초기화
    analogWrite(RED_PIN, 0);
    analogWrite(GREEN_PIN, 0);
    analogWrite(BLUE_PIN, 0);
    
    sendDataToPico("Gas Leak Cleared");
  }
}

void sendDataToPico(String data) {
  time_t now;
  time(&now);
  char timestamp[25];
  strftime(timestamp, sizeof(timestamp), "%Y-%m-%d %H:%M:%S", localtime(&now));
  
  String message = String(timestamp) + " - " + data;
  Serial1.println(message);
}

void handleTemperature() {
  if (gasLeakDetected) {
    server.send(503, "application/json", "{\"error\":\"System locked due to gas leak\"}");
    return;
  }
  
  float temperature = dht.readTemperature();
  
  if (isnan(temperature)) {
    server.send(500, "application/json", "{\"error\":\"Failed to read temperature\"}");
    return;
  }
  
  DynamicJsonDocument doc(1024);
  doc["temperature"] = temperature;
  
  String response;
  serializeJson(doc, response);
  sendDataToPico("Temperature: " + String(temperature));
  server.send(200, "application/json", response);
}

void handleHumidity() {
  if (gasLeakDetected) {
    server.send(503, "application/json", "{\"error\":\"System locked due to gas leak\"}");
    return;
  }
  
  float humidity = dht.readHumidity();
  
  if (isnan(humidity)) {
    server.send(500, "application/json", "{\"error\":\"Failed to read humidity\"}");
    return;
  }
  
  DynamicJsonDocument doc(1024);
  doc["humidity"] = humidity;
  
  String response;
  serializeJson(doc, response);
  sendDataToPico("Humidity: " + String(humidity));
  server.send(200, "application/json", response);
}

void handleLight() {
  if (gasLeakDetected) {
    server.send(503, "application/json", "{\"error\":\"System locked due to gas leak\"}");
    return;
  }
  
  int lightValue = analogRead(LIGHT_SENSOR);
  
  DynamicJsonDocument doc(1024);
  doc["light_value"] = lightValue;
  
  String response;
  serializeJson(doc, response);
  sendDataToPico("Light: " + String(lightValue));
  server.send(200, "application/json", response);
}

void handleGas() {
  String gasStatus = gasLeakDetected ? "Gas Leak Detected" : "No more gas";
  
  DynamicJsonDocument doc(1024);
  doc["gas_status"] = gasStatus;
  
  String response;
  serializeJson(doc, response);
  sendDataToPico("Gas: " + gasStatus);
  
  server.send(200, "application/json", response);
}

void handleSetRGB() {
  if (gasLeakDetected) {
    server.send(503, "application/json", "{\"error\":\"System locked due to gas leak\"}");
    return;
  }
  
  if (server.hasArg("plain")) {
    String body = server.arg("plain");
    DynamicJsonDocument doc(1024);
    deserializeJson(doc, body);
    
    int r = doc["r"];
    int g = doc["g"];
    int b = doc["b"];
    
    analogWrite(RED_PIN, r);
    analogWrite(GREEN_PIN, g);
    analogWrite(BLUE_PIN, b);
    
    String rgbCommand = String(r) + "," + String(g) + "," + String(b);
    sendDataToPico("RGB: " + rgbCommand);
    
    server.send(200, "application/json", "{\"success\":true}");
  } else {
    server.send(400, "application/json", "{\"error\":\"Invalid request\"}");
  }
}
