# BioSpark Dashboard

A web dashboard for monitoring our BioSpark biogas digester prototype. Built for MFB2102 Engineering Team Project II, Group 2, Universiti Teknologi PETRONAS.

## What it does

Displays real sensor data collected from our prototype digester over a 12-day run (3 Jul to 15 Jul 2026). Data was logged to an SD card via Arduino and is served through a Flask backend. The dashboard shows temperature readings from a DS18B20 probe inside the digester, methane levels from an MQ-4 sensor, a live 3D digital twin of the full biogas pipeline, and a full data table with status indicators.

## Tech stack

- Python (Flask) for the backend
- Chart.js for the line graphs
- Three.js for the 3D digital twin
- HTML/CSS/JS for the frontend
- Deployed on Render

## How to run locally

Make sure you have Python installed, then run the following in your terminal:

```
pip install flask gunicorn
python app.py
```

Then open your browser and go to:

```
http://127.0.0.1:5000
```

## Project files

```
biospark/
├── app.py                  main Flask app and API
├── requirements.txt        Python dependencies
├── README.md               this file
└── templates/
    └── index.html          dashboard frontend
```

## Sensor data

Data was read from the SD card after the 12-day prototype run. Readings were taken every 3 days at noon.

| Date | Temp (C) | Methane (raw) | Status |
|---|---|---|---|
| 03 Jul | 32.63 | 88 | Not Ready |
| 06 Jul | 31.0 | 127 | Building |
| 09 Jul | 31.5 | 198 | Building |
| 12 Jul | 30.8 | 310 | Good |
| 15 Jul | 30.5 | 398 | Good |

## About the project

BioSpark is a community-scale biogas system that converts food waste into clean energy for cooking. The digester takes organic food waste as input, produces biogas through anaerobic digestion, and the gas is used to power a community kitchen for food aid. This dashboard is part of our digital monitoring system for the prototype.


