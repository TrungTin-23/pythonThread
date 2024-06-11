
import paho.mqtt.client as mqtt
import json
import threading
import time, os
from datetime import datetime  
import subprocess  
import platform
import socket
import psutil
                                      

previous_time =time.time()
previous_time2=time.time()
READ_FLOAT_TIMER=5
TB_TIMER=0.5
THRESHOLD_PRESSURE_TIME=5


pump_state = [True, True, True, True, True,True,True,True]
float_state =[True, True, True, True, True,True,True,True]
pump_mode=[True, True, True, True, True,True,True,True]

def get_platform():
    return platform.system()

def get_platform_release():
    return platform.release()

def get_platform_version():
    return platform.version()

def get_architecture():
    return platform.machine()

def get_hostname():
    return socket.gethostname()

def get_processor():
    return platform.processor()

def get_ram():
    return str(round(psutil.virtual_memory().total / (1024.0 **3)))+" GB"

def get_system_info():
    info = {}
    info['platform'] = get_platform()
    info['platform-release'] = get_platform_release()
    info['platform-version'] = get_platform_version()
    info['architecture'] = get_architecture()
    info['hostname'] = get_hostname()
    info['processor'] = get_processor()
    info['ram'] = get_ram()
    return info

def waiting_for_network(test_url="google.com"):
    while True:
        try:
            res = subprocess.call(["ping", "-c", "1", test_url])
            if res == 0:
                print("Network connected")
                break
            else:
                print("Waiting for network")
                time.sleep(5)
        except Exception as err:
            print(f"An error occurred: {err}")


def on_connect(client, userdata, rc, *extra_params):
    print('Connected with result code ' + str(rc))

def connect_to_thingsboard():
    try:
        client = mqtt.Client()
        client.on_connect = on_connect
        client.username_pw_set('T2_TEST_TOKEN')
        client.connect('212.38.94.144', 1884, 60)
        client.loop_start()
    except Exception as e:
        print(e)
        t = threading.Timer(TB_TIMER, connect_to_thingsboard)
        t.start()
    return client


def send_data_to_thingsboard(client, data):
    client.loop_start()
    client.publish('v1/devices/me/telemetry', json.dumps(data), 1)

    THINGSBOARD_HOST = '212.38.94.144'
    ACCESS_TOKEN = 'T2_TEST_TOKEN'

    client = connect_to_thingsboard()
    data = get_system_info()
    send_data_to_thingsboard(client, data)

def main():
    try:
        #waiting_for_network()
        client = connect_to_thingsboard()
        data = get_system_info()
        t = threading.Thread(target=connect_to_thingsboard)
        t.start()



        time.sleep(5)
        pump_data_thread = threading.Thread(target=send_data_to_thingsboard,args=(client, data))
        pump_data_thread.start()


    except Exception as err_msg:
        print(err_msg)
if __name__ == "__main__":
    main()