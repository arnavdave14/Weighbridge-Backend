from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from app.database.db_manager import get_db
from app.models.models import AppData
from app.models.employee_model import Employee
from app.schemas.schemas import AppDataWrite, AppDataRead
from app.api.employee_deps import get_current_employee

router = APIRouter(prefix="/employee/data", tags=["Employee App Data"])

@router.get("/{collection}", response_model=List[AppDataRead])
async def list_app_data(
    collection: str,
    db: AsyncSession = Depends(get_db),
    employee: Employee = Depends(get_current_employee)
):
    """
    List all documents in a specific collection for the current tenant.
    """
    stmt = select(AppData).where(
        AppData.key_id == employee.key_id,
        AppData.collection == collection,
        AppData.is_deleted == False
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{collection}/{document_id}", response_model=AppDataRead)
async def get_app_data(
    collection: str,
    document_id: str,
    db: AsyncSession = Depends(get_db),
    employee: Employee = Depends(get_current_employee)
):
    """
    Get a specific document by its ID.
    """
    stmt = select(AppData).where(
        AppData.key_id == employee.key_id,
        AppData.collection == collection,
        AppData.document_id == document_id,
        AppData.is_deleted == False
    )
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.put("/{collection}/{document_id}", response_model=AppDataRead)
async def upsert_app_data(
    collection: str,
    document_id: str,
    data: AppDataWrite,
    db: AsyncSession = Depends(get_db),
    employee: Employee = Depends(get_current_employee)
):
    """
    Create or update a document in a collection.
    Automatically scoped to the tenant (key_id).
    """
    stmt = select(AppData).where(
        AppData.key_id == employee.key_id,
        AppData.collection == collection,
        AppData.document_id == document_id
    )
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()

    if doc:
        doc.payload = data.payload
        doc.is_deleted = False
        doc.is_synced = False  # Mark as dirty for sync
    else:
        doc = AppData(
            key_id=employee.key_id,
            collection=collection,
            document_id=document_id,
            payload=data.payload,
            is_synced=False
        )
        db.add(doc)

    await db.commit()
    await db.refresh(doc)
    return doc


@router.delete("/{collection}/{document_id}")
async def delete_app_data(
    collection: str,
    document_id: str,
    db: AsyncSession = Depends(get_db),
    employee: Employee = Depends(get_current_employee)
):
    """
    Soft-delete a document from a collection.
    """
    stmt = select(AppData).where(
        AppData.key_id == employee.key_id,
        AppData.collection == collection,
        AppData.document_id == document_id,
        AppData.is_deleted == False
    )
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    doc.is_deleted = True
    doc.is_synced = False  # Mark as dirty for sync
    await db.commit()

    return {"status": "success", "message": "Document deleted"}
