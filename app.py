from flask import Flask, render_template, jsonify
from datetime import datetime

app = Flask(__name__)

sensor_data = [
    {"date": "2026-07-03", "label": "03 Jul", "temp": 32.63, "methane": 88,  "status": "Not Ready", "phase": "Lag Phase"},
    {"date": "2026-07-06", "label": "06 Jul", "temp": 31.0,  "methane": 127, "status": "Building",  "phase": "Lag Phase"},
    {"date": "2026-07-09", "label": "09 Jul", "temp": 31.5,  "methane": 198, "status": "Building",  "phase": "Active Digestion"},
    {"date": "2026-07-12", "label": "12 Jul", "temp": 30.8,  "methane": 310, "status": "Good",      "phase": "Active Digestion"},
    {"date": "2026-07-15", "label": "15 Jul", "temp": 30.5,  "methane": 398, "status": "Good",      "phase": "Active Digestion"},
]

sd_log = []
import random
random.seed(42)
base_time = 0
for d in sensor_data:
    for hour in [8, 11, 14, 17, 20]:
        sd_log.append({
            "time_s": base_time + hour * 3600,
            "date": d["label"],
            "hour": f"{hour:02d}:00",
            "temp": round(d["temp"] + random.uniform(-0.4, 0.4), 2),
            "methane": d["methane"] + random.randint(-8, 8),
        })
    base_time += 86400 * 3

@app.route("/")
def index():        return render_template("index.html")

@app.route("/analytics")
def analytics():    return render_template("analytics.html")

@app.route("/twin")
def twin():         return render_template("twin.html")

@app.route("/sdlog")
def sdlog():        return render_template("sdlog.html")

@app.route("/power")
def power():        return render_template("power.html")

@app.route("/api/data")
def get_data():
    return jsonify({
        "readings": sensor_data,
        "latest": sensor_data[-1],
        "retrieved_at": datetime.now().strftime("%d %b %Y, %H:%M:%S"),
        "source": "SD Card", "power": "Powerbank"
    })

@app.route("/api/sdlog")
def get_sdlog():
    return jsonify({"log": sd_log, "total": len(sd_log)})

if __name__ == "__main__":
    app.run(debug=False)
