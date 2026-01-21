# Deployment Guide

The Momentum Signal App is a Streamlit application. It requires persistent storage for the Alerts feature.

## Requirements

- **Python 3.8+**
- **Persistent Volume** (Required for Alerts persistence)

## Environment Variables

- `STORAGE_PATH` (Required for cloud): Directory path to store `alerts.json`.
  - If not set, the app defaults to the project root (works locally).
  - On cloud platforms (Railway, etc.), you MUST mount a persistent volume and set this variable.

## Deploying on Railway

Railway now uses **Railpack** as the default builder.

### Steps:

1.  **Connect Repository**: Link your GitHub repository to Railway.

2.  **Configure Volume for Persistence**:
    - Go to your service → **Settings** → **Volumes**
    - Click **Add Volume**
    - Set Mount Path: `/app/data`

3.  **Set Environment Variable**:
    - Go to **Variables** tab
    - Add: `STORAGE_PATH=/app/data`

4.  **Deploy**: Railway will automatically build and deploy using `railway.json`.

### Configuration Files:

- `railway.json`: Specifies `RAILPACK` builder and start command.
- `requirements.txt`: Lists Python dependencies.

## Local Deployment

```bash
streamlit run streamlit_app.py
```

Alerts are saved to `alerts.json` in the project folder.
