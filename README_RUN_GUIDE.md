# 🏗️ Weighbridge Backend - Execution Guide

This guide provides step-by-step instructions on how to set up, configure, and run the FastAPI backend for the Weighbridge system.

---

## 📋 Prerequisites

*   **Python 3.10+**
*   **PostgreSQL** (Optional, for cloud sync)
*   **Virtual Environment** (Recommended)

---

## 🛠️ Step 1: Environment Setup

1.  **Create a Virtual Environment**:
    ```bash
    python3 -m venv venv
    ```

2.  **Activate the Environment**:
    ```bash
    source venv/bin/activate
    ```

3.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

---

## ⚙️ Step 2: Configuration (.env)

Ensure your `.env` file in the root directory is correctly configured. 
Key variables:

*   `DATABASE_URL`: Path to your local SQLite database (e.g., `sqlite+aiosqlite:///./receipts_v2.db`).
*   `POSTGRES_URL`: URL for your PostgreSQL database (e.g., `postgresql+asyncpg://user:pass@localhost/db`).
*   `ENVIRONMENT`: Set to `development` to enable automatic background sync.

---

## 🚀 Step 3: Running the Backend

### Option 1: Standard Run (for testing/development)
Use `uvicorn` to start the server with hot-reload enabled:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Option 2: Production-Ready Module Run
Run directly via Python module:

```bash
python3 -m app.main
```

---

## 📊 Step 4: Background Sync Worker

If your `ENVIRONMENT` is set to `development`, the **Sync Worker** starts automatically within the main process. 

To run the Sync Worker as a **standalone process** (best for stability):
```bash
python3 -m app.sync.sync_worker
```

---

## 📑 Access & Documentation

Once the backend is running, you can access the following:

| Service | URL |
| :--- | :--- |
| **Swagger UI (Interactive API Docs)** | [http://localhost:8000/docs](http://localhost:8000/docs) |
| **Health Check** | [http://localhost:8000/health](http://localhost:8000/health) |

---

## 🔧 Common Troubleshooting

*   **Port 8000 already in use**: Use `lsof -i :8000` to find the process ID and `kill -9 <PID>` to stop it.
*   **Database Permissions**: If you get a "permission denied" error in PostgreSQL, refer to the [PostgreSQL Permission Fix Guide](file:///Users/apple/.gemini/antigravity/brain/e6d3fa27-174d-4101-82e7-e949cb179759/walkthrough_pg_perms.md).
*   **SQLite Table Not Found**: Ensure you have restarted the backend at least once to trigger the auto-table creation logic in `app/main.py`.

---

© 2026 Weighbridge Software System - All rights reserved.
