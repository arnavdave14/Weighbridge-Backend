"""
Settings API
============
Provides endpoints for managing and reading the server's LAN connection
configuration (server_ip + port) stored on the company's ActivationKey.

Routes:
    GET  /settings          — Read current server_ip + port
    PUT  /settings          — Update server_ip and/or port
    GET  /settings/detect-ip — Auto-detect LAN IP for Admin Panel pre-fill

All routes are Admin JWT-protected.

Design notes:
    - server_ip + port live on the ActivationKey model (PostgreSQL).
    - These settings are read by devices/frontend to construct the API base URL:
          http://{server_ip}:{port}
    - Changing the port via PUT /settings does NOT restart the running server.
      The response includes restart_required=True when port changes so the
      operator knows they must restart uvicorn manually (or via systemd).
    - GET /settings/detect-ip is stateless — it just calls the socket probe
      and returns the result for the Admin Panel to pre-fill the form field.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database.db_manager import get_remote_db
from app.api.admin_deps import get_current_admin
from app.models.admin_models import ActivationKey, AdminUser
from app.schemas.admin_schemas import ServerConfigRead, ServerConfigUpdate
from app.utils.network import detect_server_ip
from app.config.settings import settings
import httpx

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/settings", tags=["Settings"])


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def _get_first_active_key(db: AsyncSession) -> ActivationKey:
    """
    Fetches the first ACTIVE or EXPIRING_SOON ActivationKey from PostgreSQL.
    This is the record that holds server_ip + port for the company.

    Raises 404 if no active license exists yet (licenses must be created first).
    """
    result = await db.execute(
        select(ActivationKey)
        .where(ActivationKey.status.in_(["ACTIVE", "EXPIRING_SOON"]))
        .order_by(ActivationKey.created_at.asc())  # oldest = primary
    )
    key = result.scalars().first()
    if not key:
        raise HTTPException(
            status_code=404,
            detail=(
                "No active license found. "
                "Create at least one activation key before managing settings."
            )
        )
    return key


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.get(
    "/detect-ip",
    summary="Auto-detect server LAN IP",
    response_model=dict,
)
async def detect_ip(
    _: AdminUser = Depends(get_current_admin),
):
    """
    Probes the OS routing table to find the machine's primary LAN IP.

    Returns:
        {
            "server_ip": "192.168.1.10",
            "port": 8000,
            "note": "Auto-detected. Editable before saving."
        }

    This endpoint is stateless — it does NOT read or write the database.
    Call it before license creation to pre-fill the server_ip field in the
    Admin Panel form.
    """
    ip = detect_server_ip()
    return {
        "server_ip": ip,
        "port": settings.SERVER_PORT,
        "note": "Auto-detected via routing table probe. Editable before saving.",
    }


@router.get(
    "",
    summary="Get current server connection settings",
    response_model=ServerConfigRead,
)
async def get_settings(
    db: AsyncSession = Depends(get_remote_db),
    _: AdminUser = Depends(get_current_admin),
):
    """
    Returns the server_ip and port saved on the first active ActivationKey.

    Frontend / devices use these values to dynamically construct the API URL:
        http://{server_ip}:{port}

    restart_required is True when the saved port differs from the process's
    running SERVER_PORT environment variable, indicating the operator needs
    to restart the backend for the new port to take effect.
    """
    key = await _get_first_active_key(db)

    saved_port = key.port or settings.SERVER_PORT
    restart_required = saved_port != settings.SERVER_PORT

    return ServerConfigRead(
        server_ip=key.server_ip,
        port=saved_port,
        restart_required=restart_required,
    )


@router.put(
    "",
    summary="Update server connection settings",
    response_model=ServerConfigRead,
)
async def update_settings(
    update_in: ServerConfigUpdate,
    db: AsyncSession = Depends(get_remote_db),
    _: AdminUser = Depends(get_current_admin),
):
    """
    Updates server_ip and/or port on the active ActivationKey.

    Partial update: only the fields present in the request body are changed.

    Important:
        - Changing the port does NOT restart the running server.
        - If the new port ≠ SERVER_PORT env var, restart_required=True is returned.
        - The operator must restart uvicorn (or the systemd service) manually.

    Returns the updated settings + restart_required flag.
    """
    key = await _get_first_active_key(db)
    prev_port = key.port or settings.SERVER_PORT

    updated = False

    if update_in.server_ip is not None:
        key.server_ip = update_in.server_ip
        updated = True
        logger.info("Settings: server_ip updated to %s", update_in.server_ip)

    if update_in.port is not None:
        key.port = update_in.port
        updated = True
        logger.info("Settings: port updated to %d (was %d)", update_in.port, prev_port)

    if updated:
        db.add(key)
        await db.commit()
        await db.refresh(key)

    saved_port = key.port or settings.SERVER_PORT
    restart_required = saved_port != settings.SERVER_PORT

    if restart_required and update_in.port is not None:
        logger.warning(
            "Settings: port changed to %d — backend restart required for change to take effect.",
            saved_port,
        )

    return ServerConfigRead(
        server_ip=key.server_ip,
        port=saved_port,
        restart_required=restart_required,
    )


from pydantic import BaseModel
import platform
import asyncio

class ConnectionTestResult(BaseModel):
    ip_status: str
    port_status: str
    service_status: str
    message: str

@router.get(
    "/test-connection",
    summary="Multi-stage connection validation",
    response_model=ConnectionTestResult,
)
async def test_connection(
    ip: str,
    port: int,
    _: AdminUser = Depends(get_current_admin),
):
    """
    Multi-stage connection validation:
    1. IP Reachability (Ping)
    2. Port Availability (TCP connection)
    3. Service Health (HTTP GET /health)
    """
    logger.info("Settings: Testing connection to %s:%d", ip, port)

    ip_reachable = False
    port_open = False
    service_running = False
    
    # 1. IP Reachability
    if ip.lower() in ("localhost", "127.0.0.1", "0.0.0.0"):
        ip_reachable = True
    else:
        try:
            param = '-n' if platform.system().lower() == 'windows' else '-c'
            timeout_param = '-w' if platform.system().lower() == 'windows' else ('-t' if platform.system().lower() == 'darwin' else '-W')
            
            proc = await asyncio.create_subprocess_exec(
                'ping', param, '1', timeout_param, '1', ip,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            await proc.communicate()
            ip_reachable = (proc.returncode == 0)
        except Exception:
            pass

    # 2. Port Availability
    try:
        _, writer = await asyncio.wait_for(asyncio.open_connection(ip, port), timeout=2.0)
        writer.close()
        await writer.wait_closed()
        port_open = True
        ip_reachable = True  # If port is open, IP is reachable
    except Exception:
        pass

    # 3. Service Health
    if port_open:
        target_url = f"http://{ip}:{port}/health"
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(target_url)
                if resp.status_code == 200:
                    service_running = True
        except Exception:
            pass

    if service_running:
        message = "Service is live and responding."
    elif port_open:
        message = "Port is open, but the service at /health is not responding. It may be booting or misconfigured."
    elif ip_reachable:
        message = "Client software is not running yet. This is expected before deployment."
    else:
        message = "The target IP is not reachable on the network. Check if the device is powered on and connected."

    return ConnectionTestResult(
        ip_status="Reachable" if ip_reachable else "Not Reachable",
        port_status="Open" if port_open else "Closed",
        service_status="Running" if service_running else "Not Running",
        message=message
    )
