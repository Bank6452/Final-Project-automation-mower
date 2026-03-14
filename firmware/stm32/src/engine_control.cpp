#include "engine_control.h"

Servo engineServo;
Servo relayRC;

bool isStarting = false;
uint32_t startTimer = 0;

void initEngineSystem() {
    engineServo.attach(PIN_THROTTLE_SERVO);
    relayRC.attach(PIN_RELAY_SYSTEM);
    
    // เริ่มต้นให้ดับเครื่องทันทีเพื่อความปลอดภัย
    powerOff(); 
    engineServo.writeMicroseconds(1100); 
}

void setThrottle(int percent) {
    percent = constrain(percent, 0, 100);
    int pwm = map(percent, 0, 100, 1100, 1900);
    engineServo.writeMicroseconds(pwm);
}

void powerOn() {
    // ระบบไฟทำงาน = Relay ต้อง OFF (เพื่อให้เครื่องไม่ถูกตัดไฟ)
    // ใช้ค่า 1500us ตามที่คุณระบุไว้สำหรับสภาวะปกติ
    relayRC.writeMicroseconds(1500); 
}

void powerOff() {
    // สั่งดับเครื่อง = Relay ON (หน้า NO ต่อวงจรเพื่อตัดไฟ/ลงกราวด์)
    // ใช้ค่า 1000us เพื่อให้ CH1 ทำงาน (ON)
    relayRC.writeMicroseconds(1000);
    isStarting = false;
}

void startEngine() {
    // สั่งสตาร์ท = CH2 ON (ระบบไฟ CH1 ต้องไม่ตัดเครื่องด้วย)
    relayRC.writeMicroseconds(2000);
    isStarting = true;
    startTimer = millis();
}

void updateStarterStatus() {
    if (!isStarting) return;

    // หยุดสตาร์ทหลัง 10 วินาที แล้วสั่ง Power On ต่อ
    if (millis() - startTimer > 10000) {
        powerOn();
        isStarting = false;
    }
}