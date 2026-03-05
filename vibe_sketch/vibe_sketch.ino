#include <ESP8266WiFi.h>
#include <Wire.h>
#include <DHT.h> // This library needs to be installed in the Arduino IDE. 
                 // You can do this by going to Sketch > Include Library > Manage Libraries and searching for "DHT"

#define DHT_PIN D1  // DHT11 sensor pin
#define RELAY_PIN D2  // Relay pin for water pump
#define LIGHT_PIN D5  // Pin for LED light
#define LIGHT_SENSOR_PIN A0  // Analog pin for light sensor
#define WATER_THRESHOLD 40  // Watering threshold (40% humidity)
#define LIGHT_THRESHOLD 500  // Light threshold (500 lux)

DHT dht(DHT_PIN, DHT11);

void setup() {
  Serial.begin(115200);
  dht.begin();
  pinMode(RELAY_PIN, OUTPUT);
  pinMode(LIGHT_PIN, OUTPUT);
  pinMode(LIGHT_SENSOR_PIN, INPUT);  // Set the light sensor pin as input
}

void loop() {
  float humidity = dht.readHumidity();
  float temperature = dht.readTemperature();
  int lightLevel = analogRead(LIGHT_SENSOR_PIN);  // Assuming an analog light sensor is connected to A0

  Serial.print("Humidity: ");
  Serial.print(humidity);
  Serial.println("%");
  Serial.print("Temperature: ");
  Serial.print(temperature);
  Serial.println("C");
  Serial.print("Light Level: ");
  Serial.print(lightLevel);
  Serial.println(" lux");

  if (humidity < WATER_THRESHOLD) {
    digitalWrite(RELAY_PIN, HIGH);  // Turn on water pump
    delay(10000);  // Water for 10 seconds
    digitalWrite(RELAY_PIN, LOW);  // Turn off water pump
  }

  if (lightLevel < LIGHT_THRESHOLD) {
    digitalWrite(LIGHT_PIN, HIGH);  // Turn on LED light
  } else {
    digitalWrite(LIGHT_PIN, LOW);  // Turn off LED light
  }

  delay(1000);  // Update every second
}