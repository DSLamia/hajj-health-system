import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import tensorflow as tf
import joblib
import os
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def predict_logic(input_df, role, has_chronic, disease_detail, bed_capacity, occupied_beds):
    # تحميل الموديل والسكيلر داخل الدالة فقط عند استدعائها!
    MODEL_PATH = os.path.join(BASE_DIR, 'ai_models', 'hajj_health_model.h5')
    SCALER_PATH = os.path.join(BASE_DIR, 'ai_models', 'scaler.pkl')

    model = load_model(MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)

def predict_logic(input_df, target_audience, has_chronic=False, disease_detail="none", diet_status="follows", bed_capacity=None, occupied_beds=0):
    scaled_input = scaler.transform(input_df)
    prediction = model.predict(scaled_input, verbose=0)

    heatstroke_count = int(max(0, prediction[0][0]))

    # 1. استخلاص القيم
    temp_raw = input_df.iloc[0, 2]
    hum = input_df.iloc[0, 3]

    temp = (temp_raw * 0.98) + (temp_raw * (hum / 100) * 0.02)

    temp = round(temp + 0.3, 2)

    if bed_capacity is None:
        bed_capacity = input_df.iloc[0, 7]

    age_group_enc = input_df.iloc[0, 0]

    ratio = heatstroke_count / bed_capacity if bed_capacity > 0 else 0

    # 3. تصنيف مستوى الحرارة
    if temp >= 40:
        heat_level, color = "High", "red"
    elif 30 <= temp < 40:
        heat_level, color = "Moderate", "orange"
    else:
        heat_level, color = "Low", "green"

    # 4. منطق الحجاج (Pilgrim)
    if target_audience.lower() == "pilgrim":
        p_risk_points = 0

        # توزيع النقاط على الأمراض حسب الخطورة (من 1 إلى 4)
        disease_weights = {
            "heart": 4,  # RR = 2.79
            "asthma": 3.5,  # RR = 2.09
            "hypertension": 3,  # RR = 2.01
            "neurological": 2.5,  # RR = 1.16
            "diabetes1": 2,  # RR = 1.10
            "diabetes2": 2,  # RR = 1.10
            "cancer": 1.5,
            "hepatitis": 1,
            "rheumatism": 1,
            "none": 0
        }

        if has_chronic:
            p_risk_points += disease_weights.get(disease_detail, 1)

        if has_chronic and diet_status == "not_follows":
            p_risk_points += 0.25

        if age_group_enc >= 2:
            p_risk_points += 2

        risk = "Low"
        rec = ["المؤشرات طبيعية حالياً. رافقكم السلامة."]

        # شرط الـ High Risk ( يعتمد على قوة المرض + الحرارة)
        if heat_level == "High" and p_risk_points >= 5:
            rec = [
                f" 🚨  درجة الحرارة ({int(temp)}°C) مرتفعة جداً وتشكل خطورة على سلامتك.",
                "يرجى البقاء في مكان بارد وتجنب التحرك أو بذل أي مجهود بدني حالياً.",
                "احرص على شرب السوائل بانتظام لتعويض ما يفقده الجسم.",
                "نرجو منك التوجه لأقرب نقطة طبية فوراً في حال الشعور بأي إعياء."
            ]
        # شرط الـ Moderate (يعتمد على حرارة متوسطة أو نقاط خطر متوسطة)
        elif heat_level == "Moderate" and p_risk_points >= 3:
            risk = "Moderate"
            rec = [
                f"⚠️ الأجواء حالياً ({int(temp)}°C) تتطلب منك أخذ الحيطة والحذر.",
                "ننصحك باستخدام المظلة الشمسية عند الضرورة لتجنب الإجهاد الحراري.",
                "احرص على تناول السوائل والأملاح لتعويض المجهود البدني المبذول.",
                "يفضل تأجيل أي تحركات غير ضرورية حتى تنكسر حدة الشمس."
            ]
        else:
            risk = "Low"
            rec = [
                f"✅ المؤشرات البيئية ({int(temp)}°C) ضمن النطاق الآمن والمستقر.",
                "يمكنك إكمال مناسكك مع الاستمرار في شرب السوائل كإجراء احترازي.",
                "حاول أخذ فترات راحة قصيرة بين الحين والآخر للحفاظ على نشاطك.",
                "تأكد من وجود تهوية جيدة في مكان إقامتك لضمان راحتك."
            ]
            print(f"DEBUG: Chronic={has_chronic}, Disease={disease_detail}, AgeGroup={age_group_enc}")
            print(p_risk_points)

    # 5. منطق المسؤولين (Officer)
    else:
            actual_ratio = occupied_beds / bed_capacity if bed_capacity > 0 else 0
            occ_perc = int(actual_ratio * 100)

            if heat_level == "High" or actual_ratio >= 0.75 or ratio > 0.10:
                risk = "High"
                color = "red"
                rec = [f"🚨 تحذير حرج: نسبة الإشغال ({occ_perc}%) تجاوزت الحد المسموح. مطلوب تفعيل خطة الطوارئ."]

            elif actual_ratio >= 0.50:
                risk = "Moderate"
                color = "orange"
                rec = [f"⚠️ تنبيه متوسط: نسبة الإشغال ({occ_perc}%) مرتفعة. يرجى الاستعداد لرفع الجاهزية الميدانية."]

            # الحالة (Low): إذا الإشغال أقل من 50%
            else:
                risk = "Low"
                color = "green"
                rec = [f"🟢 حالة النظام مستقرة. نسبة الإشغال الحالية: {occ_perc}%."]
    # 6. تحديث الرسم البياني
    create_dashboard(heatstroke_count, bed_capacity, risk, color)

    return {
        "heatstroke": heatstroke_count,
        "risk_level": risk,
        "risk_color": color,
        "recommendation": rec,
        "graph_path": "static/report.png"
    }

def create_dashboard(heatstroke, beds, risk, color):
    import os
    import joblib
    import pandas as pd
    import matplotlib
    matplotlib.use('Agg')  # لمنع تداخل واجهات الرسم مع السيرفر
    import matplotlib.pyplot as plt
    import seaborn as sns
    import tensorflow as tf

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    def predict_logic(input_df, target_audience, has_chronic=False, disease_detail="none", diet_status="follows",
                      bed_capacity=None, occupied_beds=0):
        # 1. تحميل الموديل والسكيلر "داخل الدالة ديناميكياً" لحماية ذاكرة السيرفر المجاني
        MODEL_PATH = os.path.join(BASE_DIR, 'ai_models', 'hajj_health_model.h5')
        SCALER_PATH = os.path.join(BASE_DIR, 'ai_models', 'scaler.pkl')

        model = tf.keras.models.load_model(MODEL_PATH)
        scaler = joblib.load(SCALER_PATH)

        # 2. تشغيل التنبؤ
        scaled_input = scaler.transform(input_df)
        prediction = model.predict(scaled_input, verbose=0)

        heatstroke_count = int(max(0, prediction[0][0]))

        # 3. استخلاص القيم والطقس معدل الحرارة
        temp_raw = input_df.iloc[0, 2]
        hum = input_df.iloc[0, 3]

        temp = (temp_raw * 0.98) + (temp_raw * (hum / 100) * 0.02)
        temp = round(temp + 0.3, 2)

        if bed_capacity is None:
            bed_capacity = input_df.iloc[0, 7]

        age_group_enc = input_df.iloc[0, 0]
        ratio = heatstroke_count / bed_capacity if bed_capacity > 0 else 0

        # 4. تصنيف مستوى الحرارة واللون الافتراضي
        if temp >= 40:
            heat_level, color = "High", "red"
        elif 30 <= temp < 40:
            heat_level, color = "Moderate", "orange"
        else:
            heat_level, color = "Low", "green"

        # 5. منطق الحجاج (Pilgrim)
        if target_audience.lower() == "pilgrim":
            p_risk_points = 0

            disease_weights = {
                "heart": 4,
                "asthma": 3.5,
                "hypertension": 3,
                "neurological": 2.5,
                "diabetes1": 2,
                "diabetes2": 2,
                "cancer": 1.5,
                "hepatitis": 1,
                "rheumatism": 1,
                "none": 0
            }

            if has_chronic:
                p_risk_points += disease_weights.get(disease_detail, 1)

            if has_chronic and diet_status == "not_follows":
                p_risk_points += 0.25

            if age_group_enc >= 2:
                p_risk_points += 2

            # شروط مستويات الخطورة للحجاج وتعديل الألوان والرسائل بناءً عليها
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
                    "يففضل تأجيل أي تحركات غير ضرورية حتى تنكسر حدة الشمس."
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
                print(f"DEBUG: Chronic={has_chronic}, Disease={disease_detail}, AgeGroup={age_group_enc}")
                print(p_risk_points)

        # 6. منطق المسؤولين (Officer)
        else:
            actual_ratio = occupied_beds / bed_capacity if bed_capacity > 0 else 0
            occ_perc = int(actual_ratio * 100)

            if heat_level == "High" or actual_ratio >= 0.75 or ratio > 0.10:
                risk = "High"
                color = "red"
                rec = [f"🚨 تحذير حرج: نسبة الإشغال ({occ_perc}%) تجاوزت الحد المسموح. مطلوب تفعيل خطة الطوارئ."]
            elif actual_ratio >= 0.50:
                risk = "Moderate"
                color = "orange"
                rec = [f"⚠️ تنبيه متوسط: نسبة الإشغال ({occ_perc}%) مرتفعة. يرجى الاستعداد لرفع الجاهزية الميدانية."]
            else:
                risk = "Low"
                color = "green"
                rec = [f"🟢 حالة النظام مستقرة. نسبة الإشغال الحالية: {occ_perc}%."]

        # 7. تحديث الرسم البياني وحفظه بصيغة أمنة للسيرفر
        create_dashboard(heatstroke_count, bed_capacity, risk, color)

        return {
            "heatstroke": heatstroke_count,
            "risk_level": risk,
            "risk_color": color,
            "recommendation": rec,
            "graph_path": "static/report.png"
        }

    def create_dashboard(heatstroke, beds, risk, color):
        plt.style.use('ggplot')
        fig, ax = plt.subplots(figsize=(8, 5))

        labels = ['Predicted Heatstrokes', 'Available Beds']
        values = [heatstroke, beds]

        sns.barplot(x=labels, y=values, hue=labels, palette=[color, '#3498db'], ax=ax, legend=False)

        plt.title(f"Heatstroke Prediction Analysis (Status: {risk})", fontsize=14)
        plt.ylabel("Count")

        static_dir = os.path.join(BASE_DIR, 'static')
        if not os.path.exists(static_dir):
            os.makedirs(static_dir)

        plt.tight_layout()
        plt.savefig(os.path.join(static_dir, 'report.png'))
        plt.close(fig)