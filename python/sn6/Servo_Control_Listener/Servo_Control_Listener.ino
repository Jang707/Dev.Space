#include <Servo.h> 
Servo servo; // servo변수 정의

int servoAngle = 0; // 서모보터 각도 변수 정의
void setup() {
  Serial.begin(9600);
  servo.attach(D4); //servo변수에게 제어핀 할당
}

void loop() {
  if(Serial.available() > 0) { // p5js => Arduino
    byte actionCode = Serial.read(); // 시리얼 데이터 읽기
    
    // 웹에서 보낸 값에 따라 서보모터 각도를 변경해 줍니다
    switch (actionCode) {
      case 1 :
        servoAngle = 270;
        //servoAngle = 180; 
        Serial.println("case 1 detected");
        servo.write(servoAngle);
        delay(1000);
        break;
      case 2 :
        servoAngle = 180;
        //servoAngle = 120;
        Serial.println("case 2 detected");
        servo.write(servoAngle);
        delay(1000);
        break;
      case 3 :
        servoAngle = 90;
        //servoAngle = 60;
        Serial.println("case 3 detected");
        servo.write(servoAngle);
        delay(1000);
        break;
      case 4 :
        servoAngle = 0;
        Serial.println("case 4 detected");
        servo.write(servoAngle);
        delay(1000);
        break;
      default :
        break;
    }
  }
   //servo.write(servoAngle); //서보모터 각도 변경
}
