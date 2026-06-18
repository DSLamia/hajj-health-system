from flask import Flask, jsonify, request, render_template, redirect, url_for, session
from flask_cors import CORS
import pandas as pd
import requests
from supabase import create_client, Client
import os
import time

app = Flask(__name__)
CORS(app)

app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'mecca_secure_health_key_2026')

SUPABASE_URL = "https://rmpmbnmmgxsbxcvcbkwb.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJtcG1ibm1tZ3hzYnhjdmNia3diIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzE3ODcwMzgsImV4cCI6MjA4NzM2MzAzOH0.Piu2jTOwdfihFgEsELJyTHXChGgV95abKAy4-9lsAHc"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

WEATHER_API_KEY = "0aac0c7a97816848748a258ddcb625b0"


@app.route('/')
def index():
    return render_template('Untitled 4.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        input_user = request.form.get('username')
        input_pass = request.form.get('password')

        try:
            user_query = supabase.table('users_auth').select('*').eq('username', input_user).execute()

            if user_query.data and len(user_query.data) > 0:
                user_record = user_query.data[0]

                if str(user_record.get('password')) == str(input_pass):
                    session['user'] = user_record.get('username')
                    session['role'] = user_record.get('role')

                    if session['role'] == 'officer':
                        return redirect(url_for('employee_dashboard'))
                    elif session['role'] == 'paramedic':
                        return redirect(url_for('emergency'))
                    else:
                        return render_template('login.html',
                                               error="⚠️ إشعار أمني: الصلاحية الممنوحة لهذا الحساب غير مدرجة بجدول الصلاحيات الطبية المعتمد.")
                else:
                    return render_template('login.html', error="🚨 بيان الدخول خاطئ: كلمة المرور المدخلة غير متطابقة.")
            else:
                return render_template('login.html',
                                       error="🚨 سجل مفقود: اسم المستخدم غير معرف ضمن قاعدة بيانات المنظومة الحالية.")

        except Exception:
            return render_template('login.html',
                                   error="🛠️ فحص الشبكة: تعذر فحص الحساب بسبب انقطاع المزامنة اللحظية مع السيرفر السحابي.")

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
    if 'user' not in session or session.get('role') != 'officer':
        return redirect(url_for('login'))
    return render_template('employee_dashboard.html')


@app.route('/pilgrim-dashboard')
def pilgrim_dashboard():
    return render_template('pilgrim_dashboard.html')


@app.route('/emergency')
def emergency():
    if 'user' not in session or session.get('role') != 'paramedic':
        return redirect(url_for('login'))
    return render_template('emrg.html')


@app.route('/api/update-task', methods=['POST'])
def update_task():
    try:
        data = request.get_json() or {}
        task_id = data.get('id')
        new_status = data.get('status')

        if not task_id or not new_status:
            return jsonify({"status": "error", "message": "المعطيات الميدانية غير مكتملة."}), 400

        try:
            result = supabase.table('emergency_team').update({"status": new_status}).eq('id', task_id).execute()
        except Exception:
            result = supabase.table('emergency_team').update({"status": new_status}).eq('emergency_id', task_id).execute()

        return jsonify({"status": "success", "updated_data": result.data})
    except Exception as e:
        return jsonify({
            "status": "error",
            "developer_message": "🚨 فشل تحديث المزامنة الميدانية داخلياً عبر الباك إند.",
            "error_details": str(e)
        }), 500


@app.route('/api/edit-report', methods=['POST'])
def edit_report():
    try:
        data = request.get_json() or {}
        report_id = data.get('id')
        readiness_level = data.get('readiness_level')
        location = data.get('location')
        description = data.get('description')
        status = data.get('status')

        if not report_id:
            return jsonify({"status": "error", "message": "معرف البلاغ مفقود."}), 400

        update_data = {}
        if readiness_level: update_data["readiness_level"] = readiness_level
        if location: update_data["location_name"] = location
        if description: update_data["description"] = description
        if status: update_data["status"] = status

        try:
            result = supabase.table('emergency_team').update(update_data).eq('id', report_id).execute()
        except Exception:
            result = supabase.table('emergency_team').update(update_data).eq('emergency_id', report_id).execute()

        return jsonify({"status": "success", "updated_data": result.data})
    except Exception as e:
        return jsonify({
            "status": "error",
            "developer_message": "🚨 فشل حفظ التعديلات الشاملة للبلاغ في قاعدة البيانات.",
            "error_details": str(e)
        }), 500

@app.route('/api/weather-proxy', methods=['GET'])
def weather_proxy():
    url = 'https://wttr.in/Mecca?format=j1'
    
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            
            current_condition = data.get('current_condition', [{}])[0]
            temp_c = float(current_condition.get('temp_C', '40'))
            wind_speed = float(current_condition.get('windspeedKmh', '12'))
            humidity = float(current_condition.get('humidity', '15'))
            
            hourly_temps = []
            weather_data = data.get('weather', [{}])[0]
            hourly_data = weather_data.get('hourly', [])
            
            if hourly_data:
                for hr in hourly_data:
                    t = float(hr.get('tempC', temp_c))
                    hourly_temps.extend([t, t, t]) 
            
            while len(hourly_temps) < 24:
                hourly_temps.append(temp_c)
                
            formatted_data = {
                "current_weather": {
                    "temperature": temp_c,
                    "windspeed": wind_speed
                },
                "hourly": {
                    "temperature_2m": hourly_temps,
                    "relativehumidity_2m": [humidity] * 24
                }
            }
            return jsonify(formatted_data)
            
    except Exception as e:
        print(f"⚠️ خطأ في معالجة بيانات السيرفر البديل: {str(e)}")
        
    return jsonify({
        "status": "error", 
        "message": "خوادم الطقس العالمية مستغرقة وقتاً أطول للاستجابة."
    }), 504
    
@app.route('/api/predict', methods=['POST'])
def predict():
    try:
        data = request.get_json() or {}
        
        raw_temp = data.get('temperature')
        raw_humidity = data.get('humidity')
        raw_wind_speed = data.get('wind_speed')

        temp = float(raw_temp) if (raw_temp is not None and str(raw_temp).strip() != '') else 32.2
        humidity = float(raw_humidity) if (raw_humidity is not None and str(raw_humidity).strip() != '') else 9.0
        wind_speed = float(raw_wind_speed) if (raw_wind_speed is not None and str(raw_wind_speed).strip() != '') else 10.0
        
        crowd_density = float(data.get('crowding_density', 1.0))
        bed_capacity = float(data.get('bed_capacity', 150.0))
        occupied_beds = float(data.get('occupied_beds', 45.0))
        target_audience = data.get('target_audience', 'officer')
        user_id = data.get('user_id')
        
        phone_number = data.get('phone_number')
        if user_id and not (len(str(user_id)) == 36 and '-' in str(user_id)):
            phone_number = user_id

        age_group_enc = 1.0
        chronic_disease = 0.0
        has_chronic = False
        disease_detail = "none"
        diet_status = "follows"

        is_valid_uuid = (user_id and len(str(user_id)) == 36 and '-' in str(user_id))
        if phone_number or is_valid_uuid:
            try:
                print(f"🔍 Searching Supabase for phone/UUID: '{phone_number or user_id}'")
                
                user_query = supabase.table('profiles').select('age_group, has_chronic, disease_detail, diet_status')
                
                if is_valid_uuid:
                    user_query = user_query.eq('user_id', str(user_id).strip())
                elif phone_number:
                    user_query = user_query.eq('phone_number', str(phone_number).strip())

                user_res = user_query.execute()
                
                print(f"📊 Supabase Raw Response Data: {user_res.data}")

                if user_res.data and len(user_res.data) > 0:
                    profile = user_res.data[0]
                    print(f"✅ Profile found successfully: {profile}")
                    
                    raw_age = str(profile.get('age_group', '')).strip()
                    if raw_age == "61+":
                        age_group_enc = 2.0
                    elif raw_age == "1-15":
                        age_group_enc = 0.0
                    else:
                        age_group_enc = 1.0

                    has_chronic = profile.get('has_chronic', False)
                    chronic_disease = 100.0 if has_chronic else 0.0
                    
                    disease_detail = str(profile.get('disease_detail', 'none')).lower().strip()
                    diet_status = str(profile.get('diet_status', 'follows')).lower().strip()
                    
                    print(f"➡️ Processed Values: age_enc={age_group_enc}, chronic={has_chronic}, disease={disease_detail}, diet={diet_status}")
                else:
                    print("❌ No profile matched in Supabase!")
                    
            except Exception as sub_e:
                print(f"🚨 Supabase Fetch Error: {str(sub_e)}")
                pass

        features_dict = {
            'Age_Group': [float(age_group_enc)],
            'Crowd_Density': [float(crowd_density)],
            'Temperature': [float(temp)],
            'Humidity': [float(humidity)],
            'Wind_Speed': [float(wind_speed)],
            'Hospitals_Count': [3.0],
            'Health_Centers_Count': [10.0],
            'Total_Bed_Capacity': [bed_capacity],
            'Staff_Count': [45.0],
            'Ambulance_Fleet_Size': [12.0],
            'Chronic_Disease_Input': [float(chronic_disease)]
        }

        input_df = pd.DataFrame(features_dict)
        from model_handler import predict_logic
        result_model = predict_logic(
            input_df=input_df, 
            target_audience=target_audience, 
            has_chronic=has_chronic, 
            disease_detail=disease_detail, 
            diet_status=diet_status,
            bed_capacity=bed_capacity,
            occupied_beds=occupied_beds
          )

        if isinstance(result_model, dict):
            heatstroke_count = int(result_model.get('heatstroke', result_model.get('heatstroke_predictions', 0)))
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
            disease_weights = {
                "heart": 4, "asthma": 3.5, "hypertension": 3, "neurological": 2.5,
                "diabetes1": 2, "diabetes2": 2, "cancer": 1.5, "hepatitis": 1,
                "rheumatism": 1, "none": 0
            }

            if has_chronic:
                p_risk_points += disease_weights.get(disease_detail, 1)

            if has_chronic and diet_status == "not_follows":
                p_risk_points += 0.25

            if age_group_enc >= 2:
                p_risk_points += 2

            if heat_level == "High" and p_risk_points >= 5:
                risk = "High"
                color = "red"
                rec = [
                    f" 🚨  درجة الحرارة ({int(temp)}°C) مرتفعة جداً وتشكل خطورة على سلامتك.",
                    "يرجى البقاء في مكان بارد وتجنب التحرك أو بذل أي مجهود بدني حالياً.",
                    "احرص على شرب السوائل بانتظام لتعويض ما يفقده الجسم.",
                    "نرجو منك التوجه لأقرب نقطة طبية فوراً في حال الشعور بأي إعياء."
                ]
            elif heat_level == "Moderate" and p_risk_points >= 3:
                risk = "Moderate"
                color = "orange"
                rec = [
                    f"⚠️ الأجواء حالياً ({int(temp)}°C) تتطلب منك أخذ الحيطة والحذر.",
                    "ننصحك باستخدام المظلة الشمسية عند الضرورة لتجنب الإجهاد الحراري.",
                    "احرص على تناول السوائل والأملاح لتعويض المجهود البدني المبذول.",
                    "يفضل تأجيل أي تحركات غير ضرورية حتى تنكسر حدة الشمس."
                ]
            else:
                risk = "Low"
                color = "green"
                rec = [
                    f"✅ المؤشرات البيئية ({int(temp)}°C) ضمن النطاق الآمن والمستقر.",
                    "يمكنك إكمال مناسكك مع الاستمرار في شرب السوائل كإجراء احترازي.",
                    "حاول أخذ فترات راحة قصيرة بين الحين والآخر للحفاظ على نشاطك.",
                    "تأكد من وجود تهوية جيدة في مكان إقامتك لضمان راحتك."
                ]
        else:
            try:
                actual_ratio = float(occupied_beds) / float(bed_capacity) if bed_capacity > 0 else 0
            except Exception:
                actual_ratio = 0

            occ_perc = int(actual_ratio * 100)
            ratio = heatstroke_count / bed_capacity if bed_capacity > 0 else 0

            if heat_level == "High" or actual_ratio >= 0.75 or ratio > 0.10:
                risk = "High"
                color = "red"
                rec = [
                    f"🚨 تحذير حرج: نسبة الإشغال الميداني ({occ_perc}%) تجاوزت حد الأمان الحرج.",
                    "مستويات الخطورة البيئية مرتفعة جداً؛ يرجى تفعيل خطة الطوارئ فوراً.",
                    "توجيه مصفوفة الدعم الطبي الإضافي لتقليل الضغط على المستشفيات الحالية."
                ]
            elif actual_ratio >= 0.50:
                risk = "Moderate"
                color = "orange"
                rec = [
                    f"⚠️ تنبيه متوسط: نسبة الإشغال الحالية ({occ_perc}%) في تصاعد مستمر.",
                    "يرجى توجيه الحجاج للمسارات الأقل كثافة وإخطار المراكز الصحية الميدانية.",
                    "رفع جاهزية الكوادر الطبية المتنقلة لاستقبال أي حالات إجهاد حراري محتملة."
                ]
            else:
                risk = "Low"
                color = "green"
                rec = [
                    f"🟢 حالة المنظومة الطبية والبيئية مستقرة تماماً وجاهزيتها متميزة.",
                    f"نسبة إشغال الأسرة الحالية هي {occ_perc}% وهي ضمن النطاق الطبيعي.",
                    "توزيع الكثافات البشرية يسير بشكل ممتاز بالتنسيق مع غرف العمليات."
                ]

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
            "developer_message": "⚠️ رصد خلل بنيوي داخلي أثناء المعالجة.",
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
            "developer_message": "🚨 فشل مزامنة البلاغ الميداني: قاعدة البيانات السحابية رفضت إدخال السجل الجديد.",
            "system_exception": str(e)
        }), 400


app = app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
