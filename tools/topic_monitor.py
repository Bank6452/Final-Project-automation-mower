#!/usr/bin/env python3
"""
ROS2 Topic Monitor — Standalone Version
รันตรงได้เลย: python3 topic_monitor.py
(ต้อง source ROS2 ก่อน: source /opt/ros/humble/setup.bash && source ~/ros2_ws/install/setup.bash)
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Imu, Range
from std_msgs.msg import Int8, Float64, String
import math
import time
import os

# ─── สี Terminal ────────────────────────────────────────────────
R   = '\033[91m'
G   = '\033[92m'
Y   = '\033[93m'
B   = '\033[94m'
C   = '\033[96m'
W   = '\033[97m'
D   = '\033[2m'
RST = '\033[0m'
BOLD= '\033[1m'

TIMEOUT = 1.0  # วิ — ถ้าไม่ได้รับนานกว่านี้ = DEAD


class TopicMonitor(Node):
    def __init__(self):
        super().__init__('topic_monitor')

        self.data      = {}
        self.stamp     = {}
        self.cnt       = {}
        self.hz        = {}

        subs = [
            ('/cmd_vel',                Twist,    self._cmd_vel),
            ('/odom_raw',               Odometry, self._odom_raw),
            ('/odometry/filtered',      Odometry, self._odom_filt),
            ('/odometry/global',        Odometry, self._odom_glob),
            ('/camera/camera/imu',      Imu,      self._imu),
            ('/ultrasonic/left',        Range,    self._ul),
            ('/ultrasonic/center',      Range,    self._uc),
            ('/ultrasonic/right',       Range,    self._ur),
            ('/ultrasonic_raw',         String,   self._uraw),
            ('/emergency_stop',         Int8,     self._emg),
            ('/encoder/left_velocity',  Float64,  self._elv),
            ('/encoder/right_velocity', Float64,  self._erv),
            ('/encoder/left_position',  Float64,  self._elp),
            ('/encoder/right_position', Float64,  self._erp),
        ]

        for topic, mtype, cb in subs:
            self.create_subscription(mtype, topic, cb, 10)
            self.data[topic]  = None
            self.stamp[topic] = 0.0
            self.cnt[topic]   = 0
            self.hz[topic]    = 0.0

        self.create_timer(1.0,  self._tick_hz)
        self.create_timer(0.25, self._draw)

    # ── helpers ─────────────────────────────────────────────────
    def _rec(self, key, val):
        self.data[key]  = val
        self.stamp[key] = time.time()
        self.cnt[key]   = self.cnt.get(key, 0) + 1

    def _tick_hz(self):
        for k in self.cnt:
            self.hz[k]  = float(self.cnt[k])
            self.cnt[k] = 0

    def _alive(self, k):
        return (time.time() - self.stamp.get(k, 0.0)) < TIMEOUT

    def _st(self, k):
        if self.stamp[k] == 0.0:
            return f'{D}WAIT{RST}'
        return f'{G}LIVE{RST}{D} {self.hz[k]:.0f}Hz{RST}' if self._alive(k) else f'{R}DEAD{RST}'

    def _rng(self, r):
        if r is None:   return f'{D}---{RST}'
        if math.isinf(r): return f'{G}CLEAR {RST}'
        col = R if r < 0.30 else Y if r < 0.60 else G
        return f'{col}{r:.2f}m{RST}'

    def _yaw(self, q):
        return math.degrees(math.atan2(2*(q.w*q.z + q.x*q.y),
                                       1 - 2*(q.y*q.y + q.z*q.z)))

    # ── callbacks ────────────────────────────────────────────────
    def _cmd_vel(self, m):
        self._rec('/cmd_vel', {'vx': m.linear.x, 'wz': m.angular.z})

    def _odom_raw(self, m):
        self._rec('/odom_raw', {
            'x': m.pose.pose.position.x, 'y': m.pose.pose.position.y,
            'yaw': self._yaw(m.pose.pose.orientation),
            'vx': m.twist.twist.linear.x, 'wz': m.twist.twist.angular.z})

    def _odom_filt(self, m):
        self._rec('/odometry/filtered', {
            'x': m.pose.pose.position.x, 'y': m.pose.pose.position.y,
            'yaw': self._yaw(m.pose.pose.orientation),
            'vx': m.twist.twist.linear.x, 'wz': m.twist.twist.angular.z})

    def _odom_glob(self, m):
        self._rec('/odometry/global', {
            'x': m.pose.pose.position.x, 'y': m.pose.pose.position.y,
            'yaw': self._yaw(m.pose.pose.orientation)})

    def _imu(self, m):
        q = m.orientation
        roll  = math.atan2(2*(q.w*q.x+q.y*q.z), 1-2*(q.x*q.x+q.y*q.y))
        pitch = math.asin(max(-1.0, min(1.0, 2*(q.w*q.y-q.z*q.x))))
        yaw   = math.atan2(2*(q.w*q.z+q.x*q.y), 1-2*(q.y*q.y+q.z*q.z))
        self._rec('/camera/camera/imu', {
            'ax': m.linear_acceleration.x,
            'ay': m.linear_acceleration.y,
            'az': m.linear_acceleration.z,
            'gx': m.angular_velocity.x,
            'gy': m.angular_velocity.y,
            'gz': m.angular_velocity.z,
            'roll':  math.degrees(roll),
            'pitch': math.degrees(pitch),
            'yaw':   math.degrees(yaw)})

    def _ul(self, m):   self._rec('/ultrasonic/left',        {'r': m.range})
    def _uc(self, m):   self._rec('/ultrasonic/center',      {'r': m.range})
    def _ur(self, m):   self._rec('/ultrasonic/right',       {'r': m.range})
    def _uraw(self, m): self._rec('/ultrasonic_raw',         {'s': m.data.strip()})
    def _emg(self, m):  self._rec('/emergency_stop',         {'v': m.data})
    def _elv(self, m):  self._rec('/encoder/left_velocity',  {'v': m.data})
    def _erv(self, m):  self._rec('/encoder/right_velocity', {'v': m.data})
    def _elp(self, m):  self._rec('/encoder/left_position',  {'v': m.data})
    def _erp(self, m):  self._rec('/encoder/right_position', {'v': m.data})

    # ── draw ─────────────────────────────────────────────────────
    def _draw(self):
        os.system('clear')
        t = time.strftime('%H:%M:%S')
        print(f'{BOLD}{B}╔══════════════════════════════════════════════════╗{RST}')
        print(f'{BOLD}{B}║      🤖  Robot Topic Monitor   [{t}]     ║{RST}')
        print(f'{BOLD}{B}╚══════════════════════════════════════════════════╝{RST}')

        # ── CMD VEL ──────────────────────────────────────────────
        self._hdr('📡 CMD_VEL')
        d = self.data['/cmd_vel']
        if d:
            vc = Y if abs(d['vx'])>0.01 else W
            wc = Y if abs(d['wz'])>0.01 else W
            print(f'  vx {vc}{d["vx"]:+.3f}{RST} m/s   wz {wc}{d["wz"]:+.3f}{RST} rad/s'
                  f'   [{self._st("/cmd_vel")}]')
        else:
            print(f'  {D}(ยังไม่มีคำสั่ง){RST}   [{self._st("/cmd_vel")}]')

        # ── ENCODER ──────────────────────────────────────────────
        self._hdr('🔢 ENCODER  (ticks → m/s)')
        lv = self.data.get('/encoder/left_velocity')
        rv = self.data.get('/encoder/right_velocity')
        lp = self.data.get('/encoder/left_position')
        rp = self.data.get('/encoder/right_position')
        vL = lv['v'] if lv else 0.0
        vR = rv['v'] if rv else 0.0
        pL = lp['v'] if lp else 0.0
        pR = rp['v'] if rp else 0.0
        print(f'  Speed  L:{C}{vL:+.3f}{RST} m/s   R:{C}{vR:+.3f}{RST} m/s'
              f'   [{self._st("/encoder/left_velocity")}]')
        print(f'  Pos    L:{C}{pL:+.3f}{RST} m     R:{C}{pR:+.3f}{RST} m')

        # ── ODOM RAW ─────────────────────────────────────────────
        self._hdr('📍 ODOM_RAW  (encoder only, before EKF)')
        d = self.data['/odom_raw']
        if d:
            print(f'  x:{C}{d["x"]:+7.3f}{RST}  y:{C}{d["y"]:+7.3f}{RST}  '
                  f'yaw:{C}{d["yaw"]:+7.1f}°{RST}   [{self._st("/odom_raw")}]')
            print(f'  vx:{C}{d["vx"]:+.3f}{RST} m/s   wz:{C}{d["wz"]:+.3f}{RST} rad/s')
        else:
            print(f'  {D}(no data){RST}   [{self._st("/odom_raw")}]')

        # ── EKF FILTERED ─────────────────────────────────────────
        self._hdr('🧮 ODOMETRY/FILTERED  (EKF local → odom frame)')
        d = self.data['/odometry/filtered']
        if d:
            print(f'  x:{C}{d["x"]:+7.3f}{RST}  y:{C}{d["y"]:+7.3f}{RST}  '
                  f'yaw:{C}{d["yaw"]:+7.1f}°{RST}   [{self._st("/odometry/filtered")}]')
            print(f'  vx:{C}{d["vx"]:+.3f}{RST} m/s   wz:{C}{d["wz"]:+.3f}{RST} rad/s')
        else:
            print(f'  {D}(no data){RST}   [{self._st("/odometry/filtered")}]')

        # ── EKF GLOBAL ───────────────────────────────────────────
        self._hdr('🗺️  ODOMETRY/GLOBAL  (EKF global → map frame)')
        d = self.data['/odometry/global']
        if d:
            print(f'  x:{C}{d["x"]:+7.3f}{RST}  y:{C}{d["y"]:+7.3f}{RST}  '
                  f'yaw:{C}{d["yaw"]:+7.1f}°{RST}   [{self._st("/odometry/global")}]')
        else:
            print(f'  {D}(no data){RST}   [{self._st("/odometry/global")}]')

        # ── IMU ──────────────────────────────────────────────────
        self._hdr('📐 IMU  (/camera/camera/imu)')
        d = self.data['/camera/camera/imu']
        if d:
            print(f'  Accel  x:{C}{d["ax"]:+6.2f}{RST}  y:{C}{d["ay"]:+6.2f}{RST}  '
                  f'z:{C}{d["az"]:+6.2f}{RST} m/s²   [{self._st("/camera/camera/imu")}]')
            print(f'  Gyro   x:{C}{d["gx"]:+6.3f}{RST}  y:{C}{d["gy"]:+6.3f}{RST}  '
                  f'z:{C}{d["gz"]:+6.3f}{RST} rad/s')
            print(f'  Euler  roll:{C}{d["roll"]:+6.1f}°{RST}  '
                  f'pitch:{C}{d["pitch"]:+6.1f}°{RST}  '
                  f'yaw:{C}{d["yaw"]:+6.1f}°{RST}')
        else:
            print(f'  {D}(no data){RST}   [{self._st("/camera/camera/imu")}]')

        # ── ULTRASONIC ───────────────────────────────────────────
        self._hdr('🔊 ULTRASONIC')
        dL = self.data['/ultrasonic/left']
        dC = self.data['/ultrasonic/center']
        dR = self.data['/ultrasonic/right']
        rL = dL['r'] if dL else None
        rC = dC['r'] if dC else None
        rR = dR['r'] if dR else None
        print(f'  LEFT: {self._rng(rL)}   CENTER: {self._rng(rC)}   '
              f'RIGHT: {self._rng(rR)}   [{self._st("/ultrasonic/left")}]')
        raw = self.data['/ultrasonic_raw']
        if raw:
            print(f'  raw → {D}{raw["s"]}{RST}')

        # ── EMERGENCY ────────────────────────────────────────────
        self._hdr('🚨 EMERGENCY_STOP')
        d = self.data['/emergency_stop']
        if d:
            s = f'{R}EMERGENCY!{RST}' if d['v'] == 1 else f'{G}Normal{RST}'
            print(f'  {s}  (value={d["v"]})   [{self._st("/emergency_stop")}]')
        else:
            print(f'  {D}(ยังไม่ได้ publish){RST}   [{self._st("/emergency_stop")}]')

        print(f'\n{D}  Ctrl+C เพื่อออก{RST}')

    def _hdr(self, title):
        print(f'\n{BOLD}{W}  {title}{RST}')
        print(f'  {"─"*50}')


def main():
    rclpy.init()
    node = TopicMonitor()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
