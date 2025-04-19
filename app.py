from datetime import datetime
from functools import wraps
import json 
import os
from pathlib import Path
from flask import Flask, request, jsonify, abort, session
from pymavlink import mavutil 
import math


from jsonschema import validate
from jsonschema.exceptions import ValidationError
"""
Warning
The debugger allows executing arbitrary Python code from the browser. 
It is protected by a pin, but still represents a major security risk. 
Do not run the development server or debugger in a production environment.
"""

USERNAME = "yeditepezafer"
PASSWORD = "RYc3GnxqQq"

app = Flask(__name__)

app.secret_key = "7d5d7dgrc24n78aw"

ROOT_PATH = Path(os.path.realpath(__file__)).parents[1]


#serial_port="udpin:172.28.224.1:14550"
#serial_port="udpin:localhost:14570"
serial_port="udp:127.0.0.1:14550"
baud_rate=115200

mavlink_connection = None

def get_mavlink_connection():
    global mavlink_connection
    if mavlink_connection is None:
        mavlink_connection = mavutil.mavlink_connection(serial_port, baud=baud_rate)
    return mavlink_connection

def login_required(f):
    @wraps(f)
    def func(*args, **kwargs):
        if "logged_in" not in session or session["logged_in"] is False:
            return jsonify({"hata": "Yetkisiz erisim denemesi"}), 403
        return f(*args, **kwargs)

    return func


@app.route("/api/giris", methods=["POST"])
def login():
    if not request.is_json:
        return jsonify({"hata": "paket formati hatali"}), 204

    data = request.get_json()

    if data is None or "kadi" not in data or "sifre" not in data:
        return jsonify({"hata": "kadi veya sifre eksik"}), 400

    if data["kadi"] == USERNAME and data["sifre"] == PASSWORD:
        session["logged_in"] = True
        return jsonify({"mesaj": "Basarili giris"}), 200
    else:
        return jsonify({"hata": "Hatali kullanici adi veya sifre"}), 401


@app.route("/api/cikis", methods=["GET"])
def logout():
    #eklediklerim
    try:
        session["logged_in"] = False
        return jsonify({"mesaj": "Cikis basarili"}), 200
    except Exception as e:
        return jsonify({f"mesaj : çıkış işlemi başarısız {e}"}),500
    
    #session["logged_in"] = False
    #return jsonify({"mesaj": "Cikis basarili"}), 200

#eklediklerim
schema_time={"type":"object",
             "properties":{
                 "gun":{
                     "type":"integer"
                 },
                 "saat":{
                     "type":"integer"
                 },
                 "dakika":{
                     "type":"integer"   
                 },
                 "saniye":{
                     "type":"integer" 
                 },
                 "milisaniye":{
                     "type":"integer" 
                 }
             },
             "required":["gun","saat","dakika","saniye","milisaniye"]
}
   

@app.route("/api/sunucusaati", methods=["GET"])
@login_required
def server_hour():
    now = datetime.now()
    server_time = {
        "gun": now.day,
        "saat": now.hour,
        "dakika": now.minute,
        "saniye": now.second,
        "milisaniye": now.microsecond // 1000,
    }
    #eklediklerim
    try:
        validate(server_time,schema=schema_time)
        return server_time, 200
    except ValidationError as v:
        return jsonify({"mesaj": "format hatalı"}), 400

    #return server_time, 200



@app.route("/api/qr_koordinati", methods=["GET"])
@login_required
def qr_coordinate():
    # Example qr location
    with open(ROOT_PATH / "ServerCommunication/Files/qrcode.json", 'r') as file:
        qrcode = json.load(file)

    return jsonify(qrcode), 200

#eklediklerim
schema_telemetry={"type":"object",
             "properties":{
                 "sunucusaati":{
                     "type":"object",
                     "properties":{
                          "gun":{
                              "type":"integer"
                          },
                          "saat":{
                              "type":"integer"
                          },
                          "dakika":{
                              "type":"integer"
                          },
                          "saniye":{
                              "type":"integer"
                          },
                          "milisaniye":{
                              "type":"integer"
                          }
                     },
                     "required":["gun","saat","dakika","saniye","milisaniye"]
                 },
                 "KonumBilgileri":{
                     "type":"array",
                     "items":{
                         "type":"object",
                         "properties":{
                             "takim_numarası":{
                                 "type":"integer"
                             },
                             "iha_enlem":{
                                 "type":"number"
                             },
                             "iha_boylam":{
                                 "type":"number"
                             },
                             "iha_irtifa":{
                                 "type":"number"
                             },
                             "iha_yonelme":{
                                 "type":"number",
                                 "minimum":"-180",
                                 "maximum":"180"
                             },
                             "iha_yatiş":{
                                 "type":"number",
                                 "minimum":"-180",
                                 "maximum":"180"
                             },
                             "iha_hizi":{
                                 "type":"number"
                             },
                             "zaman_farki":{
                                 "type":"integer"
                             }     
                         },
                         "required":["takim_numarasi","iha_enlem","iha_boylam","iha_irtifa","iha_dikilme","iha_yonelme","iha_yatis","iha_hizi","zaman_farki"]
                         
                     }
                 }
                
             },
             "required": ["konumBilgileri"]           
}

@app.route("/api/telemetri_gonder", methods=["GET", "POST"])
@login_required
def uav_info():
    now = datetime.now()
    server_time = {
        "gun": now.day,
        "saat": now.hour,
        "dakika": now.minute,
        "saniye": now.second,
        "milisaniye": now.microsecond // 1000,
    }

    if request.method == "POST":
        incoming_telemetry = request.get_json()
        if not incoming_telemetry:
            return jsonify({"hata": "Geçersiz telemetri verisi"}), 400 #format doğrulama ✅
        """else:
            try:
                validate(incoming_telemetry,schema=schema_telemetry)
                return jsonify({"mesaj":"teletmri formatı doğrulandı"}),200
            except ValidationError as v:
                return jsonify({"hata": "Geçersiz telemetri verisi"}), 400"""

        
        mavlink_connection = get_mavlink_connection()
        mavlink_connection.wait_heartbeat() 
        msg = mavlink_connection.recv_match(type='GLOBAL_POSITION_INT', blocking=True)
        msg2 = mavlink_connection.recv_match(type='ATTITUDE', blocking=True)
        msg3 = mavlink_connection.recv_match(type='VFR_HUD', blocking=True)

        lat = msg.lat / 1e7
        lon = msg.lon / 1e7
        alt = msg.relative_alt * 1e-3

        yonelme = math.degrees(msg2.yaw)

        payload = {
            "sunucusaati": server_time,
            "konumBilgileri": [
                {
                    "takim_numarasi": 1,
                    "iha_enlem": lat,
                    "iha_boylam": lon,
                    "iha_irtifa": alt,
                    "iha_dikilme": math.degrees(msg2.pitch),
                    "iha_yonelme": ((yonelme + 360) % 360),
                    "iha_yatis": math.degrees(msg2.roll),
                    "iha_hizi": msg3.airspeed,
                    "zaman_farki": 93,
                }
            ]
        }
        #eklediklerim
        try:
            validate(payload,schema=schema_telemetry)
            validate(incoming_telemetry,schema=schema_telemetry)
            return jsonify({"mesaj":"teletmri formatı doğrulandı"}),200 ,jsonify(payload), 200
        except ValidationError as v:
            return jsonify({"mesaj": "format hatalı"}), 400
        
        
        
        #return jsonify(payload), 200
    

    if request.method == "GET":
        return jsonify({"hata": "Geçersiz istek"}), 400
    # istek doğrulama ✅

    return jsonify(""), 400 

#eklediklerim
schema_kilitlenme={
    "type":"object",
    "properties":{
        "kilitlenme":{
             "type":"integer"
        }
    },
    "required": ["kilitlenme"]   
}

@app.route("/api/kilitlenme_bilgisi", methods=["POST"])
@login_required
def locking_info():
    #eklediklerim
    msg4 = mavlink_connection.recv_match(type='MISSION_ITEM', blocking=True)
    if msg4.target is not None: 
        kilitlenme=1
    else:
        kilitlenme=0

    kilitlenme={
        "kilitlenme":kilitlenme
    }
    try:
        validate(kilitlenme,schema=schema_kilitlenme)
        return jsonify({"mesaj": "Kilitenme verisi alındı"}), 200
    except ValidationError as v:
        return jsonify({"mesaj": "format hatalı"}), 400
    
    ##msg5 = mavlink_connection.recv_match(type='COMMAND_LONG', blocking=True),komut = msg5.command=="kilitlenme" eğer bundan kilitlenme komutu geldiyse kilitlenme durumu kontrolü bununla da sağlanabilir
    
    #return jsonify({"mesaj": "Kilitenme verisi alındı"}), 200


@app.route("/api/kamikaze_bilgisi", methods=["POST"])
@login_required
def dive_info():
    ##qr kod okunmuş mu onu kontrol edip okunmuşsa bu kısım pozitif dönmeli,dalış açısı ve çıkış açısı kontolü (pitch=-90-dalış,pitch=90-çıkış)(roll 0 olmalı çünkü dalış ve çıkışta uçağın düz olması beklenir)(yaw 0 genelde sabit kalır çünkü bu hareketler esnasında yatay yönelim değişmez),kamikaze başarılı olduysa veri aktarılır bu sırada da json format kontrolü yapılır.
    ##msg = mavlink_connection.recv_match(type='GLOBAL_POSITION_INT', blocking=True) msg2 = mavlink_connection.recv_match(type='ATTITUDE', blocking=True)-> mavlink üzerinden ulaşılacak veriler.
    return jsonify({"mesaj": "Kamikaze verisi alındı"}), 200


@app.route("/api/hss_koordinatlari", methods=["GET"])
@login_required
def get_airdefences():
    with open(ROOT_PATH / "ServerCommunication/Files/airdefences.json", "r") as file:
        airdefences = json.load(file)
    return jsonify(airdefences), 200
##try except blokları ile format kontrolü yapılmalı
##bu koordinatların dışına çıkılıp çıkılmadıını,çıkıldığında ne kadar orada ne kadar kaldığını hesaplamalıyız(ama sanırım bunu "post" metodu ile açtığımız bir endpoint üzerinden yapmalıyız)



# region Error Handling


@app.errorhandler(404)
def not_found(error):
    ##URL karşılaştırması yapılmalı
    return jsonify({"hata": "Hatalı URL"}), 404


@app.errorhandler(403)
def forbidden(error):
    return jsonify({"hata": "Yetkisiz erisim denemesi"}), 403


@app.errorhandler(500)
def internal_server_error(error):
    return jsonify({"hata": "Sunucu ici hata"}), 500





# endregion

# flask --app flask_server run
