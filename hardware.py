import time
import serial
from serial.tools import list_ports

BAUD=115200

def available_ports():
    return [(port.device, port.description or port.device) for port in list_ports.comports()]

def connect(port):
    connection=serial.Serial(port, BAUD, timeout=0.15, write_timeout=1)
    time.sleep(2.0)  # Opening a USB serial port commonly restarts the ESP32.
    return connection

def send_line(connection, text):
    if connection is None or not connection.is_open:
        raise RuntimeError("ESP32 is not connected. Choose its COM port and connect first.")
    safe=text.replace("|"," ").replace("\r"," ").replace("\n"," ")
    connection.write((safe+"\n").encode("utf-8"))
    connection.flush()

def read_lines(connection):
    if connection is None or not connection.is_open: return []
    lines=[]
    while connection.in_waiting:
        line=connection.readline().decode("utf-8",errors="replace").strip()
        if line: lines.append(line)
    return lines
