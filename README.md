# 🛡️ Autonomous Agentic AI Wildfire Operations Command Center

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.57-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Machine Learning](https://img.shields.io/badge/Ensemble-Stacking%20(0.904%20F1)-10b981)](https://scikit-learn.org/)
[![Status](https://img.shields.io/badge/Status-Operational-brightgreen)](#)

An end-to-end **Agentic AI & Machine Learning Wildfire Prediction and Emergency Command System** for the Kelowna & Okanagan region. It combines a high-precision **Stacking Ensemble ML model (0.904 F1-Score)** with an autonomous **Multi-Agent Swarm** that monitors weather telemetry, calculates spatial Rothermel flame spread vectors, deploys aerial & ground squadrons autonomously, and provides a natural-language Incident Copilot with tool-calling capabilities.

---

## 🌟 Key Highlights

* **🧠 Multi-Agent Autonomous Swarm:**
  * **Sentinel Perception Agent:** 24x7 telemetry monitoring across 36 spatial sectors with compound threat anomaly detection.
  * **Fire Spread Strategist:** Physical Rothermel flame propagation calculus on a 6x6 spatial grid to forecast downwind vulnerable sectors and Rate of Spread (ROS).
  * **Autonomous Dispatcher:** Deploys tactical assets (CL-415 Water Bombers, Bell 412 Helitack bucketing, Bulldozer firebreaks, FLIR Recon Drones) and establishes evacuation perimeters without human bottlenecks.
  * **Incident Commander Copilot:** Natural-language conversational AI equipped with tool-calling functions (`tool_get_sector_status`, `tool_simulate_wind_shift`, `tool_dispatch_custom_unit`).
* **🏆 State-of-the-Art ML Stacking:**
  * Base Level-0: Random Forest, CatBoost, XGBoost, Extra Trees.
  * Level-1 Meta-Classifier: Logistic Regression trained on Out-Of-Fold (OOF) cross-validation predictions.
  * **0.904 F1-Score** and **0.910 ROC-AUC** on unseen temporal test quarters.
* **🚨 Multi-Channel Alert Delivery:**
  * Real-time automated email alerts via Google SMTP protocol.
  * Emergency audio siren (`siren.mp3`) trigger upon high threat detection.
  * Windows native desktop notification toasts.
  * Immutable JSON incident audit trail (`incident_dispatch_log.json`).

---

## 📊 Model Benchmark

| Model Architecture | Type | F1 Score | ROC-AUC | Status |
|---|---|---|---|---|
| **Ensemble Stacking (Meta-Model)** | Level-1 Meta Classifier | **0.904** | **0.910** | 🏆 **WINNER (Deployed)** |
| **Ensemble Weighted (Genetic Algo)** | Evolutionary Optimization | 0.882 | 0.910 | Evaluated |
| **Random Forest (RF)** | Base Tree Ensemble | 0.765 | 0.892 | Level-0 Base |
| **CatBoost (CAT)** | Gradient Boosting | 0.760 | 0.895 | Level-0 Base |
| **XGBoost (XGB)** | Gradient Boosting | 0.753 | 0.887 | Level-0 Base |
| **Extra Trees (ET)** | Randomized Trees | 0.752 | 0.881 | Level-0 Base |

---

## 📸 Screenshots Showcase

All high-resolution outputs are available in the [`outputs_screenshots/`](outputs_screenshots/) directory:

| Screenshot | Description |
|---|---|
| `01_Agentic_Dashboard_Overview.png` | Command Center Overview with live Folium sector grid and flame trajectory arrows. |
| `02_Multi_Agent_Reasoning_Feed.png` | Live Multi-Agent Chain-of-Thought logs (Sentinel, Spread Physics, Dispatch). |
| `03_Incident_Commander_Copilot_Chat.png` | Interactive Tool-Using AI Copilot chatting with Commander. |
| `04_Autonomous_Fleet_Dispatch_Matrix.png` | Tactical fleet deployment table and evacuation zones. |
| `05_ML_Ensemble_Model_Comparison.png` | In-dashboard benchmark comparison showing Stacking Ensemble superiority. |
| `06_Model_F1_Score_Comparison_BarChart.png` | High-res bar chart comparing F1-scores. |
| `07_Model_ROC_AUC_Score_Comparison_BarChart.png` | High-res bar chart comparing ROC-AUC scores. |

---

## 🚀 Quickstart Guide

### 1. Installation
Clone the repository and install required dependencies:
```bash
git clone https://github.com/amanluthra001/Wild-Fire-Prediction.git
cd Wild-Fire-Prediction
pip install -r libs.txt
```

### 2. Configure Environment (`.env`)
Create a `.env` file from `.env.example`:
```env
EMAIL_USER=your_email@gmail.com
EMAIL_PASS=your_16_character_google_app_password
EMAIL_TO=recipient_alert_email@gmail.com
OWM_API_KEY=your_openweathermap_api_key_here
```

### 3. Launch the Command Center
Run the main Streamlit application:
```bash
streamlit run agentic_dashboard.py
```

### 4. Retrain Models (Optional)
To retrain the complete ML ensemble from scratch:
```bash
python wildfire_predictor_optimized.py
```

---

## 📁 Repository Structure

```text
├── agentic_dashboard.py              # Main Cyber-Tactical Command Center
├── wildfire_agents.py                # Autonomous Multi-Agent Swarm Framework
├── wildfire_predictor_optimized.py   # ML Training, Stacking & GA Optimization
├── test_agentic.py                   # Verification suite for Multi-Agent logic
├── check_alerts.py                   # Multi-channel alert & siren test script
├── dataset.csv                       # Historical wildfire & meteorological dataset
├── kelowna_regions2/                 # 36-sector GeoJSON spatial boundaries
├── models2/                          # Trained .pkl models & ensemble artifacts
├── results_opt/                      # Validation metrics, logs & plots
├── outputs_screenshots/              # High-resolution screenshots of all views
├── libs.txt                          # Python dependencies
├── .env.example                      # Environment variables template
└── README.md                         # Project documentation
```

---

## 📜 License
Developed for Academic & Wildfire Prevention Operations. All rights reserved.
