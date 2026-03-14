#ifndef ENGINE_CONTROL_H
#define ENGINE_CONTROL_H

#include <Arduino.h>
#include <Servo.h>

#define PIN_THROTTLE_SERVO PB3
#define PIN_RELAY_SYSTEM    PB15

void initEngineSystem();
void setThrottle(int percent); 
void powerOn();   
void powerOff();  
void startEngine(); 
void updateStarterStatus(); 

#endif