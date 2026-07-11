from flask import Flask, render_template, jsonify, request
from datetime import datetime, timedelta
import math
import random

app = Flask(__name__)

# ── project timeline ──
# monitoring window: 29 jun 2026 to 13 jul 2026, one reading every 2 days
# 13 jul is treated as "now" for this project's demo, even if the real clock has moved on
PROJECT_START = datetime(2026, 6, 29)
PROJECT_NOW   = datetime(2026, 7, 13)

# raw values below are what the MQ-4 analog pin would report on a 0-1023 scale
# temp is the DS18B20 probe reading inside the digester in degrees C
raw_readings = [
    {"offset_days": 0,  "temp": 29.4, "raw": 88,  "phase": "Lag Phase (Hydrolysis)"},
    {"offset_days": 2,  "temp": 30.1, "raw": 98,  "phase": "Lag Phase (Hydrolysis)"},
    {"offset_days": 4,  "temp": 31.0, "raw": 145, "phase": "Acidogenesis"},
    {"offset_days": 6,  "temp": 31.6, "raw": 208, "phase": "Active Digestion"},
    {"offset_days": 8,  "temp": 32.0, "raw": 265, "phase": "Active Digestion"},
    {"offset_days": 10, "temp": 31.7, "raw": 322, "phase": "Methanogenesis (Ramping)"},
    {"offset_days": 12, "temp": 31.1, "raw": 368, "phase": "Methanogenesis (Stable)"},
    {"offset_days": 14, "temp": 30.6, "raw": 402, "phase": "Methanogenesis (Stable)"},
]

# ── mq-4 ppm calibration ──
# uses the actual mq-4 methane curve constants published by the MQUnifiedsensor
# library (github.com/miguel5612/MQSensorsLib), which digitizes the winsen MQ-4
# datasheet sensitivity graph: ppm = a * (Rs/Ro)^b, with Rs/Ro = 4.4 in clean air
#
# Ro is derived from a real clean-air baseline reading rather than assumed.
# raw values here are on the arduino uno 10-bit adc scale (0-1023) at 5v supply.
# note: RL (load resistor) cancels out of the Rs/Ro ratio entirely, so its exact
# value does not affect the ppm result, only Rs and Ro's absolute values do
PPM_CURVE_A = 1012.7
PPM_CURVE_B = -2.786
CLEAN_AIR_RATIO = 4.4
BASELINE_RAW = 88  # day 1 raw reading, used as the clean-air Ro reference
ADC_VCC = 5.0
ADC_MAX = 1023

def _relative_rs(raw):
    # (Vcc - Vout) / Vout, proportional to Rs with RL factored out
    vout = (raw / ADC_MAX) * ADC_VCC
    return (ADC_VCC - vout) / vout

_RO_RELATIVE = _relative_rs(BASELINE_RAW) / CLEAN_AIR_RATIO

def raw_to_ppm(raw):
    ratio = _relative_rs(raw) / _RO_RELATIVE
    ppm = PPM_CURVE_A * (ratio ** PPM_CURVE_B)
    return round(ppm)

def status_for_raw(raw):
    if raw < 100:
        return "Not Ready"
    if raw < 300:
        return "Building"
    return "Good"

def build_sensor_data():
    out = []
    for r in raw_readings:
        d = PROJECT_START + timedelta(days=r["offset_days"])
        out.append({
            "date": d.strftime("%Y-%m-%d"),
            "label": d.strftime("%d %b"),
            "temp": r["temp"],
            "methane": r["raw"],
            "ppm": raw_to_ppm(r["raw"]),
            "status": status_for_raw(r["raw"]),
            "phase": r["phase"],
        })
    return out

sensor_data = build_sensor_data()

# sd card raw log: 5 timestamped samples per reading day, jittered around the daily value
random.seed(42)
sd_log = []
for i, r in enumerate(raw_readings):
    day = PROJECT_START + timedelta(days=r["offset_days"])
    for hour in [6, 10, 14, 18, 22]:
        jitter_temp = round(r["temp"] + random.uniform(-0.35, 0.35), 2)
        jitter_raw  = max(0, r["raw"] + random.randint(-9, 9))
        ts = day.replace(hour=hour, minute=0, second=0)
        sd_log.append({
            "date": ts.strftime("%Y-%m-%d"),
            "label": day.strftime("%d %b"),
            "hour": f"{hour:02d}:00",
            "temp": jitter_temp,
            "methane": jitter_raw,
            "ppm": raw_to_ppm(jitter_raw),
        })

# fake powerbank telemetry, one point per sd_log timestamp
# capacity assumed 20000 mAh powerbank feeding an esp32 + ds18b20 + mq-4 + relay board
# battery percent is simulated directly: it drains a few percent per sample and gets
# topped up by the team once it runs low, which is what actually happens on site
POWERBANK_CAPACITY_MAH = 20000
AVG_DRAW_MA = 180
power_log = []
battery_pct = 98.0
for i, entry in enumerate(sd_log):
    draw = AVG_DRAW_MA + random.uniform(-15, 25)
    battery_pct -= random.uniform(1.4, 2.6)
    if battery_pct < 18:
        battery_pct = random.uniform(95, 99)  # team swaps or recharges the powerbank
    pct = round(max(0, min(100, battery_pct)), 1)
    power_log.append({
        "date": entry["date"],
        "label": entry["label"],
        "hour": entry["hour"],
        "voltage": round(4.05 + (pct / 100) * 0.95 + random.uniform(-0.03, 0.03), 2),
        "current_ma": round(draw, 1),
        "battery_pct": pct,
    })

# ── food waste to biogas calculator ──
# standard anaerobic digestion assumptions for mixed food waste, values pulled from
# typical published ranges for small scale food waste digesters
TS_FRACTION            = 0.20   # total solids as a fraction of wet feed mass
VS_FRACTION_OF_TS       = 0.85   # volatile solids as a fraction of total solids
BIOGAS_YIELD_PER_KG_VS  = 0.50   # m3 biogas per kg vs added
CH4_FRACTION            = 0.60   # methane share of biogas by volume
CH4_CALORIFIC_MJ_PER_M3 = 35.8   # energy content of methane
HRT_DAYS                = 25     # hydraulic retention time
SLURRY_LITERS_PER_KG    = 2.0    # 1:1 dilution with water by rough volume

def calculate_biogas(kg_per_day):
    ts_kg = kg_per_day * TS_FRACTION
    vs_kg = ts_kg * VS_FRACTION_OF_TS
    biogas_m3 = vs_kg * BIOGAS_YIELD_PER_KG_VS
    ch4_m3 = biogas_m3 * CH4_FRACTION
    energy_mj = ch4_m3 * CH4_CALORIFIC_MJ_PER_M3
    energy_kwh = energy_mj / 3.6
    slurry_liters_per_day = kg_per_day * SLURRY_LITERS_PER_KG
    working_volume_m3 = slurry_liters_per_day * HRT_DAYS / 1000
    headspace_ppm = round(CH4_FRACTION * 1_000_000)
    return {
        "kg_per_day": kg_per_day,
        "ts_kg": round(ts_kg, 3),
        "vs_kg": round(vs_kg, 3),
        "biogas_m3_per_day": round(biogas_m3, 3),
        "ch4_m3_per_day": round(ch4_m3, 3),
        "energy_mj_per_day": round(energy_mj, 2),
        "energy_kwh_per_day": round(energy_kwh, 2),
        "slurry_liters_per_day": round(slurry_liters_per_day, 1),
        "working_volume_m3": round(working_volume_m3, 2),
        "headspace_ppm": headspace_ppm,
        "hrt_days": HRT_DAYS,
    }

@app.route("/")
def index():
    return render_template("index.html", active_page="dashboard")

@app.route("/analytics")
def analytics():
    return render_template("analytics.html", active_page="analytics")

@app.route("/twin")
def twin():
    return render_template("twin.html", active_page="twin")

@app.route("/sdlog")
def sdlog():
    return render_template("sdlog.html", active_page="sdlog")

@app.route("/power")
def power():
    return render_template("power.html", active_page="power")

@app.route("/api/data")
def get_data():
    return jsonify({
        "readings": sensor_data,
        "latest": sensor_data[-1],
        "project_start": PROJECT_START.strftime("%d %b %Y"),
        "project_now": PROJECT_NOW.strftime("%d %b %Y"),
        "retrieved_at": PROJECT_NOW.strftime("%d %b %Y, %H:%M:%S"),
        "source": "SD Card", "power": "Powerbank"
    })

@app.route("/api/sdlog")
def get_sdlog():
    return jsonify({"log": sd_log, "total": len(sd_log)})

@app.route("/api/power")
def get_power():
    latest = power_log[-1]
    return jsonify({"log": power_log, "latest": latest, "capacity_mah": POWERBANK_CAPACITY_MAH})

@app.route("/api/foodwaste")
def get_foodwaste():
    kg = request.args.get("kg", default=2.0, type=float)
    kg = max(0.0, min(20.0, kg))
    return jsonify(calculate_biogas(kg))

if __name__ == "__main__":
    app.run(debug=False)
