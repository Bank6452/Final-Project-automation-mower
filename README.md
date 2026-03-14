# 🚜 Autonomous Lawn Mower System (ROS 2 & STM32)

**โปรเจคจบการศึกษา (Senior Project) - ระบบรถตัดหญ้าอัตโนมัติประสิทธิภาพสูง** เป็นการพัฒนาระบบควบคุมหุ่นยนต์แบบ Differential Drive ที่ผสานการทำงานระหว่าง High-level Control (ROS 2) และ Low-level Control (STM32) เพื่อการตัดหญ้าที่แม่นยำและปลอดภัย

---

## 📝 รายละเอียดโปรเจค (Description)
ระบบรถตัดหญ้าอัตโนมัติควบคุมด้วย **ROS 2 Humble (Raspberry Pi 5)** และ **STM32** ใช้เทคนิค **Sensor Fusion** ร่วมกับเซนเซอร์ (RTK GPS, LiDAR, IMU, Encoder, Ultrasonic) เพื่อให้สามารถทำ **SLAM** และ **Navigation** ได้แม่นยำระดับเซนติเมตร พร้อมระบบความปลอดภัย **Heartbeat Safety** และฟังก์ชันสตาร์ทเครื่องยนต์อัตโนมัติ

---

## 🚀 ฟีเจอร์หลัก (Key Features)
* **Sensor Fusion (EKF):** รวมข้อมูลจาก RTK GPS และ Odometry เพื่อพิกัดที่แม่นยำที่สุด
* **SLAM & Navigation:** สร้างแผนที่สภาพแวดล้อมและเดินตาม Waypoints ที่กำหนดอัตโนมัติ
* **Safety Layer:** ระบบตรวจสอบสถานะการเชื่อมต่อ (Heartbeat) และตรวจจับสิ่งกีดขวางด้วย LiDAR และ Ultrasonic
* **Engine Control:** ระบบสตาร์ท/ดับเครื่องยนต์อัตโนมัติ และการปรับเร่งเครื่องผ่าน Software

---

## 🛠️ รายละเอียดฮาร์ดแวร์ (Hardware Components)
* **Main Controller:** Raspberry Pi 5 (Processing ROS 2 Humble)
* **Microcontroller:** STM32F103C8T6 (Bluepill)
* **Positioning:** RTK GPS System
* **Vision/Mapping:** RPLiDAR
* **Orientation:** IMU MPU6050 (with Complementary Filter)
* **Distance Sensors:** Ultrasonic HC-SR04
* **Feedback:** Hall Effect Encoders

---

## 📂 โครงสร้างซอร์สโค้ด (Source Code Structure)
* `stm32_firmware/` : โค้ดควบคุมมอเตอร์, อ่าน Encoder และ IMU พัฒนาด้วย PlatformIO
* `ros2_ws/` : Workspace ของ ROS 2 ประกอบด้วย Node สำหรับ Navigation, SLAM และ Sensor Fusion
* `engine_control/` : ระบบสตาร์ทเครื่องยนต์และ Throttle Control

---

## 👥 สมาชิกผู้จัดทำ (Team Members)
* **นายพงศธร รอดพิพัฒน์** (รหัสนักศึกษา: 6703016410080)
* **นายทินภัทร จิตต์บุญ** (รหัสนักศึกษา: 6703016410039)
* **นายวัชรากร เพกรา** (รหัสนักศึกษา: 6703016410179)

**อาจารย์ที่ปรึกษา:**
* **ผศ.ดร.สุพจน์ แก้วกรณ์**

---

![รูปcadเปรียบเทียบกับรถจริง](images/รูปcadเปรียบเทียบกับรถจริง.jpg)

© 2026 Autonomous Mower Project - All Rights Reserved
