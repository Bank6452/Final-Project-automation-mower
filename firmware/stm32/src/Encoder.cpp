#include "Encoder.h"
#include <Arduino.h>

// กำหนดพิน (PA0, PA1 ล้อซ้าย | PA4, PA5 ล้อขวา)
const int pinAL = PA0; const int pinBL = PA1;
const int pinAR = PA4; const int pinBR = PA5;

// ตัวแปรเก็บค่า Pulse (volatile สำหรับ Interrupt)
volatile long pulseL = 0;
volatile long pulseR = 0;

// ตัวแปรช่วยเช็คสถานะเพื่อป้องกันการนับทิศทางผิด (State Tracking)
volatile bool lastAL = false;
volatile bool lastBL = false;
volatile bool lastAR = false;
volatile bool lastBR = false;

// ตัวแปรสำหรับคำนวณความเร็ว
static long prevPulseL = 0;
static long prevPulseR = 0;
static float filtered_vL = 0;
static float filtered_vR = 0;

// ค่า Alpha สำหรับ Low-Pass Filter (0.1 - 0.3) 
// ยิ่งน้อยยิ่งนิ่ง แต่จะตอบสนองช้าลงนิดหน่อย
const float alpha = 0.5; 

// --- Interrupt Service Routines (ISRs) แบบ Robust Logic ---

void handleEncoderL() {
    bool A = digitalRead(pinAL);
    bool B = digitalRead(pinBL);
    
    // เช็คว่าขาไหนเปลี่ยน และทิศทางเป็นอย่างไร
    if (A != lastAL) { // ขา A เปลี่ยน
        if (A == B) pulseL++; else pulseL--;
    } else if (B != lastBL) { // ขา B เปลี่ยน
        if (A == B) pulseL--; else pulseL++;
    }
    
    lastAL = A;
    lastBL = B;
}

void handleEncoderR() {
    bool A = digitalRead(pinAR);
    bool B = digitalRead(pinBR);
    
    if (A != lastAR) { // ขา A เปลี่ยน
        if (A == B) pulseR--; else pulseR++; // ถ้าเดินหน้าแล้วเลขติดลบ ให้สลับ ++ กับ -- ตรงนี้
    } else if (B != lastBR) { // ขา B เปลี่ยน
        if (A == B) pulseR++; else pulseR--; // และสลับตรงนี้ด้วย
    }
    
    lastAR = A;
    lastBR = B;
}

// --- ฟังก์ชัน Setup ---
void setupEncoders() {
    pinMode(pinAL, INPUT_PULLUP);
    pinMode(pinBL, INPUT_PULLUP);
    pinMode(pinAR, INPUT_PULLUP);
    pinMode(pinBR, INPUT_PULLUP);

    // อ่านค่าเริ่มต้น
    lastAL = digitalRead(pinAL);
    lastBL = digitalRead(pinBL);
    lastAR = digitalRead(pinAR);
    lastBR = digitalRead(pinBR);

    // ใช้ CHANGE เพื่อความละเอียดสูงสุด (4x Decoding)
    attachInterrupt(digitalPinToInterrupt(pinAL), handleEncoderL, CHANGE);
    attachInterrupt(digitalPinToInterrupt(pinBL), handleEncoderL, CHANGE);
    
    attachInterrupt(digitalPinToInterrupt(pinAR), handleEncoderR, CHANGE);
    attachInterrupt(digitalPinToInterrupt(pinBR), handleEncoderR, CHANGE);
}

// --- ฟังก์ชันดึงข้อมูลไปใช้ ---
void getEncoderData(float &vL, float &vR, long &pL, long &pR, float dt) {
    // 1. Atomic Access: ป้องกัน Interrupt มาแทรกขณะอ่านค่า long
    noInterrupts();
    long currentL = pulseL;
    long currentR = pulseR;
    interrupts();

    // 2. คำนวณความเร็ว
    if (dt > 0) {
        // ความเร็วดิบ (Raw Ticks per Second)
        float raw_vL = (float)(currentL - prevPulseL) / dt;
        float raw_vR = (float)(currentR - prevPulseR) / dt;

        // 3. Low-Pass Filter: กรองเลขกระโดด
        filtered_vL = (alpha * raw_vL) + ((1.0 - alpha) * filtered_vL);
        filtered_vR = (alpha * raw_vR) + ((1.0 - alpha) * filtered_vR);

        // ปัดเป็น 0 เมื่อหยุดนิ่ง
        if (abs(filtered_vL) < 0.5) filtered_vL = 0;
        if (abs(filtered_vR) < 0.5) filtered_vR = 0;

        vL = filtered_vL;
        vR = filtered_vR;
    } else {
        vL = 0; vR = 0;
    }
    
    // 4. ส่งค่ากลับและอัปเดตค่าเก่า
    pL = currentL;
    pR = currentR;
    prevPulseL = currentL;
    prevPulseR = currentR;
}