from flask import Flask, jsonify, request, render_template, redirect, url_for, session
from flask_cors import CORS
import pandas as pd
import requests
from supabase import create_client, Client
import os

app = Flask(__name__)
CORS(app)

# مفتاح سري قوي لتأمين الجلسات (Sessions) والخصوصية
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'mecca_secure_health_key_2026')

# إعدادات سوبابيس
SUPABASE_URL = "https://rmpmbnmmgxsbxcvcbkwb.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJtcG1ibm1tZ3hzYnhjdmNia3diIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzE3ODcwMzgsImV4cCI6MjA4NzM2MzAzOH0.Piu2jTOwdfihFgEsELJyTHXChGgV95abKAy4-9lsAHc"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

WEATHER_API_KEY = "0aac0c7a97816848748a258ddcb625b0"


#  ==================== مسارات واجهات المستخدم مع التحقق الحقيقي ====================

@app.route('/')
def index():
    return render_template('Untitled 4.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        input_user = request.form.get('username')
        input_pass = request.form.get('password')

        try:
            # استعلام حقيقي من جدول المستخدمين في سوبابيس لضمان بروتوكولات الأمان والخصوصية
            user_query = supabase.table('users_auth').select('*').eq('username', input_user).execute()

            if user_query.data and len(user_query.data) > 0:
                user_record = user_query.data[0]

                # التحقق من مطابقة كلمة المرور المخزنة
                if user_record.get('password') == input_pass:
                    session['user'] = user_record.get('username')
                    session['role'] = user_record.get('role')

                    # توجيه المستخدم حسب صلاحياته المسجلة في قاعدة البيانات
                    if session['role'] == 'officer':
                        return redirect(url_for('employee_dashboard'))
                    elif session['role'] == 'paramedic':
                        return redirect(url_for('emergency'))
                    else:
                        return render_template('login.html', error="⚠️ خطأ الصلاحيات: دور المستخدم غير معرف في النظام.")
                else:
                    return render_template('login.html', error="🚨 كلمة المرور التي أدخلتها غير صحيحة.")
            else:
                return render_template('login.html', error="🚨 اسم المستخدم غير مسجل في منظومة البيانات.")

        except Exception as db_err:
            # رسالة مخصصة للمطور عند فشل جلب الاستعلام
            return render_template('login.html',
                                   error=f"🛠️ خطأ مطور: فشل الاتصال بخادم الاستيثاق بـ Supabase. تفاصيل: {str(db_err)}")

    return render_template('login.html', error=None)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/public-weather')
def public_weather():
    return render_template('pub.html')


@app.route('/employee-dashboard')
def employee_dashboard():
    # منع الدخول العشوائي لحماية الخصوصية والأمن
    if 'user' not in session or session.get('role') != 'officer':
        return redirect(url_for('login'))
    return render_template('employee_dashboard.html')


@app.route('/pilgrim-dashboard')
def pilgrim_dashboard():
    return render_template('pilgrim_dashboard.html')


@app.route('/emergency')
def emergency():
    # حماية صفحة الطوارئ مخصصة لفرق الإسعاف فقط
    if 'user' not in session or session.get('role') != 'paramedic':
        return redirect(url_for('login'))
    return render_template('emrg.html')


#  ==================== مسارات المعالجة والـ APIs الخلفية للمودل ====================

@app.route('/api/predict', methods=['POST'])
def predict():
    try:
        data = request.get_json() or {}
        temp = float(data.get('temperature', 32.2))
        humidity = float(data.get('humidity', 9.0))
        wind_speed = float(data.get('wind_speed', 10.0))
        crowd_density = float(data.get('crowding_density', 1.0))
        bed_capacity = float(data.get('bed_capacity', 150.0))
        occupied_beds = float(data.get('occupied_beds', 45.0))
        target_audience = data.get('target_audience', 'officer')
        phone_number = data.get('phone_number')
        user_id = data.get('user_id')

        age_group_enc = 1.0
        chronic_disease = 0.0
        has_chronic = False
        disease_detail = "none"
        diet_status = "follows"

        is_valid_uuid = False
        if user_id and len(str(user_id)) == 36 and '-' in str(user_id):
            is_valid_uuid = True

        if phone_number or is_valid_uuid:
            try:
                user_query = supabase.table('profiles').select('age, chronic_diseases, disease_type, diet_compliance')
                if phone_number:
                    user_query = user_query.eq('phone_number', str(phone_number))
                elif is_valid_uuid:
                    user_query = user_query.eq('pilgrim_id', str(user_id))

                user_res = user_query.execute()

                if user_res.data and len(user_res.data) > 0:
                    profile = user_res.data[0]
                    raw_age = int(profile.get('age', 35))
                    age_group_enc = 0.0 if raw_age <= 15 else (2.0 if raw_age >= 61 else 1.0)
                    has_chronic = profile.get('chronic_diseases', False)
                    chronic_disease = 100.0 if has_chronic else 0.0
                    disease_detail = str(profile.get('disease_type', 'none')).lower()
                    diet_status = str(profile.get('diet_compliance', 'follows')).lower()
            except Exception as sb_e:
                print(f"Supabase context fetch skipped safely: {sb_e}")

        features_dict = {
            'Age_Group': [float(age_group_enc)],
            'Crowd_Density': [float(crowd_density)],
            'Temperature': [float(temp)],
            'Humidity': [float(humidity)],
            'Wind_Speed': [wind_speed],
            'Hospitals_Count': [3.0],
            'Health_Centers_Count': [10.0],
            'Total_Bed_Capacity': [bed_capacity],
            'Staff_Count': [45.0],
            'Ambulance_Fleet_Size': [12.0],
            'Chronic_Disease_Input': [float(chronic_disease)]
        }

        input_df = pd.DataFrame(features_dict)
        from model_handler import predict_logic
        result_model = predict_logic(input_df, temp)

        if isinstance(result_model, dict):
            heatstroke_count = int(result_model.get('heatstroke_predictions', result_model.get('prediction', 0)))
        else:
            heatstroke_count = int(result_model)

        if temp >= 40:
            heat_level, color = "High", "red"
        elif 30 <= temp < 40:
            heat_level, color = "Moderate", "orange"
        else:
            heat_level, color = "Low", "green"

        if str(target_audience).lower() == "pilgrim":
            p_risk_points = 0
            disease_weights = {"heart": 4, "asthma": 3.5, "hypertension": 3, "diabetes1": 2, "none": 0}
            if has_chronic: p_risk_points += disease_weights.get(disease_detail, 1)
            if age_group_enc >= 2: p_risk_points += 2

            if heat_level == "High" and p_risk_points >= 5:
                risk, color = "High", "red"
                rec = ["🚨 خطورة حرجة على سلامتك نظراً لارتفاع مؤشر الخطورة الحراري."]
            else:
                risk, color = "Low", "green"
                rec = ["✅ المؤشرات البيئية مستقرة وضمن الحدود الآمنة للحركة البنائية للنسك."]
        else:
            actual_ratio = float(occupied_beds) / float(bed_capacity) if bed_capacity > 0 else 0
            occ_perc = int(actual_ratio * 100)
            if heat_level == "High" or actual_ratio >= 0.75:
                risk, color = "High", "red"
                rec = [f"🚨 تحذير ديفلوبر: القدرة الاستيعابية حرجة جداً الإشغال الحالي {occ_perc}%."]
            else:
                risk, color = "Low", "green"
                rec = [f"🟢 حالة الأنظمة والجاهزية مستقرة الإشغال الحالي {occ_perc}%."]

        return jsonify({
            "status": "success",
            "heatstroke_predictions": heatstroke_count,
            "risk_level": risk,
            "risk_color": color,
            "recommendations": rec
        })
    except Exception as main_e:
        return jsonify({
            "status": "error",
            "developer_message": "⚠️ تم رصد خطأ داخلي أثناء معالجة بيانات مصفوفة الإدخال، تأكدي من تطابق أبعاد المصفوفة (11 Features).",
            "error_details": str(main_e)
        }), 500


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
        return jsonify({
            "status": "error",
            "developer_message": "🚨 فشل المطور في معالجة إرسال السجل الجديد إلى قاعدة البيانات المزامنة.",
            "system_exception": str(e)
        }), 400


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)