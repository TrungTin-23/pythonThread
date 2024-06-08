
import paho.mqtt.client as mqtt
import json
import threading
import time, os
from datetime import datetime  
import subprocess                                                     
client = None

TOPIC_P_TELEMETRY = "v1/devices/me/telemetry"
TOPIC_P_ATTRIBUTES = "v1/devices/me/attributes"
TOPIC_P_CLIENT_RPC = "v1/devices/me/rpc/response/+"
TOPIC_S_SERVER_RPC = "v1/devices/me/rpc/request/+" 
TOPIC_P_CLIENT_ATTRIBUTES = 'v1/devices/me/attributes/response/+'

t1_change_pump=False
g_pressure_max=24
check_state_pressure=True
g_mode=False
g_power=False
g_set_time1= 20
g_set_time2= 20
inverter1=50
inverter2=50
previous_time =time.time()
previous_time2=time.time()
READ_FLOAT_TIMER=5
TB_TIMER=0.5
THRESHOLD_PRESSURE_TIME=5
old_status=0
is_RO_off_process_started = False
is_RO_process=False

pump_state = [True, True, True, True, True,True,True,True]
float_state =[True, True, True, True, True,True,True,True]
pump_mode=[True, True, True, True, True,True,True,True]

def decode_func(encoded_str, password):
    decoded_str = jwt.decode(encoded_str, password, algorithms=['HS256'])
    return decoded_str
def get_server():
    f = open("/home/pi/Desktop/vts/license.txt", "r")
    dec_str = decode_func(f.read().strip(), "vts@2022")
    f.close()
    print(dec_str['server'])

    server ="103.199.6.216"
    print(server)
    return server

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



def push_telemetry(payload_telemetry):
    print("Push Telemetry: %s" %payload_telemetry)
    client.publish(TOPIC_P_TELEMETRY, json.dumps(payload_telemetry), 0)


def on_pump_auto_thread():   
    global float_state,g_mode,g_power
    try:
        if g_power: 
            auto_mode()    
    except Exception as e:
        print(e) 
    t = threading.Timer(READ_FLOAT_TIMER, on_pump_auto_thread)
    t.start()

def get_token():
    f = open("/home/pi/Desktop/vts/license.txt", "r")
    dec_str = decode_func(f.read().strip(), "vts@2022")
    print(dec_str['token'])
    f.close()


def thingsboard():
    try:   
        global client
        def on_connect(client, userdata, rc, *extra_params):
            print('Connected with result code ' + str(rc))
            client.subscribe(TOPIC_S_SERVER_RPC)

        def on_message(client, userdata, msg): 
            global g_power,g_mode,g_pressure_max,g_set_time1,g_set_time2,inverter1,inverter2
            if msg.topic.startswith('v1/devices/me/rpc/request/'):
                requestId = msg.topic[len('v1/devices/me/rpc/request/'):len(msg.topic)]
            data = json.loads(msg.payload)
            if 'pumpMode' in  data["method"]:
                if power:
                    payload= {data["method"]:data["params"]}
                    channel = int(data["method"].replace('modeState',''))
                    if data["params"]:
                        pump_mode[channel-1]=True
                    else:
                        pump_mode[channel-1]=False
                    push_telemetry(payload)
                else:
                    print("Power State is off. Can not change from Remote")  
            if 'pump' in  data["method"]:
                if power:
                    payload= {data["method"]:data["params"]}
                    channel = int(data["method"].replace('pump',''))
                    set_relay(channel, data["params"])
                    update_hmi(payload)
                    push_telemetry(payload)
                else:
                    print("Power State is off. Can not change from Remote")      
           
                if power:
                    payload= {data["method"]:data["params"]}
                    channel = int(data["method"].replace('inverter',''))
                    if channel==1:
                        inverter1=int(data["params"])
                    if channel==2:
                        inverter2=int(data["params"])                
                    set_frequency_vf(channel, int(data["params"]))
                    update_hmi(payload)
                    push_telemetry(payload)
                else:
                    print("Power State is off. Can not change from Remote")                           
            if data["method"]=="setPower":
                setup_power_device(data["params"])
            if data["method"]=="setConfiguration": 
                pressure_setting=data["params"]
                for key, value in pressure_setting.items(): 
                    if key=="pressureMax":
                        g_pressure_max=value
                    if key=="setTime1":
                        g_set_time1=int(value)
                    if key=="setTime2":
                        g_set_time2=int(value)
                    payload={key:value}
    
                    push_telemetry(payload)
            if data["method"]=="setMode":        
                payload= {"mode":data["params"]}
 
                push_telemetry(payload)

        client = mqtt.Client()
        client.on_connect = on_connect
        client.on_message = on_message
        client.username_pw_set(get_token())
        client.connect(get_server(), 3009, 60)
        client.loop_forever()
    except Exception as e:
        print(e)
    t = threading.Timer(TB_TIMER, thingsboard)
    t.start()


def main():
    try:
        waiting_for_network()

        t = threading.Thread(target=thingsboard)
        t.start()



        time.sleep(5)
        pump_data_thread = threading.Thread(target=on_pump_auto_thread)
        pump_data_thread.start()


    except Exception as err_msg:
        print(err_msg)
if __name__ == "__main__":
    main()