#include "HX711.h"
#include <Wire.h>
#include <hd44780.h>
#include <hd44780ioClass/hd44780_I2Cexp.h>

// HX711 scale
#define LOADCELL_DOUT_PIN 6
#define LOADCELL_SCK_PIN 7

// Buttons
#define START_BUTTON_PIN 4
#define TARE_BUTTON_PIN 5

// States
#define STATE_IDLE 0
#define STATE_TARE 1
#define STATE_READING 2

// Scale
HX711 scale;

// declare lcd object: auto locate & auto config expander chip
hd44780_I2Cexp lcd;

// LCD geometry
const int LCD_COLS = 16;
const int LCD_ROWS = 2;

float reading = 0.0;
float lastreading = 0.0;

int currentState = STATE_IDLE;

unsigned long startTimer;

void setup() {
  // Initialize the buttons
  pinMode(START_BUTTON_PIN, INPUT_PULLUP);
  pinMode(TARE_BUTTON_PIN, INPUT_PULLUP);

  // Initialize the LCD
  lcd.begin(LCD_COLS, LCD_ROWS);

  Serial.begin(115200);
  Serial.println("HX711 Demo");

  Serial.println("Initializing the scale");
  lcd.print("Initializing...");

  // Initialize library with data output pin, clock input pin and gain factor.
  // Channel selection is made by passing the appropriate gain:
  // - With a gain factor of 64 or 128, channel A is selected
  // - With a gain factor of 32, channel B is selected
  // By omitting the gain factor parameter, the library
  // default "128" (Channel A) is used here.
  scale.begin(LOADCELL_DOUT_PIN, LOADCELL_SCK_PIN);

  Serial.println("Before setting up the scale:");

  // print a raw reading from the ADC
  Serial.print("read: \t\t");
  Serial.println(scale.read());

  // print the average of 20 readings from the ADC
  Serial.print("read average: \t\t");
  Serial.println(scale.read_average(20));

  // print the average of 5 readings from the ADC minus the tare weight (not set yet)
  Serial.print("get value: \t\t");
  Serial.println(scale.get_value(5));

  // print the average of 5 readings from the ADC minus tare weight (not set) divided
  // by the SCALE parameter (not set yet)
  Serial.print("get units: \t\t");
  Serial.println(scale.get_units(5), 1);

  // this value is obtained by calibrating the scale with known weights; see the README for details
  scale.set_scale(1103.f);

  // reset the scale to 0
  scale.tare();

  Serial.println("After setting up the scale:");

  // print a raw reading from the ADC
  Serial.print("read: \t\t");
  Serial.println(scale.read());

  // print the average of 20 readings from the ADC
  Serial.print("read average: \t\t");
  Serial.println(scale.read_average(20));

  // print the average of 5 readings from the ADC minus the tare weight, set with tare()
  Serial.print("get value: \t\t");
  Serial.println(scale.get_value(5));

  // print the average of 5 readings from the ADC minus tare weight, divided
  // by the SCALE parameter set with set_scale
  Serial.print("get units: \t\t");
  Serial.println(scale.get_units(5), 1);

  Serial.println("Ready.");
  lcd.clear();
  lcd.print("Ready.");
  // put the ADC in sleep mode
  scale.power_down();
}

void loop() {
  switch (currentState) {
    case STATE_IDLE:
      if (digitalRead(START_BUTTON_PIN) == LOW) {
        currentState = STATE_READING;
        start();
      }
      if (digitalRead(TARE_BUTTON_PIN) == LOW) {
        currentState = STATE_TARE;
        tare();
      }
      break;
    case STATE_READING:
      read();
      if (digitalRead(START_BUTTON_PIN) == LOW) {
        currentState = STATE_IDLE;
        stop();
      }
      break;
  }
}

void tare() {
  Serial.println("Taring scale...");

  lcd.clear();
  lcd.print("Taring scale...");

  scale.power_up();
  scale.tare();
  delay(500);
  scale.power_down();

  currentState = STATE_IDLE;

  Serial.println("Scale tared.");

  lcd.clear();
  lcd.print("Scale tared.");

  delay(1000);

  lcd.clear();
  lcd.print("Ready.");
}

void start() {
  Serial.println("Starting...");

  lcd.clear();
  lcd.print("Starting...");

  scale.power_up();
  delay(500);
  startTimer = millis();

  Serial.println("Started.");
  Serial.println("BEGIN DATA");

  lcd.clear();
  lcd.print("Reading data");
}

void stop() {
  Serial.println("END DATA");
  Serial.println("Stopping...");

  lcd.clear();
  lcd.print("Stopping...");

  scale.power_down();
  delay(500);

  Serial.println("Stopped.");

  lcd.clear();
  lcd.print("Ready.");
}

void read() {
  Serial.print(millis() - startTimer);
  Serial.print("|");
  Serial.println(scale.get_units(), 2);
}
