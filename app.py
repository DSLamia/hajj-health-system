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


# 🌐 ==================== مسارات واجهات المستخدم (HTML Routing) ====================

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


# 📊 ==================== مسارات المعالجة والـ APIs الخلفية ====================

@app.route('/api/predict', methods=['POST'])
def predict():
    try:
        data = request.json or {}
        u_id = data.get('user_id', 'GUEST')
        target = data.get('target_audience', 'pilgrim')
        occ_beds = data.get('occupied_beds', 0)

        user_data = {}
        disease_name = 'none'
        diet_status = 'follows'

        # جلب الموارد الصحية الحقيقية من قاعدة البيانات
        SPECIFIC_ID = "4e13e939-e91e-4eb0-abe4-2bd111445112"
        res_query = supabase.from_("health_resources").select("*").eq("id", SPECIFIC_ID).execute()

        if res_query.data:
            resources = res_query.data[0]
        else:
            resources = {
                'total_beds': 10240, 'occupied_beds': 0, 'hospitals_count': 36,
                'health_centers_count': 192, 'staff_count': 50000, 'ambulances': 900
            }

        bed_cap = resources.get('total_beds', 10240)

        # منطق استخراج بيانات الحاج بدقة لمنع تمرير حقول فارغة للمودل
        if str(target).lower() == 'officer' or u_id == 'OFFICER-01':
            age_enc = 1
            has_chronic = False
            role = 'officer'
        else:
            role = 'pilgrim'
            user_res = supabase.from_("profiles").select("*").eq("id", u_id).execute()
            if not user_res.data:
                user_res = supabase.from_("profiles").select("*").eq("phone_number", u_id).execute()

            if user_res.data:
                user_data = user_res.data[0]
                age_map = {"1-15": 0, "16-60": 1, "61+": 2}
                age_enc = age_map.get(user_data.get('age_group'), 1)
                has_chronic = user_data.get('has_chronic', False)
                disease_name = user_data.get('disease_detail', 'none')
                diet_status = user_data.get('diet_status', 'follows')
            else:
                age_enc, has_chronic = 1, False

        # جلب بيانات الطقس الحالية
        temp, hum, wind = get_makkah_weather()
        temp = round(temp)
        chronic_input_value = 100 if has_chronic else 0

        # بناء المصفوفة الرقمية الخام مباشرة لضمان عدم تأثرها باختلاف أسماء الأعمدة
        raw_input = [
            float(age_enc),
            1800000.0,
            float(temp),
            float(hum),
            float(wind),
            float(resources.get('hospitals_count', 36)),
            float(resources.get('health_centers_count', 192)),
            float(bed_cap),
            float(resources.get('staff_count', 50000)),
            float(resources.get('ambulances', 900)),
            float(chronic_input_value)
        ]

        # تحويلها إلى DataFrame مع مطابقة الأعمدة تماماً
        input_df = pd.DataFrame([raw_input], columns=FEATURES)

        # استدعاء المودل الحقيقي وتمرير المتغيرات المطلوبة كاملة
        try:
            results = predict_logic(
                input_df,
                role,
                has_chronic=has_chronic,
                disease_detail=disease_name,
                diet_status=diet_status,
                bed_capacity=bed_cap,
                occupied_beds=occ_beds
            )
        except Exception as model_error:
            print(f"!!! MODEL LOGIC CRASHED !!! Reason: {model_error}")
            return jsonify({
                "status": "error",
                "message": f"انهار المودل داخلياً بسبب مصفوفة المدخلات: {str(model_error)}"
            }), 200

        # حفظ التنبؤ في قاعدة البيانات للرجوع التاريخي
        try:
            supabase.from_("predictions").insert({
                "user_id": str(u_id),
                "heatstroke_predicted": int(results.get('heatstroke', 0)),
                "risk_level": results.get('risk_level', 'Low'),
                "occupied_beds": int(occ_beds)
            }).execute()
        except Exception as db_err:
            print(f"Database Log: {db_err}")

        final_recommendations = results.get('recommendation', ["الوضع مستقر بالمشاعر المقدسة."])

        return jsonify({
            "status": "success",
            "results": {
                "heatstroke": results.get('heatstroke', 0),
                "risk_level": results.get('risk_level', 'Low'),
                "risk_color": results.get('risk_color', 'green'),
                "recommendation": final_recommendations,
                "recommendations": final_recommendations,
                "rec": final_recommendations,
                "graph_path": "static/report.png"
            },
            "weather": {"temp": temp, "humidity": hum}
        })

    except Exception as e:
        print(f"Critical Error in Predict Endpoint: {e}")
        return jsonify({"status": "error", "message": str(e)}), 200
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