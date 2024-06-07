from asyncore import read
from ssl import AlertDescription
from turtle import update
from urllib import request
from numpy import power
from pymodbus.client.sync import ModbusSerialClient as ModbusClient
import paho.mqtt.client as mqtt
import json
import threading
import time, os
from datetime import datetime                                                       
import jwt
from flask import Flask, render_template, request, url_for, redirect, session, flash, g, session, jsonify
import requests
from flask_socketio import SocketIO, send, emit
import random

client = None
client1 = ModbusClient(method='rtu', port='/dev/ttyAMA2',baudrate = 9600,timeout=1,parity='N',stopbits=1)
client1.connect()
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
def get_token():
    f = open("/home/pi/Desktop/vts/license.txt", "r")
    dec_str = decode_func(f.read().strip(), "vts@2022")
    print(dec_str['token'])
    f.close()

    return dec_str['token']
def get_server():
    f = open("/home/pi/Desktop/vts/license.txt", "r")
    dec_str = decode_func(f.read().strip(), "vts@2022")
    f.close()
    print(dec_str['server'])

    server ="103.199.6.216"
    print(server)
    return server
    # return dec_str['server']
def get_device_type():
    f = open("/home/pi/Desktop/vts/license.txt", "r")
    dec_str = decode_func(f.read().strip(), "vts@2022")
    f.close()
    print(dec_str['device_type'])
    return dec_str['device_type']
def waiting_for_network(test_url="google.com"):
    while True:
        try:
            res = os.system("ping -c 1 " + test_url)
            if res == 0:
                break
            else:
                print_log("Waiting for network")
                time.sleep(5)
        except Exception as err:
            print_log(str(err))

def set_relay(channel, value):
    if pump_state[channel-1]!=value:
        coil =channel - 1
        slave_id=1
        print("Set Relay:" + str(channel) +":" + str(value))
        if value:
            client1.write_coil(coil, 1, unit=slave_id) 
                
        else:
            client1.write_coil(coil, 0, unit=slave_id)
            if coil==0 or coil==1:
                client1.write_register(8192, 5, unit=11) 
        payload = {"pump"+ str(channel): value}
        update_hmi(payload)
        push_telemetry(payload)
        pump_state[channel-1] = value

def update_float(channel, value):
    global float_state
    if float_state[channel-1]!=value:
        payload = {"floatState"+ str(channel): value}
        update_hmi(payload)
        push_telemetry(payload)
        float_state[channel-1] = value

def set_frequency_vf(channel,value):
    frequency = int(value)*100
    # channel= channel +10
    # for testing
    slave_id=11
    client1.write_register(8192, 1, unit=slave_id)
    client1.write_registers(8193, frequency, unit=slave_id)   
    print("Set frequency: %d: %d" %(channel,value))


def push_telemetry(payload_telemetry):
    print("Push Telemetry: %s" %payload_telemetry)
    client.publish(TOPIC_P_TELEMETRY, json.dumps(payload_telemetry), 0)
def update_hmi(payload_telemetry):
    print("Update HMI: %s" %payload_telemetry)
    socketio.emit('state', json.dumps(payload_telemetry))

def read_float():
    try:
        global float_state,old_status
        float_state_rr = client1.read_discrete_inputs(0, 8, unit=1)   
        for i in range(0,8,1):        
            # if i==2 or i==1:
            #     # if float_state_rr.bits[i]:
            #     float_value = not float_state_rr.bits[i]
                    # float_state[i] = False
                # else:
                    # float_state[i] = True
                # float_state[i]= float_state_rr.bits[i]
            # else:
                # float_state[i]=float_state_rr.bits[i]                
            float_value = float_state_rr.bits[i]
            update_float(i+1,float_value)
            
            
        #0-> True
        #1 -> Fasle
        if  float_state[0] and not float_state[1]:
            print("che do 1")
            return 1
        elif not float_state[0] and not float_state[1]:
            print("che do 5")
            return 5
        elif not float_state[0] and float_state[1]:
            print("che do 2")
            return 2
        elif float_state[0] and float_state[1] and not float_state[2] and float_state[3] and float_state[4]:
            print("che do 3")
            return 3
        elif not float_state[1]:
            print("che do 5")
            return 5
        elif float_state[1] and not float_state[2] and not float_state[3]:
            print("che do 2")
            return 2
        elif float_state[2]:
            if old_status ==3:
                return 4
        else:
            return 5
        
        # elif float_state[2]:
        #     if not float_state[3] or not float_state[4]:
        #         return 4

       
    except Exception as e:
        print(e)
def auto_mode():
    global g_mode,old_status
    x=read_float()
    if g_mode:
        # if x = old_float_status:

        # if x != old_status:
        #     for i in range(0,8,1):      
        #         payload_float= {"floatState" + str(i+1):float_state[i]}             
        #         push_telemetry(payload_float)
        if x==1 :
            raw_process_on()
        elif x==2:
            raw_process_off()
        elif x==4 :
            RO_process_off()
        elif x==5:
            system_off()
        elif x==3:
            RO_process_on()
        old_status=x
    else:
        print("MANUAL RUNNING")
        payload={"runningOperation":"Đang ở chế độ Manual"}
        update_hmi(payload)  

def threshold_pressure_thread():
    global pressure,g_pressure_max,check_state_pressure,g_power
    try:
        pressure=client1.read_holding_registers(4372,1,unit=11)
        if int(pressure.registers[0])>220:
            pressure=round(((int(pressure.registers[0])-200)/(800)*25),1)
        else:
            pressure=float(0)
        payload={"pressure1":pressure}
        print(payload)
        update_hmi(payload)
        push_telemetry(payload)
        if pressure > int(g_pressure_max):
            # setup_power_device(False)
            msg_alert="Áp suất hiện tại là: " + str(pressure) + "(bar). Cao hơn ngưỡng cho phép: "+str(g_pressure_max) + "(bar)."
            payload={"alert":msg_alert}
            update_hmi(payload)
            push_telemetry(payload)
        else:
            msg_alert="Hệ Thông Tốt"
    except Exception as e:
        print(e) 
    t = threading.Timer(THRESHOLD_PRESSURE_TIME, threshold_pressure_thread)
    t.start()
# Running Mode
def raw_process_on():
    global pump_mode,inverter1,inverter2
    try:
        if pump_mode[0]:
            set_relay(1, True)
            set_frequency_vf(1, inverter1)
        if pump_mode[1]:
            set_relay(2, False) 
        if pump_mode[2]:
            set_relay(3, False)
        if pump_mode[3]:
            set_relay(4, False)    
        if pump_mode[4]:
            set_relay(5, False)         
        if pump_mode[5]:
            set_relay(6, False)
        payload={"runningOperation":"Lọc Thô Hoạt Động"}
        update_hmi(payload)  
        push_telemetry(payload)
    except Exception as e:
        print(e)
def raw_process_off():
    global pump_mode
    try:
        if pump_mode[0]:
            set_relay(1, False)
        if pump_mode[1]:
            set_relay(2, False) 
        if pump_mode[2]:
            set_relay(3, False)
        if pump_mode[3]:
            set_relay(4, False)    
        if pump_mode[4]:
            set_relay(5, False)         
        if pump_mode[5]:
            set_relay(6, False)
        payload={"runningOperation":"Lọc Thô Không Hoạt Động"}
        update_hmi(payload)  
        push_telemetry(payload)
    except Exception as e:
        print(e)
def RO_process_on():   
    global g_set_time1, previous_time, t1_change_pump,pump_mode,is_RO_process,inverter2
    try:
        if pump_mode[0]:
            set_relay(1, False)
        if pump_mode[1]:
            set_relay(2, True)
            set_frequency_vf(1, inverter2)
        if pump_mode[2]:
            set_relay(3, False)
        if pump_mode[5]:
            set_relay(6, True)
        if(time.time() - previous_time) > g_set_time1:
            t1_change_pump = not t1_change_pump
            previous_time=time.time()
            if t1_change_pump:
                if pump_mode[3]:
                    set_relay(4, True)
                if pump_mode[4]:
                    set_relay(5, False)
            else:
                if pump_mode[3]:
                    set_relay(4, False)
                if pump_mode[4]:
                    set_relay(5, True)                 
        is_RO_process=True
        payload={"runningOperation":"Lọc RO Hoạt Động"}
        update_hmi(payload)  
        push_telemetry(payload)  
    except Exception as e:
        print(e)
def RO_process_off(): 
    global g_set_time2, previous_time2,is_RO_off_process_started,old_status,pump_mode,is_RO_process
    try:
        if is_RO_process:
            if not is_RO_off_process_started:
                if pump_mode[0]:
                    set_relay(1, False)
                if pump_mode[1]:
                    set_relay(2, False) 
                if pump_mode[2]:
                    set_relay(3, True)
                if pump_mode[3]:
                    set_relay(4, False)    
                if pump_mode[4]:
                    set_relay(5, False)         
                if pump_mode[5]:
                    set_relay(6, True)
                previous_time2 =time.time()
                is_RO_off_process_started = True
            else:
                if (time.time() - previous_time2) > g_set_time2:
                    if is_RO_off_process_started:
                        if pump_mode[0]:
                            set_relay(1, False)
                        if pump_mode[1]:
                            set_relay(2, False) 
                        if pump_mode[2]:
                            set_relay(3, False)
                        if pump_mode[3]:
                            set_relay(4, False)    
                        if pump_mode[4]:
                            set_relay(5, False)         
                        if pump_mode[5]:
                            set_relay(6, False)
                        is_RO_off_process_started = False  
                        is_RO_process=False
            payload={"runningOperation":"Lọc RO không hoạt động"}
            update_hmi(payload)   
            push_telemetry(payload)
    except Exception as e:
        print(e)

def system_off():
    global pump_mode
    try:
        if pump_mode[0]:
            set_relay(1, False)
        if pump_mode[1]:
            set_relay(2, False) 
        if pump_mode[2]:
            set_relay(3, False)
        if pump_mode[3]:
            set_relay(4, False)    
        if pump_mode[4]:
            set_relay(5, False)         
        if pump_mode[5]:
            set_relay(6, False)
        payload={"runningOperation":"Không Hoạt Động"}
        update_hmi(payload)   
        push_telemetry(payload)
    except Exception as e:
        print(e)
#Thread
def on_pump_auto_thread():   
    global float_state,g_mode,g_power
    try:
        if g_power: 
            auto_mode()    
    except Exception as e:
        print(e) 
    t = threading.Timer(READ_FLOAT_TIMER, on_pump_auto_thread)
    t.start()
  
def setup_power_device(power_state):
    global g_power
    try:     
        payload= {"power":power_state}
        g_power=power_state
        push_telemetry(payload)
        update_hmi(payload)
        if not power_state:
            for i in range(0, 8, 1):
                payload= {"pump"+ str(i+1): False} 
                set_relay(i, False)
                update_hmi(payload)
                push_telemetry(payload)
    except Exception as e:
        print(e) 
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
            # if 'vf' in  data["method"]:
            #     if power:
            #         payload= {data["method"]:data["params"]}
            #         channel = int(data["method"].replace('pump',''))+10
            #         # set_vf(channel, data["params"])
            #         update_hmi(payload)
            #         push_telemetry(payload)
            #     else:
            #         print("Power State is off. Can not change from Remote")      
            if 'inverter' in  data["method"]:
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
                    update_hmi(payload)
                    push_telemetry(payload)
            if data["method"]=="setMode":        
                payload= {"mode":data["params"]}
                update_hmi(payload)
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

app = Flask(__name__, template_folder='templates')
socketio = SocketIO(app)
APP_ROOT = os.path.dirname(os.path.abspath(
    __file__))   # refers to application_top
APP_STATIC = os.path.join(APP_ROOT, 'static')

@app.route("/")
def main():
    return response_out_ok

response_out_ok = app.response_class(
    json.dumps({'result': 'successfull'}),
    status=200,
    mimetype='application/json'
)
response_out_nok = app.response_class(
    json.dumps({'result': 'unsuccessfull'}),
    status=200,
    mimetype='application/json'
)

# API for HMI
@app.route('/api/set_pump', methods=['POST'])
def api_set_pump():
    try:
        if request.method == "POST":
            push_telemetry(json.dumps(request.get_json()))
            update_hmi(json.dumps(request.get_json()))
            pairs = request.get_json().items()
            for key, value in pairs:
                channel = int(key.replace('pump',''))

                print(channel)
                set_relay(channel,value)

                # for testing
                if channel ==1 or channel ==2:
                    client1.write_register(8192, 5, unit=11) 



            return response_out_ok
        else:
            return response_out_nok
    except AssertionError as error:
        print(error)
        
@app.route('/api/set_power', methods=['POST'])
def api_set_power():
    global g_power
    try:
        if request.method == "POST":
            pairs = request.get_json().items()
            for key, value in pairs:
                if key == "power":
                    g_power = value
                    payload= {key:value}
                    push_telemetry(payload)
                    if not value:
                        for i in range(0,8,1):
                            set_relay(i, False)
                            payload = {"pump"+ str(i+1): False}
                            update_hmi(payload)
                            push_telemetry(payload)

            return response_out_ok
        else:
            return response_out_nok
    except AssertionError as error:
        print(error)
        
@app.route('/api/set_mode', methods=['POST'])
def api_set_mode():
    global payload_telemetry,g_mode
    try:
        if request.method == "POST":
            pairs = request.get_json().items()
            print(request.get_json())
            for key, value in pairs:
                if(key == "mode"):
                    g_mode=value     # true:auto,false:manual
                    socketio.emit('state', json.dumps({key: value}))
                    if not g_mode:
                        for i in range(1, 8, 1):
                            payload= {"pump"+ str(i): False} 
                            set_relay(i, False)
                            update_hmi(payload)
                            push_telemetry(payload)

                    payload_telemetry= {key:value}
                    push_telemetry(payload_telemetry)      
            return response_out_ok
        else:
            return response_out_nok
    except AssertionError as error:
        print(error)

@app.route('/api/set_configuration', methods=['POST'])
def api_set_configuration():
    global payload_telemetry,g_mode,g_pressure_max,g_set_time1,g_set_time2,inverter1,inverter2
    try:
        if request.method == "POST":
            pairs = request.get_json().items()
            print(request.get_json())  
            for key, value in pairs:
                if(key == "pressureMax"):
                    g_pressure_max=int(value) 
                if key=="setTime1":
                    g_set_time1=int(value)
                if key=="setTime2":
                    g_set_time2=int(value)
                if key=="inverter1":
                    inverter1=int(value)
                    set_frequency_vf(1,int(value))
                if key=="inverter2":
                    inverter2=int(value)
                    set_frequency_vf(2,int(value))
                payload_telemetry= {key:value}
                push_telemetry(payload_telemetry)     
                update_hmi(payload_telemetry) 
            return response_out_ok
        else:
            return response_out_nok
    except AssertionError as error:
        print(error)

@app.route('/api/set_frequency_vf', methods=['POST'])
def api_set_frequency_vf():
    try:
        if request.method == "POST":
            client.publish(TOPIC_P_TELEMETRY,
                           json.dumps(request.get_json()), 1)
            print(request.get_json())
            pairs = request.get_json().items()
            for key, value in pairs:
                    set_frequency_vf(key,value)
            return response_out_ok
        else:
            return response_out_nok
    except AssertionError as error:
        print(error)

# @app.route('/api/update_pump', methods=['POST'])
# def update_pump():
#     try:
#         if request.method == "POST":
#             print(request.get_json())
#             print("call socket io")
#             socketio.emit('state', request.get_json())
#             return response_out_ok
#         else:
#             return response_out_nok
#     except AssertionError as error:
        # print(error)

def flaskThread():
    app.run()


def main():
    try:
        waiting_for_network()

        t = threading.Thread(target=thingsboard)
        t.start()

        time.sleep(2)
        flask_thread = threading.Thread(target=flaskThread)
        flask_thread.start()

        time.sleep(5)
        pump_data_thread = threading.Thread(target=on_pump_auto_thread)
        pump_data_thread.start()

        time.sleep(1)
        pressure_thread = threading.Thread(target=threshold_pressure_thread())
        pressure_thread.start()

    except Exception as err_msg:
        print(err_msg)
if __name__ == "__main__":
    main()