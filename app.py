from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import pandas as pd
import requests
from supabase import create_client, Client
from model_handler import predict_logic
import os

app = Flask(__name__)
CORS(app)

# إعدادات سوبابيس
SUPABASE_URL = "https://rmpmbnmmgxsbxcvcbkwb.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJtcG1ibm1tZ3hzYnhjdmNia3diIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzE3ODcwMzgsImV4cCI6MjA4NzM2MzAzOH0.Piu2jTOwdfihFgEsELJyTHXChGgV95abKAy4-9lsAHc"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

WEATHER_API_KEY = "0aac0c7a97816848748a258ddcb625b0"
FEATURES = [
    'age_group', 'total_pilgrims', 'temperature', 'humidity', 'wind_speed',
    'hospitals_count', 'health_centers_count', 'total_beds', 'staff_count',
    'ambulances', 'chronic_input'
]


def get_makkah_weather():
    url = f"https://api.openweathermap.org/data/2.5/weather?q=Mecca,SA&appid={WEATHER_API_KEY}&units=metric"
    try:
        res = requests.get(url, timeout=5).json()
        if res.get("cod") == 200:
            return res['main']['temp'], res['main']['humidity'], res['wind']['speed'] * 3.6
    except Exception as e:
        print(f"Log: External Weather API failed, using defaults. Info: {e}")
    return 22.6, 45.0, 10.0


#  ==================== مسارات واجهات المستخدم (HTML Routing) ====================

@app.route('/')
def index():
    # الصفحة الرئيسية الأولى التي يراها الزائر (بوابة الحج والتلبية التفاعلية)
    return render_template('Untitled 4.html')


@app.route('/public-weather')
def public_weather():
    # لوحة طقس مكة المكرمة العامة والتوصيات الذكية للأفراد
    return render_template('pub.html')


@app.route('/employee-dashboard')
def employee_dashboard():
    # لوحة تحكم الموظفين والمسؤولين لمتابعة الإشغالات وإرسال التنبيهات
    return render_template('employee_dashboard.html')


@app.route('/pilgrim-dashboard')
def pilgrim_dashboard():
    # لوحة تحكم وتنبؤات الحجاج الشخصية
    return render_template('pilgrim_dashboard.html')


@app.route('/emergency')
def emergency():
    # صفحة الطوارئ والإسعاف وفرق الاستجابة العاجلة
    return render_template('emrg.html')


#  ==================== مسارات المعالجة والـ APIs الخلفية ====================

@app.route('/api/predict', methods=['POST'])
def predict():
    try:
        data = request.get_json() or {}

        # 1. قراءة البيانات الجوية القادمة من الواجهة
        temp = float(data.get('temperature', 35.0))
        humidity = float(data.get('humidity', 50.0))
        wind_speed = float(data.get('wind_speed', 10.0))
        crowd_density = float(data.get('crowding_density', 1.0))

        # 2. تحديد هوية المستخدم
        phone_number = data.get('phone_number')
        user_id = data.get('user_id')

        # فئات رقمية حقيقية للمودل
        age_group = 1.0
        chronic_disease = 0.0

        # إذا الطلب جاي من واجهة حاج ومعه بيانات، نسحب بياناته الحقيقية من Supabase
        if phone_number or user_id:
            user_query = supabase.table('profiles').select('*')
            if phone_number:
                user_query = user_query.eq('phone_number', str(phone_number))
            else:
                user_query = user_query.eq('ID', str(user_id))

            user_res = user_query.execute()

            if user_res.data and len(user_res.data) > 0:
                profile = user_res.data[0]
                # تحويل العمر لفئة رقمية
                raw_age = int(profile.get('age', 35))
                age_group = 0.0 if raw_age <= 15 else (2.0 if raw_age >= 61 else 1.0)

                # تحويل المرض المزمن
                has_chronic = profile.get('chronic_diseases', False)
                chronic_disease = 100.0 if has_chronic else 0.0

        # 3. بناء المصفوفة الـ 11 الحقيقية بالترتيب للمودل
        features_dict = {
            'Age_Group': [float(age_group)],
            'Crowd_Density': [float(crowd_density)],
            'Temperature': [float(temp)],
            'Humidity': [float(humidity)],
            'Wind_Speed': [float(wind_speed)],
            'Hospitals_Count': [3.0],
            'Health_Centers_Count': [10.0],
            'Total_Bed_Capacity': [150.0],
            'Staff_Count': [45.0],
            'Ambulance_Fleet_Size': [12.0],
            'Chronic_Disease_Input': [float(chronic_disease)]
        }

        input_df = pd.DataFrame(features_dict)

        # 4. استدعاء مودل  ONNX
        from model_handler import predict_logic
        heatstroke_count = predict_logic(input_df, temp)

        # تصنيف مستوى الخطر بناءً على مخرجات المودل
        risk_level = "مستقر" if heatstroke_count < 5 else ("متوسط" if heatstroke_count < 15 else "حرج")

        return jsonify({
            "status": "success",
            "heatstroke_predictions": heatstroke_count,
            "risk_level": risk_level,
            "recommendations": f"التنبؤ الحالي يسجل {heatstroke_count} حالة إجهاد حراري محتملة في الموقع."
        })

    except Exception as main_e:
        # نطبع الخطأ في السيرفر ونرسله للواجهة
        error_msg = f"Inference Error: {str(main_e)}"
        print(f"🚨 {error_msg}")
        return jsonify({
            "status": "error",
            "message": error_msg
        }), 400  
@app.route('/api/send-report', methods=['POST'])
def send_report():
    try:
        data = request.json or {}
        report_data = {
            "location_name": data.get('location'),
            "readiness_level": data.get('type', 'General'),
            "status": "Active"
        }
        supabase.from_("emergency_team").insert(report_data).execute()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


if __name__ == '__main__':
    # تهيئة رقم المنفذ المتوافق مع خوادم الاستضافة السحابية
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)