from sqlalchemy import Column, Integer, String, DateTime, Text, BigInteger, Numeric
from sqlalchemy.sql import func
from .database import Base

class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    weighbridgeCode = Column(String(5), index=True)
    ticketNo = Column(String, index=True)
    ticketDate = Column(String) # YYYY-MM-DD
    gatePassType = Column(String(1)) # 'I' or 'O'
    partyName = Column(String(100))
    itemDescription = Column(String(60))
    poNo = Column(String(20))
    reference = Column(String(60))
    transporterName = Column(String(60))
    vehicleNo = Column(String, index=True) # Optimized for quick search
    driverName = Column(String(40))
    driverContactNo = Column(String(10))
    
    # Weights stored as strings to match sample, or Numeric for calculations
    grossWeight = Column(String) # Stored as string to handle BHEL's format
    grossWtDate = Column(String) # YYYY-MM-DD HH:MI:SS
    tareWeight = Column(String)
    tareWtDate = Column(String) # YYYY-MM-DD HH:MI:SS
    netWeight = Column(String)
    
    # BHEL images often base64 and quite large
    image01 = Column(Text, nullable=True) 
    image02 = Column(Text, nullable=True)
    image03 = Column(Text, nullable=True)
    image04 = Column(Text, nullable=True)
    
    # Internal system fields
    apiTxnId = Column(String, unique=True, index=True)
    recordedAt = Column(DateTime(timezone=True), server_default=func.now())
