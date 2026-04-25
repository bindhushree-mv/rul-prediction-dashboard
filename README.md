Jet Engine RUL Prediction Dashboard
A full-stack, cloud-deployed predictive maintenance system that uses machine learning to predict Remaining Useful Life (RUL) of jet engines in real time. Built on the NASA CMAPSS FD001 benchmark dataset.

Project overview
A Python simulator reads NASA jet engine sensor data row by row and publishes it to a FastAPI backend every 5 seconds — simulating a real factory machine streaming live telemetry. A trained Random Forest model predicts how many cycles remain before engine failure. The prediction flows through a FastAPI WebSocket server to a React dashboard that updates in real time, showing live sensor charts, a RUL countdown gauge, and a critical alert log.

Demo
Normal operation — engine healthy
Show Image
Critical alert — engine failure imminent
Show Image
Live demo video: [YouTube link]

Architecture

NASA CMAPSS CSV
      |
      v
Python simulator (reads row-by-row, predicts RUL)
      |
      v
FastAPI backend (HTTP ingestion + WebSocket broadcast)
      |
      v
React dashboard (live charts, RUL gauge, alerts)
      |
      v
AWS SNS (email alerts when RUL < 30 cycles)

All components run on a single AWS EC2 t2.micro instance (free tier), served via Nginx on port 80.

Model performance
MetricValueAlgorithmRandom Forest RegressorDatasetNASA CMAPSS FD001Training engines80 unitsValidation engines20 unitsValidation RMSE19.81 cyclesValidation MAE14.60 cyclesValidation R squared0.7697RUL cap125 cyclesRolling window30 cycles
RMSE of 19.81 is competitive with published academic results on CMAPSS FD001 (typical research range: 13 to 25 cycles).

Tech stack
LayerTechnologyML modelscikit-learn RandomForestRegressorFeature engineeringpandas, numpy (rolling mean/std, MinMaxScaler)SimulatorPython (HTTP POST to backend)Backend APIFastAPI, Uvicorn, WebSocketsAlert systemAWS SNSFrontendReact, Recharts, ViteWeb serverNginx (reverse proxy)DeploymentAWS EC2 Ubuntu 24.04Data storageIn-memory (deque, capped at 100 readings)

Dataset
NASA CMAPSS FD001 (Commercial Modular Aero-Propulsion System Simulation)

100 jet engine units, each run to failure
21 sensor readings per cycle (temperature, pressure, RPM, etc.)
1 operating condition, 1 fault mode
Training set: 20,631 rows
Test set: 13,096 rows
Source: https://www.nasa.gov/content/prognostics-center-of-excellence-data-set-repository


Feature engineering

RUL labelling - calculated as max_cycle - current_cycle per engine, capped at 125
Constant sensor removal - dropped s1, s10, s18, s19, op3 (zero variance)
Rolling window features - 30-cycle rolling mean and std for each sensor
Normalisation - MinMaxScaler fitted on training data, applied to test data
Train/validation split - by engine unit (not random) to prevent data leakage


Project structure
rul-prediction-dashboard/
- notebooks/
  - phase1_exploration.ipynb
  - phase2_feature_engineering.ipynb
  - phase3_model_training.ipynb
- model/
  - rul_model.joblib
  - scaler.joblib
  - feature_cols.joblib
- simulator/
  - simulator_http.py
- backend/
  - main.py
- frontend/
  - dashboard/
    - src/App.jsx
    - package.json
- README.md
- .gitignore

How to run locally
Prerequisites

Python 3.11 or higher
Node.js 20 or higher
4GB RAM minimum

1. Clone the repository
bashgit clone https://github.com/YOUR_USERNAME/rul-prediction-dashboard.git
cd rul-prediction-dashboard
2. Set up Python environment
bashpython -m venv venv
source venv/bin/activate
pip install pandas numpy scikit-learn matplotlib seaborn joblib fastapi uvicorn websockets boto3 requests
On Windows use venv\Scripts\activate instead of source venv/bin/activate.
3. Download NASA CMAPSS data
Download from https://www.kaggle.com/datasets/behrad3d/nasa-cmaps and place these files in data/:
train_FD001.txt
test_FD001.txt
RUL_FD001.txt
4. Run the notebooks in order

notebooks/phase1_exploration.ipynb - Loads and cleans data
notebooks/phase2_feature_engineering.ipynb - Creates features
notebooks/phase3_model_training.ipynb - Trains the model

This produces model/rul_model.joblib - the trained model.
5. Start the backend
bashpython backend/main.py
Backend runs on http://localhost:8000 with API docs at /docs.
6. Start the simulator (new terminal)
bashpython simulator/simulator_http.py
7. Start the frontend (new terminal)
bashcd frontend/dashboard
npm install
npm run dev
Open http://localhost:5173

API endpoints
EndpointMethodPurpose/GETHealth check/healthGETSystem status (clients, readings, alerts)/latestGETMost recent sensor reading/history?limit=100GETLast N readings/alertsGETAll critical alerts fired/statusGETFull system status/ingestPOSTReceives data from simulator/ws/streamWebSocketLive updates to dashboard

Key findings

Sensors s11, s12, s4, s7 showed the strongest degradation trends and highest feature importance
Rolling window features (30-cycle mean/std) improved RMSE by approximately 15 percent over raw sensor values
Capping RUL at 125 cycles significantly reduced prediction error in early healthy cycles
Random Forest outperformed a linear baseline (RMSE ~35) by 44 percent


Engineering decisions and trade-offs

Random Forest over LSTM - chosen as a strong interpretable baseline. Published research shows LSTMs achieve approximately 13 to 15 RMSE; future work could close this gap.
HTTP simulator over MQTT - simpler architecture for portfolio scope; production version would use AWS IoT Core.
In-memory storage - sufficient for 100-reading window; production would use TimescaleDB or InfluxDB.
Single EC2 instance - acceptable for portfolio; production would use auto-scaling and load balancing.


Future work

Train on FD002, FD003, FD004 sub-datasets for multi-condition generalisation
Implement LSTM model to capture longer temporal dependencies
Add SHAP values for per-prediction explainability
Deploy model to AWS SageMaker real-time inference endpoint
Add user authentication and HTTPS via Let's Encrypt
Replace HTTP simulator with full AWS IoT Core MQTT pipeline
Add data drift detection on incoming sensor distributions


References

Saxena, A. et al. (2008). Damage Propagation Modeling for Aircraft Engine Run-to-Failure Simulation. PHM Conference.
NASA Ames Prognostics Data Repository: https://www.nasa.gov/content/prognostics-center-of-excellence-data-set-repository
