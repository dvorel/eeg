#define SAMPLE_RATE 500
#define BAUD_RATE 500000


const byte inPins[] = 
{
  A0,
  A1,
  A2,
  A3,
  A4,
  A5,
  A6,
  A7,
  A8,
  A9,
  A10,
  A11,
  A12,
  A13,
  A14,
  A15
};


void setup() {
	Serial.begin(BAUD_RATE);
}

void loop() {
	// Calculate elapsed time
	static unsigned long past = 0;
	unsigned long present = micros();
	unsigned long interval = present - past;
	past = present;

	// Run timer
	static long timer = 0;
	timer -= interval;

	// Sample
	if(timer < 0){
		timer += 1000000 / SAMPLE_RATE;

    for(int i=0;i<15;i++){
      Serial.print(analogRead(inPins[i]));
      Serial.print(",");
    }
    Serial.println(analogRead(inPins[15]));
	}
}
