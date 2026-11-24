// UNODE bench check for an ESP-12E (ESP8266) devkit + SW-420 vibration module
// Board: "NodeMCU 1.0 (ESP-12E Module)"   Serial Monitor: 115200 baud
// Wiring (optional for the SW-420 part): VCC->3V3, GND->GND, DO->D7 (GPIO13)

#include <ESP8266WiFi.h>

const int VIB_PIN = D7;          // SW-420 DO
unsigned long lastReport = 0;
unsigned long pulses = 0;
int lastState = -1;

void setup() {
  Serial.begin(115200);
  delay(500);
  pinMode(LED_BUILTIN, OUTPUT);  // on-board LED, ON when the pin is LOW
  pinMode(VIB_PIN, INPUT);

  Serial.println();
  Serial.println("=== ESP8266 check ===");
  Serial.printf("Chip ID:          %08X\n", ESP.getChipId());
  Serial.printf("CPU frequency:    %u MHz\n", ESP.getCpuFreqMHz());
  Serial.printf("Flash real size:  %u bytes\n", ESP.getFlashChipRealSize());
  Serial.printf("Flash IDE size:   %u bytes\n", ESP.getFlashChipSize());
  Serial.printf("Supply (approx):  %.2f V  (needs ADC_MODE, may read 0 here)\n", ESP.getVcc() / 1000.0);
  Serial.printf("Reset reason:     %s\n", ESP.getResetReason().c_str());

  // Wi-Fi scan: lists networks and signal strength (RSSI). -70 dBm or stronger is good.
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  delay(100);
  Serial.println("Scanning Wi-Fi...");
  int n = WiFi.scanNetworks();
  for (int i = 0; i < n; i++) {
    Serial.printf("  %-32s  %4d dBm  ch %2d\n",
                  WiFi.SSID(i).c_str(), WiFi.RSSI(i), WiFi.channel(i));
  }
  if (n == 0) Serial.println("  no networks found");
  Serial.println("=== SW-420 test: tap the table near the sensor ===");
}

void loop() {
  int s = digitalRead(VIB_PIN);
  if (s != lastState) {
    if (lastState != -1 && s == HIGH) pulses++;   // count rising edges
    lastState = s;
  }
  digitalWrite(LED_BUILTIN, s == HIGH ? LOW : HIGH);  // LED on while DO is HIGH

  if (millis() - lastReport >= 1000) {
    lastReport = millis();
    Serial.printf("SW-420 DO=%d  pulses in last second=%lu\n", s, pulses);
    pulses = 0;
  }
}
