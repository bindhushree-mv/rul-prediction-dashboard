# Predictive Maintenance Dashboard for Aircraft Engines

A real-time machine learning system that predicts when a jet engine will fail — before it actually does.

Trained on the **NASA CMAPSS FD001** benchmark dataset and deployed as a live cloud dashboard on AWS.

---

<table>
  <tr>
    <td><img src="screenshot_normal.png" alt="Healthy engine"/></td>
    <td><img src="screenshot_critical.png" alt="Critical alert"/></td>
  </tr>
  <tr>
    <td align="center"><b>Normal operation — engine healthy</b></td>
    <td align="center"><b>Critical alert — failure imminent</b></td>
  </tr>
</table>

---

## Model performance

| Metric | Value | Meaning |
|---|---|---|
| **RMSE** | 19.81 cycles | Average prediction error |
| **MAE** | 14.60 cycles | Median prediction error |
| **R²** | 0.7697 | Model explains 77% of variance |

Competitive with published academic results on CMAPSS FD001 (typical range: 13–25 cycles RMSE).

---

## How it works

NASA CMAPSS data → Python simulator → FastAPI backend → React dashboard
(sensor rows)     (predicts RUL)     (WebSocket)       (live updates)
+ SNS alerts

+ A Python simulator streams jet engine sensor data every 5 seconds. A trained Random Forest predicts the **Remaining Useful Life (RUL)** in cycles. The FastAPI backend broadcasts predictions via WebSocket to a React dashboard, and fires email alerts through AWS SNS when predicted RUL drops below 30 cycles.

---

## Tech stack

| Layer | Tools |
|---|---|
| ML | Python, scikit-learn, pandas, numpy |
| Backend | FastAPI, WebSockets, Uvicorn |
| Frontend | React, Recharts, Vite |
| Cloud | AWS EC2, AWS IoT Core, AWS SNS, Nginx |

---

## Engineering highlights

- **Engine-level train/validation split** — prevents data leakage from temporally adjacent rows
- **30-cycle rolling window features** — rolling mean and std capture degradation trends
- **RUL capping at 125 cycles** — focuses model on the actual degradation zone
- **Live WebSocket streaming** — automatic reconnection with exponential backoff

---

## How to reproduce

```bash
git clone https://github.com/bindhushree-mv/rul-prediction-dashboard.git
cd rul-prediction-dashboard

python -m venv venv && source venv/bin/activate
pip install pandas numpy scikit-learn fastapi uvicorn websockets requests joblib boto3

# Download CMAPSS data from kaggle.com/datasets/behrad3d/nasa-cmaps → place in data/

# Train the model — run notebooks in order
jupyter notebook   # phase1 → phase2 → phase3

# Start all three components (separate terminals)
python backend/main.py
python simulator/simulator_http.py
cd frontend/dashboard && npm install && npm run dev
```

Open `http://localhost:5173`

---

## Future work

- LSTM model for longer temporal dependencies
- SHAP explanations for individual RUL predictions
- Train across all four CMAPSS sub-datasets (FD001–FD004)
- Data drift detection on incoming sensor streams
- AWS SageMaker endpoint with autoscaling

---

## Reference

Saxena, A., Goebel, K., Simon, D., & Eklund, N. (2008). *Damage Propagation Modeling for Aircraft Engine Run-to-Failure Simulation.* IEEE PHM Conference.

