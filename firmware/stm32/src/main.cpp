#include <Arduino.h>
#include "motor_control.h"
#include "Encoder.h"
#include "engine_control.h" // สำหรับระบบสตาร์ทเครื่องยนต์

String inputBuffer = "";
bool emergencyMode = false;
uint32_t last_send = 0;
uint32_t last_cmd_received = 0;
const uint32_t HEARTBEAT_TIMEOUT = 1000; 

void processCommand(String cmd) {
    cmd.trim();
    if (cmd.length() == 0) return;
    int first = cmd.indexOf(',');
    int second = cmd.indexOf(',', first + 1);
    int third = cmd.indexOf(',', second + 1);
    if (first == -1) return;
    String header = cmd.substring(0, first);
    header.toUpperCase();

    if (header == "E" && second != -1) {
        int state = cmd.substring(first + 1, second).toInt();
        int chk = cmd.substring(second + 1).toInt();
        if ((state + 69) == chk) {
            emergencyMode = (state == 1);
            if (emergencyMode) stop();
            last_cmd_received = millis();
        }
    }
    if (header == "C" && third != -1) {
        float vL = cmd.substring(first + 1, second).toFloat();
        float vR = cmd.substring(second + 1, third).toFloat();
        int receivedChk = cmd.substring(third + 1).toInt();
        // Checksum: int(vL*100) + int(vR*100) ต้องตรงกับฝั่ง Python
        int calcChk = (int)(vL * 100) + (int)(vR * 100);
        if (calcChk == receivedChk) {
            if (emergencyMode) { stop(); return; }
            driveMotors(vL, vR);
            last_cmd_received = millis();
        }
    }
}

void setup() {
    __HAL_RCC_AFIO_CLK_ENABLE(); 
    __HAL_AFIO_REMAP_SWJ_NOJTAG(); 

    pinMode(PB14, INPUT_PULLUP);
    pinMode(PC14, OUTPUT);
    pinMode(PC13, OUTPUT);

    Serial1.begin(115200); 

    initMotors();       // เริ่มระบบมอเตอร์ล้อ
    setupEncoders();    // เริ่มระบบ Encoder
    initEngineSystem(); // เริ่มระบบสตาร์ทเครื่องยนต์
    
    last_cmd_received = millis();
}

void loop() {
    // 1. รับคำสั่ง Serial
    while (Serial1.available()) {
        char c = Serial1.read();
        if (c == '\n' || c == '\r') {
            if (inputBuffer.length() > 0) {
                processCommand(inputBuffer);
                inputBuffer = "";
            }
        } else {
            inputBuffer += c;
            if (inputBuffer.length() > 50) inputBuffer = "";
        }
    }

    // 2. Safety Heartbeat
    if (!emergencyMode && (millis() - last_cmd_received > HEARTBEAT_TIMEOUT)) {
        stop();
    }

    // 3. ระบบจัดการเครื่องยนต์ (เช็คการสั่นสะเทือนเพื่อหยุดสตาร์ท)
    updateStarterStatus();

    // 4. ส่งข้อมูลกลับ Pi ทุก 100ms
    if (millis() - last_send >= 100) { 
        float dt = (millis() - last_send) / 1000.0;
        last_send = millis();

        // ส่งข้อมูล Encoder
        float vL, vR; long pL, pR;
        getEncoderData(vL, vR, pL, pR, dt);
        Serial1.print("D,"); Serial1.print(vL, 2); Serial1.print(",");
        Serial1.print(vR, 2); Serial1.print(","); Serial1.print(pL); Serial1.print(",");
        Serial1.println(pR);
    }

    bool isManual = (digitalRead(PB14) == LOW);
    digitalWrite(PC14, isManual ? LOW : HIGH);
    digitalWrite(PC13, isManual ? HIGH : LOW);
}