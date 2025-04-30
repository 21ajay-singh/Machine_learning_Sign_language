#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <Servo.h>

// LCD setup
LiquidCrystal_I2C lcd(0x27, 16, 2);

// Servo
Servo servo;
int servoPin = D4;

// Ultrasonic sensor pins
const int trigLeft = D5;
const int echoLeft = D6;
const int trigRight = D7;
const int echoRight = D8;

// Word buffer
String incomingWord = "";

// Servo control states
int currentServoPos = 90;  // Track current servo position
bool objectDetectedBefore = false;  // Track previous detection state

void setup() {
  Serial.begin(9600);
  lcd.init();
  lcd.backlight();

  servo.attach(servoPin);
  servo.write(currentServoPos);  // Start at 90 degrees

  pinMode(trigLeft, OUTPUT);
  pinMode(echoLeft, INPUT);
  pinMode(trigRight, OUTPUT);
  pinMode(echoRight, INPUT);

  lcd.setCursor(0, 0);
  lcd.print("Ready...");
}

void loop() {
  // Read incoming word
  while (Serial.available() > 0) {
    char c = Serial.read();
    if (c == '\n') {
      if (incomingWord == "NEXT") {
        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("Ready...");
      } else {
        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("Word:");
        lcd.setCursor(0, 1);
        lcd.print(incomingWord);
      }
      incomingWord = "";
    } else {
      incomingWord += c;
    }
  }

  // Read distance from ultrasonic sensors
  long leftDist = getDistance(trigLeft, echoLeft);
  long rightDist = getDistance(trigRight, echoRight);

  // Print ultrasonic sensor values to serial monitor
  Serial.print("Left Trigger: ");
  Serial.print(digitalRead(trigLeft));
  Serial.print(", Left Echo: ");
  Serial.println(digitalRead(echoLeft));
  
  Serial.print("Right Trigger: ");
  Serial.print(digitalRead(trigRight));
  Serial.print(", Right Echo: ");
  Serial.println(digitalRead(echoRight));

  bool objectDetected = false;
  int targetServoPos = currentServoPos; // default: no change

  // Check detection
  if (leftDist < 15 && rightDist >= 15) {
    targetServoPos = 30;
    objectDetected = true;
  } else if (rightDist < 15 && leftDist >= 15) {
    targetServoPos = 150;
    objectDetected = true;
  } else {
    targetServoPos = 90;
    objectDetected = false;
  }

  // Move servo only when:
  // 1. Detection status changes (object detected or not)
  // 2. or target position is different
  if (objectDetected != objectDetectedBefore || currentServoPos != targetServoPos) {
    servo.write(targetServoPos);
    currentServoPos = targetServoPos;
    objectDetectedBefore = objectDetected;
    delay(300);  // Allow smooth movement
  }

  delay(50);  // Short delay for loop smoothness
}

long getDistance(int trigPin, int echoPin) {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  long duration = pulseIn(echoPin, HIGH, 30000);  // Timeout after 30ms
  long distance = duration * 0.034 / 2;
  return distance;
}
