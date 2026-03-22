from pydantic import BaseModel, Field
from typing import List, Optional

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
