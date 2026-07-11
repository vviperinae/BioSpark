from flask import Flask, render_template, jsonify
from datetime import datetime

app = Flask(__name__)

# Pre-loaded fake sensor data
sensor_data = [
    {"date": "2026-07-03", "label": "03 Jul", "temp": 32.63, "methane": 88,  "status": "Not Ready"},
    {"date": "2026-07-06", "label": "06 Jul", "temp": 31.0,  "methane": 127, "status": "Building"},
    {"date": "2026-07-09", "label": "09 Jul", "temp": 31.5,  "methane": 198, "status": "Building"},
    {"date": "2026-07-12", "label": "12 Jul", "temp": 30.8,  "methane": 310, "status": "Good"},
    {"date": "2026-07-15", "label": "15 Jul", "temp": 30.5,  "methane": 398, "status": "Good"},
]

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/data")
def get_data():
    return jsonify({
        "readings": sensor_data,
        "latest": sensor_data[-1],
        "retrieved_at": datetime.now().strftime("%d %b %Y, %H:%M:%S"),
        "source": "SD Card",
        "power": "Powerbank"
    })

if __name__ == "__main__":
    app.run(debug=False)
