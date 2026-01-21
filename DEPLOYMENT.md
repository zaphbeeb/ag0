# Deployment Guide

The Momentum Signal App is a Streamlit application. It requires persistent storage for the Alerts feature.

## Requirements

- **Python 3.8+**
- **Persistent Volume** (Recommended for Alerts)

## Environment Variables

- `STORAGE_PATH` (Optional): Directory path to store `alerts.json`.
  - If not set, the app defaults to the project root.
  - On cloud platforms (Railway, Heroku), you MUST mount a persistent volume and set this variable to the mount path (e.g., `/data`).

## Deploying on Railway

1.  **Project Settings**: Set Build Command to `pip install -r requirements.txt`.
2.  **Start Command**: `streamlit run streamlit_app.py --server.port $PORT --server.address 0.0.0.0`
3.  **Persistence**:
    - Add a **Volume** to your service.
    - Mount it to a path, e.g., `/app/data`.
    - Add a Service Variable: `STORAGE_PATH=/app/data`.

## Local Deployment

Simply run:
```bash
streamlit run streamlit_app.py
```
Alerts will be saved to `alerts.json` in the project folder.
