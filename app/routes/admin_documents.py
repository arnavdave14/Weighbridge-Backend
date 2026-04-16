from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, or_
from typing import Optional, List, Dict, Any
import uuid

from app.database.db_manager import get_remote_db
from app.models.admin_models import DocumentDeliveryLog, ActivationKey
from app.api.admin_deps import get_current_admin

router = APIRouter(prefix="/documents", tags=["Admin Documents"])

@router.get("/logs")
async def get_document_logs(
    company_id: Optional[str] = None,
    status: Optional[str] = None,
    document_type: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_remote_db),
    admin=Depends(get_current_admin)
):
    """
    Paginated list of document delivery logs with filters.
    """
    stmt = select(DocumentDeliveryLog)
    conditions = []

    if company_id:
        try:
            conditions.append(DocumentDeliveryLog.key_id == uuid.UUID(company_id))
        except ValueError:
            pass

    if status:
        conditions.append(DocumentDeliveryLog.status == status)

    if document_type:
        conditions.append(DocumentDeliveryLog.document_type == document_type)

    if search:
        search_pattern = f"%{search}%"
        conditions.append(or_(
            DocumentDeliveryLog.document_name.ilike(search_pattern),
            DocumentDeliveryLog.email_used.ilike(search_pattern),
            DocumentDeliveryLog.whatsapp_channel.ilike(search_pattern),
            DocumentDeliveryLog.company_name.ilike(search_pattern)
        ))

    if conditions:
        stmt = stmt.where(and_(*conditions))

    # Count total
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    # Paginate
    offset = (page - 1) * limit
    stmt = stmt.order_by(desc(DocumentDeliveryLog.created_at)).offset(offset).limit(limit)
    
    result = await db.execute(stmt)
    logs = result.scalars().all()

    # Format result
    formatted_logs = []
    for log in logs:
        formatted_logs.append({
            "id": str(log.id),
            "key_id": str(log.key_id) if log.key_id else None,
            "company_name": log.company_name,
            "document_name": log.document_name,
            "document_type": log.document_type,
            "email_used": log.email_used,
            "whatsapp_channel": log.whatsapp_channel,
            "sender_name": log.sender_name,
            "provider_type": log.provider_type,
            "delivery_channel": log.delivery_channel,
            "status": log.status,
            "latency": log.latency,
            "attachments_count": len(log.attachments) if log.attachments else 0,
            "created_at": log.created_at
        })

    return {
        "items": formatted_logs,
        "total": total,
        "page": page,
        "limit": limit
    }

@router.get("/stats")
async def get_document_stats(
    db: AsyncSession = Depends(get_remote_db),
    admin=Depends(get_current_admin)
):
    """
    Overview stats for Summary Cards.
    """
    # Total count
    total_res = await db.execute(select(func.count(DocumentDeliveryLog.id)))
    total = total_res.scalar() or 0

    # Failed count
    failed_res = await db.execute(select(func.count(DocumentDeliveryLog.id)).where(DocumentDeliveryLog.status == "FAILED"))
    failed = failed_res.scalar() or 0

    # Success count
    success_res = await db.execute(select(func.count(DocumentDeliveryLog.id)).where(DocumentDeliveryLog.status == "SUCCESS"))
    success = success_res.scalar() or 0

    success_rate = (success / total * 100) if total > 0 else 0

    # Average latency
    latency_res = await db.execute(select(func.avg(DocumentDeliveryLog.latency)).where(DocumentDeliveryLog.status == "SUCCESS"))
    avg_latency = latency_res.scalar() or 0

    return {
        "total_documents": total,
        "total_failed": failed,
        "success_rate": round(success_rate, 2),
        "average_latency": round(avg_latency, 3)
    }

@router.get("/{idx}")
async def get_document_detail(
    idx: str,
    db: AsyncSession = Depends(get_remote_db),
    admin=Depends(get_current_admin)
):
    """
    Full details for a specific log entry.
    """
    try:
        log_id = uuid.UUID(idx)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid log ID")

    result = await db.execute(select(DocumentDeliveryLog).where(DocumentDeliveryLog.id == log_id))
    log = result.scalars().first()

    if not log:
        raise HTTPException(status_code=404, detail="Document log not found")

    return {
        "id": str(log.id),
        "key_id": str(log.key_id) if log.key_id else None,
        "company_name": log.company_name,
        "document_name": log.document_name,
        "document_type": log.document_type,
        "email_used": log.email_used,
        "whatsapp_channel": log.whatsapp_channel,
        "sender_name": log.sender_name,
        "provider_type": log.provider_type,
        "delivery_channel": log.delivery_channel,
        "status": log.status,
        "error_message": log.error_message,
        "retry_count": log.retry_count,
        "latency": log.latency,
        "metadata": log.metadata_json or {},
        "attachments": log.attachments or [],
        "created_at": log.created_at
    }

@router.post("/{idx}/retry")
async def retry_document_delivery(
    idx: str,
    db: AsyncSession = Depends(get_remote_db),
    admin=Depends(get_current_admin)
):
    """
    Retry a failed document delivery.
    """
    try:
        log_id = uuid.UUID(idx)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid log ID")

    result = await db.execute(select(DocumentDeliveryLog).where(DocumentDeliveryLog.id == log_id))
    log = result.scalars().first()

    if not log:
        raise HTTPException(status_code=404, detail="Document log not found")
        
    if log.status == "SUCCESS":
        raise HTTPException(status_code=400, detail="Document was already delivered successfully.")

    # Call service again with stored values
    from app.services.document_delivery_service import DocumentDeliveryService
    
    success = await DocumentDeliveryService.process_and_deliver_document(
        key_id=str(log.key_id) if log.key_id else None,
        document_type=log.document_type,
        document_name=log.document_name,
        document_bytes=None, # Cannot resend bytes from here currently without fetching from storage, but we can resend metadata link
        metadata_json=log.metadata_json or {},
        target_email=log.email_used,
        target_whatsapp=log.whatsapp_channel
    )
    
    if success:
        log.status = "SUCCESS"
        log.error_message = None
        log.retry_count = (log.retry_count or 0) + 1
        db.add(log)
        await db.commit()
        return {"status": "success", "message": "Document delivery retry succeeded"}
    else:
        log.retry_count = (log.retry_count or 0) + 1
        db.add(log)
        await db.commit()
        raise HTTPException(status_code=500, detail="Document delivery retry failed again")
