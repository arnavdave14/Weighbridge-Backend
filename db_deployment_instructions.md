# Fly.io Database & Application Deployment Guide

You requested a setup utilizing your precise allowance on Fly.io (three 256MB machines with 3GB of persistent volume and PostgreSQL for the online DB). Here is how to create this infrastructure from scratch safely.

## 1. Deploy the PostgreSQL Cluster
Fly.io provides a managed PostgreSQL app. Run this command to provision your DB instance as a 256MB VM (taking up 1 of your 3 VM slots):

```bash
fly postgres create \
  --name weighbridge-db \
  --vm-size shared-cpu-1x \
  --memory 256 \
  --volume-size 1 \
  --initial-cluster-size 1
```
*(The `--volume-size 1` gives you 1GB of the 3GB persistent limit. You can increase this to 3 if no other VMs need a volume).*

You will receive a connection string which looks like:
`postgres://postgres:<password>@weighbridge-db.flycast:5432`

## 2. Prepare the Application for Deployment
We created a `fly.toml` that configures your FastAPI app to run on a 256MB memory VM.

Set your environment variables (so the app can connect to the Database):
```bash
fly secrets set REMOTE_DATABASE_URL="postgresql+asyncpg://postgres:<password>@weighbridge-db.flycast:5432/postgres?sslmode=disable"
fly secrets set SECRET_KEY="<your_jwt_secret>"
# Add API keys for DIGITALSMS and BHEL as well
```

## 3. Deploy the Application
Run the deployment command:
```bash
fly deploy
```

Since the `fly.toml` uses `min_machines_running = 1`, it will spawn a single 256MB VM running the Web Server.

## 4. Scaling (Using the 3rd VM)
You have 1 DB VM and 1 Web Server VM. You requested 3 VMs total. You can safely tell Fly.io to scale your Web Server count to 2 replicas:
```bash
fly scale count 2
```
This spawns a second 256MB VM. Fly.io's proxy will automatically load-balance requests across the two machines.

If you prefer to use the 3rd VM as a Celery background worker instead, we can configure an additional `[processes]` block in `fly.toml` later.
