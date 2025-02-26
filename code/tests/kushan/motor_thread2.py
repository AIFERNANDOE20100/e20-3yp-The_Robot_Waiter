import RPi.GPIO as GPIO
import time
import paho.mqtt.client as mqtt
import os
import threading  # For auto-stop timer
import multiprocessing
from ultrasonic_thread1 import measure_distance  # Import the distance measure function

# Define GPIO pins for the motors
IN1 = 17  # Motor 1
IN2 = 27
IN3 = 22  # Motor 2
IN4 = 23

# AWS IoT Core Details
AWS_ENDPOINT = "a2cdp9hijgdiig-ats.iot.ap-southeast-2.amazonaws.com"
MQTT_TOPIC = "/3YP/batch2025/device1"

# Paths to AWS IoT Core certificates
CA_CERT = "../../AWS/AmazonRootCA1.pem"
CERT_FILE = "../../AWS/d963cd1faf2a812ee9a50f1257971e394cdb03d34b49e6f9d787e81fdd2630fa-certificate.pem.crt"
KEY_FILE = "../../AWS/d963cd1faf2a812ee9a50f1257971e394cdb03d34b49e6f9d787e81fdd2630fa-private.pem.key"

# Validate certificate paths
for file in [CA_CERT, CERT_FILE, KEY_FILE]:
    if not os.path.exists(file):
        raise FileNotFoundError(f"Certificate file not found: {file}")

# Setup GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(IN1, GPIO.OUT)
GPIO.setup(IN2, GPIO.OUT)
GPIO.setup(IN3, GPIO.OUT)
GPIO.setup(IN4, GPIO.OUT)
GPIO.setwarnings(False)

# Auto-stop timer variable
motor_timer = None

# Function to stop motors after timeout
def stop_motor_after_timeout(timeout=5):
    global motor_timer
    if motor_timer:
        motor_timer.cancel()  # Cancel previous timer if any
    motor_timer = threading.Timer(timeout, motor_stop)
    motor_timer.start()

# Function to move motors forward
def motor_forward():
    print("🚀 Moving forward")
    GPIO.output(IN1, GPIO.HIGH)
    GPIO.output(IN2, GPIO.LOW)
    GPIO.output(IN3, GPIO.HIGH)
    GPIO.output(IN4, GPIO.LOW)
    stop_motor_after_timeout()

# Function to move motors backward
def motor_backward():
    print("🔄 Moving backward")
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.HIGH)
    GPIO.output(IN3, GPIO.LOW)
    GPIO.output(IN4, GPIO.HIGH)
    stop_motor_after_timeout()

# Function to turn left (motors move in opposite directions)
def motor_left():
    print("⬅️ Turning left")
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.HIGH)
    GPIO.output(IN3, GPIO.HIGH)
    GPIO.output(IN4, GPIO.LOW)
    stop_motor_after_timeout()

# Function to turn right (motors move in opposite directions)
def motor_right():
    print("➡️ Turning right")
    GPIO.output(IN1, GPIO.HIGH)
    GPIO.output(IN2, GPIO.LOW)
    GPIO.output(IN3, GPIO.LOW)
    GPIO.output(IN4, GPIO.HIGH)
    stop_motor_after_timeout()

# Function to stop motors
def motor_stop():
    print("🛑 Stopping motors")
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.LOW)
    GPIO.output(IN3, GPIO.LOW)
    GPIO.output(IN4, GPIO.LOW)

# MQTT callback for successful connection
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("✅ Connected to AWS IoT Core")
        client.subscribe(MQTT_TOPIC)
        print(f"📡 Subscribed to topic: {MQTT_TOPIC}")
    else:
        print(f"⚠️ Connection failed with error code {rc}")

# MQTT callback when a message is received
def on_message(client, userdata, msg):
    global motor_timer
    payload = msg.payload.decode()
    print(f"📩 Message received: {payload}")

    # Check if distance is safe to move
    if shared_distance.value < 30:
        motor_stop()
        print("🚫 Too close, stopping motors")
        return

    if payload == '{"key":"ArrowUp"}':
        motor_forward()
    elif payload == '{"key":"ArrowDown"}':
        motor_backward()
    elif payload == '{"key":"ArrowLeft"}':
        motor_left()
    elif payload == '{"key":"ArrowRight"}':
        motor_right()
    else:
        motor_stop()
        if motor_timer:
            motor_timer.cancel()

# MQTT client setup
client = mqtt.Client()

# Set TLS certificates for AWS IoT
client.tls_set(ca_certs=CA_CERT, certfile=CERT_FILE, keyfile=KEY_FILE)

# Attach callbacks
client.on_connect = on_connect
client.on_message = on_message

# Shared memory for distance
shared_distance = multiprocessing.Value('d', 0.0)

# Start the ultrasonic process in another process
ultrasonic_process = multiprocessing.Process(target=measure_distance, args=(shared_distance,))
ultrasonic_process.start()

# Connect to AWS IoT Core
print(f"🔗 Connecting to AWS IoT Core at {AWS_ENDPOINT}...")
client.connect(AWS_ENDPOINT, 8883, 60)

# Start MQTT client loop
try:
    client.loop_start()
    print("✅ MQTT client running... Waiting for messages.")
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\n🛑 Stopping MQTT client...")
finally:
    motor_stop()
    GPIO.cleanup()
    client.loop_stop()
    ultrasonic_process.terminate()
    print("✅ Cleanup complete. Exiting.")

