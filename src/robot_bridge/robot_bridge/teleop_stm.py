import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import Int8, Float64, String
from nav_msgs.msg import Odometry
import serial
import threading
import time

class TeleopSTMNode(Node):
    def __init__(self):
        super().__init__('teleop_stm')

        # พารามิเตอร์ของพอร์ต (เผื่อไว้ในกรณีที่หา Auto ไม่เจอ)
        self.declare_parameter('port', '/dev/ttyUSB0')
        self.declare_parameter('baudrate', 115200)
        self.declare_parameter('max_speed_ms', 1.25) # ⚠️ TODO: วัดจริงแล้วใส่ค่า max speed (m/s)

        self.baudrate = self.get_parameter('baudrate').value
        self.max_speed_ms = self.get_parameter('max_speed_ms').value

        # ใช้ค่า Paremater โดยตรง เนื่องจากมีการใช้ udev rules ล็อคพอร์ต /dev/stm32 แล้ว
        self.port = self.get_parameter('port').value
        self.get_logger().info(f"Using fixed STM32 port: {self.port}")

        # Publishers ของ Sensor กลับไปให้ ROS2
        # IMU: ใช้ RealSense driver โดยตรง ไม่ต้อง publish ที่นี่
        self.pub_odom = self.create_publisher(Odometry, 'odom_raw', 10)

        # Publishers แยกล้อซ้าย-ขวา (สำหรับ Calibrate และเทียบกับ IMU)
        self.pub_enc_left_vel = self.create_publisher(Float64, 'encoder/left_velocity', 10)
        self.pub_enc_right_vel = self.create_publisher(Float64, 'encoder/right_velocity', 10)
        self.pub_enc_left_pos = self.create_publisher(Float64, 'encoder/left_position', 10)
        self.pub_enc_right_pos = self.create_publisher(Float64, 'encoder/right_position', 10)

        # Diagnostic Mirror Topics (สำหรับการส่องโปรโตคอล)
        self.pub_serial_tx = self.create_publisher(String, 'serial/raw_tx', 10)
        self.pub_serial_rx = self.create_publisher(String, 'serial/raw_rx', 10)

        # เชื่อมต่อ Serial ไปยัง STM32
        try:
            self.serial_conn = serial.Serial(self.port, self.baudrate, timeout=0.05)
            self.get_logger().info(f"Successfully connected to STM32 on {self.port}")
            
            # เปิดเธรดอ่านข้อมูลที่ STM ส่งกลับมา
            self.read_thread = threading.Thread(target=self.read_serial_data)
            self.read_thread.daemon = True
            self.read_thread.start()
            
        except serial.SerialException as e:
            self.get_logger().error(f"Failed to connect to STM32 on {self.port}: {e}")
            self.serial_conn = None


        self.sub_cmd_vel = self.create_subscription(Twist, 'cmd_vel', self.cmd_vel_callback, 10)
        self.sub_emergency = self.create_subscription(Int8, 'emergency_stop', self.emergency_callback, 10)

        # รับข้อมูล U ดิบจาก Arduino Reader เพื่อส่งต่อให้ STM32
        self.sub_ultrasonic_raw = self.create_subscription(String, 'ultrasonic_raw', self.ultra_raw_callback, 10)

        # Timer ส่งคำสั่งซ้ำๆ (Heartbeat) ที่ 10Hz (0.1 วิ) เหมือนใน main_control.py
        self.timer = self.create_timer(0.1, self.heartbeat_loop)
    
        self.current_vL = 0.0  # m/s ล้อซ้าย
        self.current_vR = 0.0  # m/s ล้อขวา
        self.last_cmd_time = self.get_clock().now()

        # เก็บสถานะพิกัดสะสมของ Odom (X, Y, Theta)
        self.odom_x = 0.0
        self.odom_y = 0.0
        self.odom_th = 0.0
        self.last_odom_time = self.get_clock().now()

        # Safety: ดักหมุนเกิน 1.5 รอบ (540°)
        self.rotation_accumulator = 0.0  # สะสมมุมหมุน (rad)
        self.ROTATION_LIMIT = 3.0 * 3.14159  # 1.5 รอบ = 540° = 3π rad
        self.rotation_safety_triggered = False
        self.pub_cmd_vel_override = self.create_publisher(Twist, 'cmd_vel', 10)
        


    def cmd_vel_callback(self, msg):
        v_linear = msg.linear.x
        v_angular = msg.angular.z

        # Differential Drive: แปลง linear.x / angular.z → vL / vR (m/s)
        track_width = 0.5  # เมตร (ต้องตรงกับหุ่นจริง)
        vL = v_linear - (v_angular * track_width / 2.0)
        vR = v_linear + (v_angular * track_width / 2.0)

        # Clamp ไม่ให้เกิน max speed
        self.current_vL = max(-self.max_speed_ms, min(self.max_speed_ms, vL))
        self.current_vR = max(-self.max_speed_ms, min(self.max_speed_ms, vR))
        self.last_cmd_time = self.get_clock().now()

    def ultra_raw_callback(self, msg):
        # ส่งข้อความ U,x,y,z\n ตรงๆ ไปยัง STM32 เลย
        self.send_serial(msg.data)

    def emergency_callback(self, msg):
        state = msg.data # 0 = Normal, 1 = Emergency
        if state in [0, 1]:
            # STM32 ต้องการ Checksum: state + 69
            chk = state + 69  
            cmd_str = f"E,{state},{chk}\n"
            self.send_serial(cmd_str)
            self.get_logger().warn(f"Emergency command sent: {state}")
            
            if state == 1:  # Emergency Stop
                # หยุดรถทันที + รีเซ็ต Safety
                self.current_vL = 0.0
                self.current_vR = 0.0
                self.rotation_accumulator = 0.0
                self.rotation_safety_triggered = False
                # ส่ง cmd_vel = 0 ให้ Nav2 รู้ว่าต้องหยุด
                stop_msg = Twist()
                self.pub_cmd_vel_override.publish(stop_msg)
                self.get_logger().warn('🛑 Emergency: หยุดรถ + ยกเลิกคำสั่ง Nav2')


    def heartbeat_loop(self):
        # ถ้าไม่มีคนกดจอยสติ๊ก หรือ Nav2 ไม่ส่งมาเกิน 2.0 วินาที ให้รถหยุด (safety timeout)
        now = self.get_clock().now()
        if (now - self.last_cmd_time).nanoseconds > 2e9: # 2.0 seconds
            self.current_vL = 0.0
            self.current_vR = 0.0

        # ยิงคำสั่งปัจจุปันส่งไปหา STM32 รัวๆ (Continuous Heartbeat)
        self.send_control_cmd(self.current_vL, self.current_vR)

    def send_control_cmd(self, vL, vR):
        # ปรับปรุง: ใช้ round() เพื่อให้ค่าทศนิยมแม่นยำก่อนคำนวณ Checksum 
        # ป้องกันปัญหา 0.48 * 100 = 47.9999 -> int() แล้วได้ 47 จน Checksum เพี้ยนครับ
        vL_rounded = round(vL, 2)
        vR_rounded = round(vR, 2)
        vL_int = int(round(vL_rounded * 100))
        vR_int = int(round(vR_rounded * 100))
        
        chk = vL_int + vR_int
        cmd_str = f"C,{vL_rounded:.2f},{vR_rounded:.2f},{chk}\n"
        self.send_serial(cmd_str)

    def send_serial(self, data: str):
        # ปรับเป็น debug เพื่อไม่ให้รกหน้าจอ (เพราะมันส่ง 10 ครั้งต่อวินาที)
        self.get_logger().debug(f"[TX to STM32] -> {data.strip()}")
        
        if self.serial_conn is not None and self.serial_conn.is_open:
            try:
                self.serial_conn.write(data.encode('utf-8'))
                # Mirror to ROS2 topic
                msg = String()
                msg.data = data.strip()
                self.pub_serial_tx.publish(msg)
            except Exception as e:
                self.get_logger().error(f"Serial write error: {e}")
                
    def read_serial_data(self):
        while rclpy.ok():
            if self.serial_conn and self.serial_conn.is_open and self.serial_conn.in_waiting > 0:
                try:
                    line = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        # Mirror to ROS2 topic
                        msg = String()
                        msg.data = line
                        self.pub_serial_rx.publish(msg)
                        
                        self.process_stm32_data(line)
                except Exception as e:
                    self.get_logger().debug(f"Error reading STM32 serial: {e}")
            else:
                time.sleep(0.01)

    def process_stm32_data(self, line):
        # รับข้อมูลจาก STM32 ไปกระจายต่อใน ROS2
        if line.startswith('P,'):
            pass # TODO: publish Power
        elif line.startswith('G,'):
            pass # TODO: publish General
        elif line.startswith('D,'):
            try:
                parts = line.split(',')
                if len(parts) >= 5:
                    current_time = self.get_clock().now()
                    msg = Odometry()
                    msg.header.stamp = current_time.to_msg()
                    msg.header.frame_id = "odom"
                    msg.child_frame_id = "base_link"
                    
                    # 1. อ่านค่า Ticks (พัลส์) จาก STM32
                    vL_ticks = float(parts[1]) if parts[1] else 0.0
                    vR_ticks = float(parts[2]) if parts[2] else 0.0
                    pL_ticks = int(parts[3]) if parts[3] else 0
                    pR_ticks = int(parts[4]) if parts[4] else 0
                    
                    # 2. สเกลค่า Ticks ให้กลายเป็น เมตร (Meters) และ m/s
                    # ⚠️ ต้องจูนค่า TICKS_PER_METER นี้ให้ตรงกับมอเตอร์จริง! (สมมติที่ 10,000 tick/เมตร)
                    TICKS_PER_METER = 13450.0 
                    track_width = 0.5 # เมตร
                    
                    vL = vL_ticks / TICKS_PER_METER
                    vR = vR_ticks / TICKS_PER_METER
                    pL = pL_ticks / TICKS_PER_METER  # ตำแหน่งล้อซ้าย (เมตร)
                    pR = pR_ticks / TICKS_PER_METER  # ตำแหน่งล้อขวา (เมตร)
                    
                    # 2.5 Publish ค่าแยกล้อซ้าย-ขวา (สำหรับ Calibrate)
                    enc_msg = Float64()
                    enc_msg.data = vL
                    self.pub_enc_left_vel.publish(enc_msg)
                    enc_msg.data = vR
                    self.pub_enc_right_vel.publish(enc_msg)
                    enc_msg.data = pL
                    self.pub_enc_left_pos.publish(enc_msg)
                    enc_msg.data = pR
                    self.pub_enc_right_pos.publish(enc_msg)
                    
                    # 3. คำนวณความเร็ว (Twist) ในหน่วย m/s และ rad/s
                    v_x = (vR + vL) / 2.0
                    v_th = (vR - vL) / track_width
                    msg.twist.twist.linear.x = v_x
                    msg.twist.twist.angular.z = v_th
                    
                    # 4. คำนวณพิกัดสะสมล้อ (Odometry Position)
                    dt = (current_time - self.last_odom_time).nanoseconds / 1e9
                    import math
                    delta_x = (v_x * math.cos(self.odom_th)) * dt
                    delta_y = (v_x * math.sin(self.odom_th)) * dt
                    delta_th = v_th * dt
                    
                    self.odom_x += delta_x
                    self.odom_y += delta_y
                    self.odom_th += delta_th
                    self.last_odom_time = current_time
                    
                    msg.pose.pose.position.x = self.odom_x
                    msg.pose.pose.position.y = self.odom_y
                    
                    # แปลงมุม odom_th (Euler Yaw) เป็น Quaternion สำหรับ ROS2
                    msg.pose.pose.orientation.z = math.sin(self.odom_th / 2.0)
                    msg.pose.pose.orientation.w = math.cos(self.odom_th / 2.0)
                    
                    # เพิ่ม Covariance (EKF Tuning) เพื่อระบุความไม่แน่นอน
                    msg.pose.covariance[0] = 0.01  # x
                    msg.pose.covariance[7] = 0.01  # y
                    msg.pose.covariance[35] = 0.05 # yaw
                    msg.twist.covariance[0] = 0.01 # linear.x
                    msg.twist.covariance[35] = 0.05 # angular.z

                    self.pub_odom.publish(msg)
            except Exception as e:
                self.get_logger().debug(f"Encoder Parse Error: {e}")

def main(args=None):
    rclpy.init(args=args)
    node = TeleopSTMNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        # สั่งหยุดรถก่อนปิดโหนด
        if hasattr(node, 'serial_conn') and node.serial_conn and node.serial_conn.is_open:
            node.serial_conn.write(b"C,0.00,0.00,0\n")
            time.sleep(0.1)
            node.serial_conn.close()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
