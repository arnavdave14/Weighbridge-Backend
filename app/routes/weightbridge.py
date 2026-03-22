from fastapi import APIRouter, Header, Depends, HTTPException, status
from sqlalchemy.orm import Session
import uuid
from app.database import get_db
from app import models
from app.schemas import BHELRequest, BHELResponse, BHELResponseRecord

router = APIRouter()
API_TOKEN = "44642f0b5b11ae709134849ff7ad853d2b0955f7"

@router.post("/api/weigh-bridge/", response_model=BHELResponse)
def weigh_bridge_submission(
    request: BHELRequest,
    x_api_token: str = Header(..., alias="X-Api-Token"),
    db: Session = Depends(get_db)
):
    if x_api_token != API_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or Missing API Token"
        )
    
    response_list = []
    
    for record in request.data:
        txn_id = uuid.uuid4().hex[:8].upper()
        
        db_ticket = models.Ticket(
            **record.model_dump(),
            apiTxnId=txn_id
        )
        
        db.add(db_ticket)
        
        response_list.append(BHELResponseRecord(
            weighbridgeCode=record.weighbridgeCode,
            ticketNo=record.ticketNo,
            apiTxnId=txn_id
        ))
        
        try:
            db.commit()
            db.refresh(db_ticket)
        except Exception:
            db.rollback()
            raise
    
    return BHELResponse(data=response_list)

@router.get("/api/weigh-bridge/history")
def get_history(
    x_api_token: str = Header(..., alias="X-Api-Token"),
    db: Session = Depends(get_db)
):
    if x_api_token != API_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    return db.query(models.Ticket).all()