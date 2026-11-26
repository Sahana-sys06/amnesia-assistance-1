#include <Wire.h>
#include <WiFi.h>
#include "secrets.h"
#include <Adafruit_GFX.h>
#include <Adafruit_SH110X.h>

// Enter the name and password of the same 2.4 GHz Wi-Fi network
// that your laptop is connected to.

// OLED: SDA -> GPIO 21, SCL -> GPIO 22; button between GPIO 18 and GND.
// Button is active-low and uses the ESP32's internal pull-up.
// Optional alerts: LED (with series resistor) -> GPIO 25; buzzer SIG -> GPIO 26.
constexpr int OLED_WIDTH = 128;
constexpr int OLED_HEIGHT = 64;
constexpr int BUTTON_PIN = 18;
constexpr int LED_PIN = 25;
constexpr int BUZZER_PIN = 26;
constexpr uint8_t OLED_ADDRESS = 0x3C;
constexpr unsigned long DEBOUNCE_MS = 50;
constexpr unsigned long WIFI_RETRY_MS = 10000;

Adafruit_SH1106G display(OLED_WIDTH, OLED_HEIGHT, &Wire, -1);
String personName = "Unknown person";
String personRelationship = "Relationship not set";
String medicationName = "No medicine reminder";
String medicationTime = "";
String statusMessage = "Starting Wi-Fi";
String serialLine = "";
long activeDoseId = 0;
long lastAcknowledgedDoseId = 0;
int lastButtonReading = HIGH;
int stableButtonState = HIGH;
unsigned long lastDebounceTime = 0;
unsigned long statusExpiresAt = 0;
unsigned long lastWifiAttempt = 0;
bool oledReady = false;
bool reminderAlertActive = false;
bool buzzerOn = false;
unsigned long reminderAlertStartedAt = 0;

void stopReminderAlert() {
  noTone(BUZZER_PIN);
  digitalWrite(LED_PIN, LOW);
  reminderAlertActive = false;
  buzzerOn = false;
}

void startReminderAlert() {
  reminderAlertStartedAt = millis();
  reminderAlertActive = true;
  buzzerOn = false;
}

void updateReminderAlert() {
  if (!reminderAlertActive) return;

  const unsigned long elapsed = millis() - reminderAlertStartedAt;
  if (elapsed >= 2400) {
    stopReminderAlert();
    return;
  }

  // Three short beeps and flashes, 800 ms apart.
  const bool shouldBeOn = (elapsed % 800) < 250;
  if (shouldBeOn != buzzerOn) {
    if (shouldBeOn) tone(BUZZER_PIN, 2000);
    else noTone(BUZZER_PIN);
    buzzerOn = shouldBeOn;
  }
  digitalWrite(LED_PIN, shouldBeOn ? HIGH : LOW);
}

String cleanText(String value, int limit = 18) {
  value.replace('|', ' ');
  value.replace('\r', ' ');
  value.replace('\n', ' ');
  value.trim();
  if (value.length() > limit) value = value.substring(0, limit);
  return value;
}

void drawScreen() {
  if (!oledReady) return;

  display.clearDisplay();
  display.setTextColor(SH110X_WHITE);
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.println("MemoryCare");
  display.drawLine(0, 10, 127, 10, SH110X_WHITE);
  display.setCursor(0, 14);
  display.print("Person: ");
  display.println(cleanText(personName, 12));
  display.setCursor(0, 24);
  display.print("Relation: ");
  display.println(cleanText(personRelationship, 10));
  display.setCursor(0, 34);
  display.print("Med: ");
  display.println(cleanText(medicationName, 16));
  display.setCursor(0, 44);
  if (medicationTime.length()) {
    display.print("Scheduled: ");
    display.println(cleanText(medicationTime, 5));
  } else {
    display.println("Reminder time: --:--");
  }
  display.setCursor(0, 55);
  if (statusExpiresAt && millis() < statusExpiresAt) {
    display.println(cleanText(statusMessage, 20));
  } else if (activeDoseId > 0) {
    display.println("Press button to ACK");
  } else if (WiFi.status() == WL_CONNECTED) {
    display.println("Wi-Fi connected");
  } else {
    display.println("Connecting to Wi-Fi");
  }
  display.display();
}

void handleCommand(String line) {
  line.trim();
  if (line.startsWith("PERSON|")) {
    int separator = line.indexOf('|', 7);
    if (separator >= 0) {
      personName = cleanText(line.substring(7, separator), 48);
      personRelationship = cleanText(line.substring(separator + 1), 48);
    } else {
      personName = cleanText(line.substring(7), 48);
      personRelationship = "Relationship not set";
    }
    drawScreen();
    return;
  }
  if (line.startsWith("MED|")) {
    int first = line.indexOf('|');
    int second = line.indexOf('|', first + 1);
    int third = line.indexOf('|', second + 1);
    if (second < 0 || third < 0) return;
    long doseId = line.substring(first + 1, second).toInt();
    if (doseId <= 0) return;
    activeDoseId = doseId;
    medicationName = cleanText(line.substring(second + 1, third), 18);
    medicationTime = cleanText(line.substring(third + 1), 5);
    statusMessage = "Reminder active";
    statusExpiresAt = millis() + 2500;
    startReminderAlert();
    drawScreen();
    return;
  }
  if (line.startsWith("ACK|")) {
    long doseId = line.substring(4).toInt();
    if (doseId > 0 && doseId == activeDoseId) {
      activeDoseId = 0;
      lastAcknowledgedDoseId = doseId;
    }
    statusMessage = "Acknowledged. Thank you.";
    statusExpiresAt = millis() + 6000;
    drawScreen();
    return;
  }
  if (line.startsWith("INFO|")) {
    statusMessage = cleanText(line.substring(5), 20);
    statusExpiresAt = millis() + 5000;
    drawScreen();
  }
}

void connectToWifi() {
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_NAME, WIFI_PASSWORD);
  lastWifiAttempt = millis();
  statusMessage = "Connecting to Wi-Fi";
  statusExpiresAt = millis() + 3000;
  drawScreen();
}

void setup() {
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  pinMode(LED_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  noTone(BUZZER_PIN);
  Serial.begin(115200);
  Serial.setTimeout(30);
  Wire.begin(21, 22);

  oledReady = display.begin(OLED_ADDRESS, true);
  if (!oledReady) {
    // Avoid writing diagnostics to Serial because it carries the existing
    // dashboard-to-ESP32 command protocol.
    return;
  }

  drawScreen();
  connectToWifi();
}

void loop() {
  updateReminderAlert();

  while (Serial.available()) {
    char incoming = static_cast<char>(Serial.read());
    if (incoming == '\n') {
      handleCommand(serialLine);
      serialLine = "";
    } else if (incoming != '\r' && serialLine.length() < 160) {
      serialLine += incoming;
    }
  }

  if (WiFi.status() != WL_CONNECTED && millis() - lastWifiAttempt >= WIFI_RETRY_MS) {
    connectToWifi();
  }

  int reading = digitalRead(BUTTON_PIN);
  if (reading != lastButtonReading) lastDebounceTime = millis();
  if (millis() - lastDebounceTime > DEBOUNCE_MS && reading != stableButtonState) {
    stableButtonState = reading;
    if (stableButtonState == LOW) {
      stopReminderAlert();
      if (activeDoseId > 0 && activeDoseId != lastAcknowledgedDoseId) {
        Serial.print("ACKNOWLEDGED|");
        Serial.println(activeDoseId);
        statusMessage = "Sent acknowledgment";
      } else {
        Serial.println("ACKNOWLEDGED|0");
        statusMessage = "No active dose to acknowledge";
      }
      statusExpiresAt = millis() + 3000;
      drawScreen();
    }
  }
  lastButtonReading = reading;
}

