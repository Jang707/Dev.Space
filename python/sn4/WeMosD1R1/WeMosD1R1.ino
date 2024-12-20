#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <ArduinoJson.h>
#include <DHT.h>
#include <time.h>

const char* ssid = "KIPLING_IF";
const char* password = "ai@t2023";
ESP8266WebServer server(80);

#define DHTPIN D2
#define DHTTYPE DHT11
#define LIGHT_SENSOR A0
#define GAS_SENSOR D5
#define RED_PIN D7
#define GREEN_PIN D8
#define BLUE_PIN D9

DHT dht(DHTPIN, DHTTYPE);

void setup() {
  Serial.begin(115200); // 기본 UART 설정 (디버깅용)
  Serial1.begin(115200); // UART1 설정
  
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

  if (currentTime - lastReadTime > 2000) {
    float temperature = dht.readTemperature();
    float humidity = dht.readHumidity();
    lastReadTime = currentTime;
  }

  server.handleClient();
  delay(10);
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
  float temperature = dht.readTemperature();
  Serial.print("Temperature: ");
  Serial.println(temperature);

  if (isnan(temperature)) {
    Serial.println("Failed to read temperature from DHT sensor!");
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
  float humidity = dht.readHumidity();
  Serial.print("Humidity: ");
  Serial.println(humidity);

  if (isnan(humidity)) {
    Serial.println("Failed to read humidity from DHT sensor!");
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
  int lightValue = analogRead(LIGHT_SENSOR);
  
  DynamicJsonDocument doc(1024);
  doc["light_value"] = lightValue;
  
  String response;
  serializeJson(doc, response);
  sendDataToPico("Light: " + String(lightValue));
  
  server.send(200, "application/json", response);
}

void handleGas() {
  String gasStatus = (digitalRead(GAS_SENSOR) == HIGH) ? "No more gas" : "Gas Leak Detected";
  
  DynamicJsonDocument doc(1024);
  doc["gas_status"] = gasStatus;
  
  String response;
  serializeJson(doc, response);
  sendDataToPico("Gas: " + gasStatus);
  
  server.send(200, "application/json", response);
}

void handleSetRGB() {
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
    server.send(400, "application/json", "{\"success\":false,\"error\":\"Invalid request\"}");
  }
}