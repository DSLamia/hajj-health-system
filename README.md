# 🕋 Mecca Integrated Weather & Health Risk Prediction System

An advanced, AI-driven predictive health-risk framework tailored for the microclimate of Mecca and holy sites. This project bridges deep learning inference with real-time field data to predict emergency and heat-related medical loads, empowering field coordinators and pilgrims through continuous monitoring.

---

## 🚀 System Architecture & Flow

The system operates via a tightly decoupled client-server architecture designed for zero-latency inference and absolute operational integrity.

<pre>
[Pilgrim / Officer Dashboard]
       │
       │ (Real-time HTTP POST via Fetch API)
       ▼
[Flask Backend API (Render Cloud)] ──────► [Supabase DB] (Profiles & Historical Logs)
       │
       ├─► [Live Weather Sync (Open-Meteo API)]
       │
       ▼
[Feature Alignment & Scaling Pipeline (scaler.pkl)]
       │
       │ (Strict 11-Feature Tensor Vector)
       ▼
[Operational Deep Learning Inference (ONNX Runtime Engine)]
       │
       ▼
[Dynamic Risk Level Output & Tailored Preventive Protocols]
</pre>

---

## 🛠️ Key Architectural Updates (Production Deployment)

To transition this system from a local development environment to a live, production-grade cloud solution, the following enhancements were implemented:

1. **Strict 11-Feature Matrix Feeding:** Adjusted the preprocessing logical layout to handle true mathematical representations. Categorical values (such as chronic illness markers) are strictly mapped to float numbers (`100.0` or `0.0`) to match the matrix weights the ONNX model was trained on.
2. **Robust Backend Verification:** Reconfigured `app.py` to securely run parallel user identification checks (via Phone Number matching followed by unique UUID checking) ensuring database integrity before calculations take place.
3. **Elimination of Mock Placeholders:** Removed all legacy fallback statistical approximations. The inference system now natively relies 100% on pure ONNX tensor output; if a framework mismatch or asset loss occurs, the server raises a strict runtime exception rather than falsifying clinical criteria.
4. **Cloud Infrastructure Configuration:** Implemented dynamic environment porting and automated dependency management via Gunicorn engines for seamless deployment on cloud providers (Render).

---

## 📊 Feature Matrix Layout (ONNX & Scaler Alignment)

The model evaluates a rigid array of **11 specific input dimensions** structured sequentially:

| Index | Feature Parameter | Data Type | Description / Operational Context |
|---|---|---|---|
| 1 | `Age Group Encoded` | `float32` | Encoded ordinal brackets (`0` for 1-15, `1` for 16-60, `2` for 61+) |
| 2 | `Crowd Density Indicator` | `float32` | Standard dynamic baseline footprint density value |
| 3 | `Temperature` | `float32` | Real-time ambient temperature fetched dynamically per hour |
| 4 | `Humidity` | `float32` | Atmospheric relative humidity percentage |
| 5 | `Wind Speed` | `float32` | Meteorological wind tracking parameter |
| 6 | `Hospitals Count` | `float32` | Operational healthcare infrastructure capacity index |
| 7 | `Health Centers Count` | `float32` | Available clinical processing stations |
| 8 | `Total Bed Capacity` | `float32` | Max physical capacity managed under resource databases |
| 9 | `Staff Count` | `float32` | Deployed medical personnel and field emergency forces |
| 10 | `Ambulance Fleet Size` | `float32` | Mobilized emergency vehicular response units |
| 11 | `Chronic Disease Input` | `float32` | Boolean health status amplified to tensor metrics (`100.0` / `0.0`) |

---

## 📂 Project Repository Structure

* `app.py` — Core production Flask application hosting predictive endpoints and Supabase initialization wrappers.
* `model_handler.py` — Serialized asset validation module executing ONNX runtime session parsing and feature engineering scaling.
* `static/` — Production front-end asset bundles (UI stylesheets, iconography, video wrappers).
* `templates/` — Interactive portal templates (Pilgrim dashboard layouts, tactical monitoring interfaces).
* `requirements.txt` — Frozen environment deployment configuration declaring explicit dependencies (`onnxruntime`, `joblib`, `pandas`, etc.).
---

## 🎓 Academic Integrity & Transparency Statement
This repository is published as part of **Appendix E** for the formal graduation thesis documentation. It represents an audited, authentic implementation of AI applications in seasonal event logistics management.
