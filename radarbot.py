from ev3dev2.sensor.lego import UltrasonicSensor
from ev3dev2.motor import MediumMotor
from ev3dev2.motor import LargeMotor
from ev3dev2.sensor.lego import GyroSensor
import time
import socket
import json

# Define motor and sensor stuff
medium_motor = MediumMotor()
r_large_motor = LargeMotor('outD')
l_large_motor = LargeMotor('outB')
initial_position = medium_motor.position
ultrasonic_sensor = UltrasonicSensor()
ultrasonic_sensor.MODE_US_DIST_IN
gyro_sensor = GyroSensor()
gyro_sensor.MODE_GYRO_ANG

def referenced_motor_position():
    return medium_motor.position - initial_position

def radar_scan():
    # Define important variables for scanning and the result
    next_motor_degree = 12.5
    next_ultrasonic_degree = 87.5
    ultrasonic_measurements = []

    # Add initial degree 0 ultrasonic measurement
    ultrasonic_measurements.append([90, round(ultrasonic_sensor.distance_inches)])
    # Start rotating motor
    medium_motor.on(20, brake=True, block=False)

    # Begin recording data
    while referenced_motor_position() < 901:
        if next_motor_degree - 4 <= referenced_motor_position() <= next_motor_degree + 4:
            measurement = ultrasonic_sensor.distance_inches
            if round(measurement, 1) != 100.3:
                ultrasonic_measurements.append([next_ultrasonic_degree, round(measurement, 1)])
            next_motor_degree += 12.5
            next_ultrasonic_degree -= 2.5

    medium_motor.on_for_degrees(-75, medium_motor.position - initial_position, brake=True, block=True)
    time.sleep(0.5)
    medium_motor.on_for_degrees(0, 0, brake=False, block=False)
    response = {"type": "radar", "data": ultrasonic_measurements}
    return response

def rotate(y):
    degrees = float(y)
    gyro_sensor.reset
    gyro_sensor.MODE_GYRO_ANG
    if degrees > 0:
        r_large_motor.on(-20)
        l_large_motor.on(20)
    elif degrees < 0:
        r_large_motor.on(20)
        l_large_motor.on(-20)
    else:
        return({"type": "message", "data": "invalid degrees"})

    gyro_sensor.wait_until_angle_changed_by(degrees, direction_sensitive=True)

    l_large_motor.on_for_degrees(0, 0, brake=True, block=False)
    r_large_motor.on_for_degrees(0, 0, brake=True, block=True)
    time.sleep(0.5)
    l_large_motor.on_for_degrees(0, 0, brake=False, block=False)
    r_large_motor.on_for_degrees(0, 0, brake=False, block=False)

    u = "Rotated {} degrees.".format(degrees)
    return({"type": "message", "data": u})

def move_forward(q):
    feet = float(q)
    inches_to_move = feet * 12
    # 6.926346007913385 inches tire circumference
    r_large_motor.on_for_rotations(35, inches_to_move / 6.926346007913385, brake=True, block=False)
    l_large_motor.on_for_rotations(35, inches_to_move / 6.926346007913385, brake=True, block=True)
    time.sleep(0.3)
    r_large_motor.on_for_rotations(0, 0, brake=False, block=False)
    l_large_motor.on_for_rotations(0, 0, brake=False, block=False)
    x = "Moved forward {} feet.".format(feet)
    response = {"type": "message", "data": x}
    return response

def send_message(connection, message):
    connection.sendall("{}\r\n".format(message).encode('utf-8'))

def request_handler(request):
    if request['type'] == "radar":
        result = radar_scan()
    elif request['type'] == "forward":
        result = move_forward(request['feet'])
    elif request['type'] == "rotate":
        result = rotate(request['degrees'])
    else:
        result = {"type": "message", "data": 'invalid request'}

    return json.dumps(result)

def tcp_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_address = ('0.0.0.0', 8437)
    sock.bind(server_address)
    sock.listen(1)
    print("Listening...")
    connection, client_address = sock.accept()
    connection.setblocking(True)
    print("got client at {}".format(client_address))
    buffer = ""

    while True:
        result = connection.recv(100).decode('utf-8')
        buffer = buffer + result
        lines = buffer.split("\r\n")
        buffer = lines.pop()
        for line in lines:
            request = json.loads(line)
            print("Got a request: {}".format(request))
            response = request_handler(request)
            print("Sending response: {}".format(response))
            send_message(connection, response)

        time.sleep(0.1)


tcp_server()