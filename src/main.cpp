#include <WiFi.h>
#include <WiFiUdp.h>
#include <Wire.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>

#define NUM_MPUS 3
const int MPU_SEL_PIN[NUM_MPUS] = {T9, T8, T7};
Adafruit_MPU6050 mpu[NUM_MPUS];

// WiFi credentials
const char *ssid = "ESP32_AP";
const char *password = "12345678";

// UDP parameters
WiFiUDP udp;
const int udpPort = 12345;
const char *udpAddress = "192.168.4.2"; // IP of the connected computer

// Timer for sending data at 10 Hz
unsigned long previousMillis = 0;
const long interval = 100; // 10 Hz

void selectMPU(int sel) {
  for (int i = 0; i < NUM_MPUS; i++) {
    digitalWrite(MPU_SEL_PIN[i], i != sel);
  }
}

void setup() {
  Serial.begin(115200);
  Wire.begin();
  WiFi.softAP(ssid, password);
  udp.begin(udpPort);

  for (int i = 0; i < NUM_MPUS; i++) {
    pinMode(MPU_SEL_PIN[i], OUTPUT);
    digitalWrite(MPU_SEL_PIN[i], HIGH);
  }

  for (int i = 0; i < NUM_MPUS; i++) {
    selectMPU(i);
    if (!mpu[i].begin()) {
      Serial.print("Failed to find MPU6050 #");
      Serial.println(i);
      continue;
    }
    Serial.print("Found MPU6050 #");
    Serial.println(i);
    mpu[i].setAccelerometerRange(MPU6050_RANGE_8_G);
    mpu[i].setGyroRange(MPU6050_RANGE_500_DEG);
    mpu[i].setFilterBandwidth(MPU6050_BAND_5_HZ);
  }

  delay(100);
}

void loop() {
  unsigned long currentMillis = millis();
  if (currentMillis - previousMillis >= interval) {
    previousMillis = currentMillis;

    String message = "";

    for (int i = 0; i < NUM_MPUS; i++) {
      selectMPU(i);

      sensors_event_t a, g, t;
      if (mpu[i].getEvent(&a, &g, &t)) {
        message += String(a.acceleration.x, 2) + "," + String(a.acceleration.y, 2) + "," + String(a.acceleration.z, 2);
      } else {
        message += "0,0,0"; // Error case
      }

      if (i < NUM_MPUS - 1) {
        message += ",";
      }
    }

    // Send message via UDP
    udp.beginPacket(udpAddress, udpPort);
    udp.print(message);
    udp.endPacket();
  }
}
