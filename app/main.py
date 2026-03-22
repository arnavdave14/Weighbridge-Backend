import uvicorn
from fastapi import FastAPI, HTTPException, Header, status, Depends
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uuid
import os
from dotenv import load_dotenv
from sqlalchemy.orm import Session

# Load environment variables
load_dotenv()


# Database Imports
from .database import engine, SessionLocal, get_db
from . import models

# Initialize database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="BHEL Weigh Bridge API",
    description="Backend API for BHEL Weigh Bridge System Integration with PostgreSQL",
    version="1.1.0"
)

# Constants
BHEL_API_TOKEN = os.getenv("BHEL_API_TOKEN")


# --- Pydantic Models for API Requests/Responses ---

class BHELDataRecord(BaseModel):
    weighbridgeCode: str = Field(..., max_length=5)
    ticketNo: str
    ticketDate: str
    gatePassType: str = Field(..., max_length=1)
    partyName: str = Field(..., max_length=100)
    itemDescription: str = Field(..., max_length=60)
    poNo: str = Field(..., max_length=20)
    reference: str = Field(..., max_length=60)
    transporterName: str = Field(..., max_length=60)
    vehicleNo: str = Field(..., max_length=12)
    driverName: str = Field(..., max_length=40)
    driverContactNo: str = Field(..., max_length=10)
    grossWeight: str
    grossWtDate: str
    tareWeight: str
    tareWtDate: str
    netWeight: str
    image01: Optional[str] = None
    image02: Optional[str] = None
    image03: Optional[str] = None
    image04: Optional[str] = None

class BHELRequest(BaseModel):
    data: List[BHELDataRecord]

class BHELResponseRecord(BaseModel):
    weighbridgeCode: str
    ticketNo: str
    apiTxnId: str

class BHELResponse(BaseModel):
    data: List[BHELResponseRecord]

# --- API Endpoints ---

@app.get("/")
async def root():
    return {"message": "BHEL Integration API Online", "database": "PostgreSQL Ready"}

@app.post("/api/weigh-bridge/", response_model=BHELResponse)
async def weigh_bridge_submission(
    request: BHELRequest,
    x_api_token: str = Header(..., alias="X-Api-Token"),
    db: Session = Depends(get_db)
):
    # 1. Token Verification
    if x_api_token != BHEL_API_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or Missing API Token"
        )

    response_list = []
    
    # 2. Process each record in the batch
    for record in request.data:
        # Generate a unique Transaction ID
        txn_id = uuid.uuid4().hex[:8].upper()
        
        # 3. Create Database Entry
        db_ticket = models.Ticket(
            **record.model_dump(),
            apiTxnId=txn_id
        )
        
        db.add(db_ticket)
        
        # Prepare the response entry
        response_list.append(BHELResponseRecord(
            weighbridgeCode=record.weighbridgeCode,
            ticketNo=record.ticketNo,
            apiTxnId=txn_id
        ))

        try:
            db.commit()      # Attempt to save to PostgreSQL
            db.refresh(db_ticket)
        except Exception:
            db.rollback()    # If anything goes wrong, undo the changes
            raise           # Re-raise the error so you can see it in logs

    return BHELResponse(data=response_list)

@app.get("/api/weigh-bridge/history")
async def get_history(
    x_api_token: str = Header(..., alias="X-Api-Token"),
    db: Session = Depends(get_db)
):
    if x_api_token != BHEL_API_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized"
        )
    
    # Retrieve all tickets from database
    tickets = db.query(models.Ticket).all()
    return tickets

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
