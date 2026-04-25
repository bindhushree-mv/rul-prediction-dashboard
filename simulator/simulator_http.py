import time
import json
import requests
import pandas as pd
import joblib
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "../data")
MODEL_DIR = os.path.join(os.path.dirname(__file__), "../model")
BACKEND_URL = "http://localhost:8000/ingest"
SLEEP_SECONDS = 0.5
RUL_CAP = 125

print("Loading model...", flush=True)
model = joblib.load(os.path.join(MODEL_DIR, "rul_model.joblib"))
feature_cols = joblib.load(os.path.join(MODEL_DIR, "feature_cols.joblib"))
print("Loading test data...", flush=True)
test_df = pd.read_csv(os.path.join(DATA_DIR, "test_processed.csv"))
test_df = test_df.sort_values(["unit", "cycle"]).reset_index(drop=True)
print(f"Streaming {len(test_df)} rows every {SLEEP_SECONDS}s", flush=True)

for idx, row in test_df.iterrows():
    try:
        unit_id = int(row["unit"])
        cycle = int(row["cycle"])
        features = pd.DataFrame([row[feature_cols].values], columns=feature_cols)
        rul_pred = float(model.predict(features)[0])
        rul_pred = round(max(0, min(rul_pred, RUL_CAP)), 2)
        sensor_data = {k: round(float(v), 4) for k, v in row.items() if k.startswith("s")}
        payload = {
            "unit_id": unit_id,
            "cycle": cycle,
            "predicted_RUL": rul_pred,
            "sensors": sensor_data,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
        r = requests.post(BACKEND_URL, json=payload, timeout=5)
        status = "OK" if r.status_code == 200 else f"FAIL {r.status_code}"
        print(f"Unit {unit_id} | Cycle {cycle} | RUL: {rul_pred} | {status}", flush=True)
        time.sleep(SLEEP_SECONDS)
    except KeyboardInterrupt:
        break
    except Exception as e:
        print(f"Error: {e}", flush=True)
        time.sleep(SLEEP_SECONDS)
