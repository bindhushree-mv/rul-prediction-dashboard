# ============================================================
# PHASE 4 — RUL Simulator
# Reads CMAPSS test data row by row, predicts RUL using the
# trained model, and publishes to AWS IoT Core every 5 seconds
# ============================================================

import time
import json
import pandas as pd
import numpy as np
import joblib
import os
from awscrt import mqtt
from awsiot import mqtt_connection_builder

# ── Configuration ────────────────────────────────────────────
ENDPOINT       = "a1rk7akocxg5n0-ats.iot.us-east-1.amazonaws.com"
CLIENT_ID      = "jet-engine-simulator"
TOPIC          = "engines/FD001/telemetry"
ALERT_TOPIC    = "engines/FD001/alerts"
CERT_DIR       = os.path.join(os.path.dirname(__file__), "certs")
CA_PATH        = os.path.join(CERT_DIR, "AmazonRootCA1.pem")
CERT_PATH      = os.path.join(CERT_DIR, "certificate.pem.crt")
KEY_PATH       = os.path.join(CERT_DIR, "private.pem.key")
MODEL_DIR      = os.path.join(os.path.dirname(__file__), "../model")
DATA_DIR       = os.path.join(os.path.dirname(__file__), "../data")
RUL_CAP        = 125
ALERT_THRESHOLD = 30
SLEEP_SECONDS  = 5

# ── Load model and feature list ───────────────────────────────
print("Loading model and scaler...")
model        = joblib.load(os.path.join(MODEL_DIR, "rul_model.joblib"))
scaler       = joblib.load(os.path.join(MODEL_DIR, "scaler.joblib"))
feature_cols = joblib.load(os.path.join(MODEL_DIR, "feature_cols.joblib"))
print("✅ Model loaded")

# ── Load and prepare test data ────────────────────────────────
print("Loading test data...")
test_df = pd.read_csv(os.path.join(DATA_DIR, "test_processed.csv"))
test_df = test_df.sort_values(['unit', 'cycle']).reset_index(drop=True)
test_df = test_df.sort_values(['unit', 'cycle']).reset_index(drop=True)
print(f"✅ Test data loaded: {test_df.shape}")

# ── MQTT connection callbacks ─────────────────────────────────
def on_connection_interrupted(connection, error, **kwargs):
    print(f"Connection interrupted: {error}")

def on_connection_resumed(connection, return_code, session_present, **kwargs):
    print(f"Connection resumed: return_code={return_code}")

# ── Connect to AWS IoT Core ───────────────────────────────────
print("Connecting to AWS IoT Core...")

mqtt_connection = mqtt_connection_builder.mtls_from_path(
    endpoint=ENDPOINT,
    cert_filepath=CERT_PATH,
    pri_key_filepath=KEY_PATH,
    ca_filepath=CA_PATH,
    client_id=CLIENT_ID,
    on_connection_interrupted=on_connection_interrupted,
    on_connection_resumed=on_connection_resumed,
    clean_session=False,
    keep_alive_secs=30
)

connect_future = mqtt_connection.connect()
connect_future.result()
print("✅ Connected to AWS IoT Core!")
print(f"   Publishing to topic: {TOPIC}")
print(f"   Alert topic        : {ALERT_TOPIC}")
print(f"   Interval           : every {SLEEP_SECONDS} seconds")
print(f"   Alert threshold    : RUL < {ALERT_THRESHOLD} cycles")
print("-" * 55)

# ── Stream rows one by one ────────────────────────────────────
alert_sent = set()   # track which engines already got an alert

for idx, row in test_df.iterrows():
    try:
        unit_id = int(row['unit'])
        cycle   = int(row['cycle'])

        # Build feature vector for prediction
        features = pd.DataFrame([row[feature_cols].values], columns=feature_cols)

        # Predict RUL
        rul_pred = float(model.predict(features)[0])
        rul_pred = round(max(0, min(rul_pred, RUL_CAP)), 2)

        # Build payload
        sensor_data = {
            k: round(float(v), 4)
            for k, v in row.items()
            if k.startswith('s')
        }

        payload = {
            "unit_id"       : unit_id,
            "cycle"         : cycle,
            "predicted_RUL" : rul_pred,
            "alert"         : rul_pred < ALERT_THRESHOLD,
            "timestamp"     : time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                            time.gmtime()),
            "sensors"       : sensor_data
        }

        # Publish telemetry
        mqtt_connection.publish(
            topic   = TOPIC,
            payload = json.dumps(payload),
            qos     = mqtt.QoS.AT_LEAST_ONCE
        )

        print(f"  Unit {unit_id:>3} | Cycle {cycle:>4} | "
              f"RUL: {rul_pred:>6.1f} cycles | "
              f"{'⚠️  ALERT' if rul_pred < ALERT_THRESHOLD else '✅ OK'}")

        # Publish alert if RUL is critically low
        if rul_pred < ALERT_THRESHOLD and unit_id not in alert_sent:
            alert_payload = {
                "unit_id"       : unit_id,
                "predicted_RUL" : rul_pred,
                "message"       : f"Engine {unit_id} critical — only {rul_pred} cycles remaining!",
                "timestamp"     : time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                                time.gmtime())
            }
            mqtt_connection.publish(
                topic   = ALERT_TOPIC,
                payload = json.dumps(alert_payload),
                qos     = mqtt.QoS.AT_LEAST_ONCE
            )
            alert_sent.add(unit_id)
            print(f"  🚨 ALERT published for Engine {unit_id}!")

        time.sleep(SLEEP_SECONDS)

    except KeyboardInterrupt:
        print("\n⛔ Simulator stopped by user")
        break
    except Exception as e:
        print(f"  ❌ Error on row {idx}: {e}")
        continue

# ── Disconnect ────────────────────────────────────────────────
print("\nDisconnecting...")
disconnect_future = mqtt_connection.disconnect()
disconnect_future.result()
print("✅ Disconnected cleanly")
