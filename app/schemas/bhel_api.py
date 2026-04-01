from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date, datetime

class BHELWeighBridgeEntry(BaseModel):
    weighbridgeCode: str = Field(..., description="WB001, WB002, WB004")
    ticketNo: str = Field(..., description="Ticket number, e.g. 1, 2, 3")
    ticketDate: date = Field(..., description="Format YYYY-MM-DD")
    gatePassType: str = Field(..., description="'I' - Inward, 'O' - Outward")
    partyName: str = Field(..., description="Party Name (VARCHAR2 100)")
    itemDescription: str = Field(..., description="Item Description (VARCHAR2 60)")
    poNo: str = Field(..., description="PO Number (VARCHAR2 20)")
    reference: Optional[str] = Field(None, description="Reference Details (VARCHAR2 60)")
    transporterName: str = Field(..., description="Transporter Name (VARCHAR2 60)")
    vehicleNo: str = Field(..., description="Vehicle Number (VARCHAR2 12)")
    driverName: Optional[str] = Field(None, description="Driver Name (VARCHAR2 40)")
    driverContactNo: Optional[str] = Field(None, description="Driver Contact No (VARCHAR2 10)")
    grossWeight: str = Field(..., description="Gross Weight as string, e.g. '21990.00'")
    grossWtDate: str = Field(..., description="Format YYYY-MM-DD HH24:MI:SS")
    tareWeight: str = Field(..., description="Tare Weight as string, e.g. '9700.00'")
    tareWtDate: str = Field(..., description="Format YYYY-MM-DD HH24:MI:SS")
    netWeight: str = Field(..., description="Net Weight as string, e.g. '12200.00'")
    image01: Optional[str] = Field(None, description="Base64 encoded image 01")
    image02: Optional[str] = Field(None, description="Base64 encoded image 02")
    image03: Optional[str] = Field(None, description="Base64 encoded image 03")
    image04: Optional[str] = Field(None, description="Base64 encoded image 04")

class BHELRequest(BaseModel):
    data: List[BHELWeighBridgeEntry]

class BHELResponseItem(BaseModel):
    weighbridgeCode: str
    ticketNo: str
    apiTxnId: str

class BHELResponse(BaseModel):
    data: List[BHELResponseItem]
