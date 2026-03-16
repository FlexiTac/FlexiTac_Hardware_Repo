#define BAUD_RATE                 2000000
#define ROW_COUNT                 16
#define COLUMN_COUNT              32

#define PIN_ADC_INPUT             A0
#define PIN_SHIFT_REGISTER_DATA   2
#define PIN_SHIFT_REGISTER_CLOCK  3
#define PIN_MUX_CHANNEL_0         4  
#define PIN_MUX_CHANNEL_1         5
#define PIN_MUX_CHANNEL_2         6
#define PIN_MUX_CHANNEL_3         7
#define PIN_MUX_INHIBIT_0         8 
#define PIN_MUX_INHIBIT_1         9

#define SET_SR_DATA_HIGH()        PORTD|=B00000100
#define SET_SR_DATA_LOW()         PORTD&=~B00000100
#define SET_SR_CLK_HIGH()         PORTD|=B00001000
#define SET_SR_CLK_LOW()          PORTD&=~B00001000


#define ROWS_PER_MUX              16
#define MUX_COUNT                 1
#define CHANNEL_PINS_PER_MUX      4

#ifndef cbi
#define cbi(sfr, bit) (_SFR_BYTE(sfr) &= ~_BV(bit))
#endif
#ifndef sbi
#define sbi(sfr, bit) (_SFR_BYTE(sfr) |= _BV(bit))
#endif

int current_enabled_mux = MUX_COUNT - 1;  //init to number of last mux so enabled mux increments to first mux on first scan.

void setup()
{
  Serial.begin(BAUD_RATE);
  pinMode(PIN_ADC_INPUT, INPUT);
  pinMode(PIN_SHIFT_REGISTER_DATA, OUTPUT);
  pinMode(PIN_SHIFT_REGISTER_CLOCK, OUTPUT);
  pinMode(PIN_MUX_CHANNEL_0, OUTPUT);
  pinMode(PIN_MUX_CHANNEL_1, OUTPUT);
  pinMode(PIN_MUX_CHANNEL_2, OUTPUT);
  pinMode(PIN_MUX_CHANNEL_3, OUTPUT);
  pinMode(PIN_MUX_INHIBIT_0, OUTPUT);
  pinMode(PIN_MUX_INHIBIT_1, OUTPUT);

  sbi(ADCSRA,ADPS2);  //set ADC prescaler to CLK/16
  cbi(ADCSRA,ADPS1);
  cbi(ADCSRA,ADPS0);
}



void loop()
{
  // Optional start-of-frame marker (for resync)
  Serial.write(0xAA);
  Serial.write(0x55);

  for (int i = 0; i < ROW_COUNT; i++)
  {
    setRow(i);
    shiftColumn(true);
    shiftColumn(false);

    for (int j = 0; j < COLUMN_COUNT; j++)
    {
      int raw_reading = analogRead(PIN_ADC_INPUT);
      // 10-bit (0–1023) -> 8-bit (0–255)
      byte send_reading = (byte)(raw_reading >> 2);

      Serial.write(send_reading);   // <--- binary, 1 byte per sensor
      shiftColumn(false);
    }
  }

  // No Serial.println(), no text formatting.
}


void setRow(int row_number)
{
  if((row_number % ROWS_PER_MUX) == 0) 
  {
    digitalWrite(PIN_MUX_INHIBIT_0 + current_enabled_mux, HIGH);  
    current_enabled_mux ++;
    if(current_enabled_mux >= MUX_COUNT)
    {
      current_enabled_mux = 0;
    }
    digitalWrite(PIN_MUX_INHIBIT_0 + current_enabled_mux, LOW); 
  }
  for(int i = 0; i < CHANNEL_PINS_PER_MUX; i ++)
  {
    if(bitRead(row_number, i))
    {
      digitalWrite(PIN_MUX_CHANNEL_0 + i, HIGH);
    }
    else
    {
      digitalWrite(PIN_MUX_CHANNEL_0 + i, LOW);
    }
  }
}


void shiftColumn(boolean is_first)
{
  if(is_first)
  {
    SET_SR_DATA_HIGH();
  }
  SET_SR_CLK_HIGH();
  SET_SR_CLK_LOW();
  if(is_first)
  {
    SET_SR_DATA_LOW();
  }
}

// void printFixed(byte value)
// {
//   Serial.print(value);
// }

