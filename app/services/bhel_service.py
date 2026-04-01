import os
import httpx
import json
from typing import List, Dict, Any, Optional
from app.schemas.bhel_api import BHELRequest, BHELResponse
import logging

logger = logging.getLogger(__name__)

# BHEL API Configuration
BHEL_DEV_URL = os.getenv("BHEL_DEV_URL", "http://10.27.55.55:82/api/weigh-bridge/")
BHEL_PROD_URL = os.getenv("BHEL_PROD_URL", "https://cfpapp.bhel.in/api/weigh-bridge/")
BHEL_API_TOKEN = os.getenv("BHEL_API_TOKEN", "44642f0b5b11ae709134849ff7ad853d2b0955f7")

class BHELService:
    @staticmethod
    async def post_to_bhel(data: BHELRequest, environment: str = "dev") -> Optional[BHELResponse]:
        """
        Sends weighing data to BHEL API.
        
        :param data: BHELRequest object containing list of entries.
        :param environment: 'dev' or 'prod' to choose endpoint.
        :return: BHELResponse or None if request fails.
        """
        url = BHEL_DEV_URL if environment.lower() == "dev" else BHEL_PROD_URL
        headers = {
            "Content-Type": "application/json",
            "X-Api-Token": BHEL_API_TOKEN
        }
        
        # Convert Pydantic model to dict, then to JSON string if needed, 
        # but httpx handles dict directly.
        payload = data.model_dump()
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=headers
                )
                
                # Check for HTTP errors
                response.raise_for_status()
                
                # Parse the response JSON
                response_json = response.json()
                logger.info(f"Successfully posted to BHEL {environment}: {response_json}")
                
                return BHELResponse(**response_json)
        
        except httpx.HTTPStatusError as e:
            logger.error(f"BHEL API Error ({environment}): HTTP {e.response.status_code} - {e.response.text}")
            return None
        except httpx.RequestError as e:
            logger.error(f"BHEL API Connection Error ({environment}): {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in BHELService: {str(e)}")
            return None

    @staticmethod
    async def sync_receipt_to_bhel(receipt_data: Dict[str, Any], environment: str = "dev"):
        """
        Helper method to convert local receipt data to BHEL format and sync.
        This is a placeholder for actual mapping logic based on project's receipt model.
        """
        # Example mapping (needs to be adjusted once actual receipt model is known)
        bhel_entry = {
            "weighbridgeCode": receipt_data.get("wb_code", "WB001"),
            "ticketNo": str(receipt_data.get("id", "1")),
            "ticketDate": receipt_data.get("date", "2026-03-02"),
            "gatePassType": receipt_data.get("type", "I"),
            "partyName": receipt_data.get("party_name", "N/A"),
            "itemDescription": receipt_data.get("item", "N/A"),
            "poNo": receipt_data.get("po_no", "N/A"),
            "reference": receipt_data.get("reference", ""),
            "transporterName": receipt_data.get("transporter", "N/A"),
            "vehicleNo": receipt_data.get("vehicle_no", "N/A"),
            "driverName": receipt_data.get("driver", ""),
            "driverContactNo": receipt_data.get("phone", ""),
            "grossWeight": str(receipt_data.get("gross_weight", "0.00")),
            "grossWtDate": receipt_data.get("gross_date", "2026-03-02 00:00:00"),
            "tareWeight": str(receipt_data.get("tare_weight", "0.00")),
            "tareWtDate": receipt_data.get("tare_date", "2026-03-02 00:00:00"),
            "netWeight": str(receipt_data.get("net_weight", "0.00")),
            # Base64 images from storage if available
            "image01": receipt_data.get("image01", ""),
            "image02": receipt_data.get("image02", ""),
            "image03": receipt_data.get("image03", ""),
            "image04": receipt_data.get("image04", ""),
        }
        
        request = BHELRequest(data=[bhel_entry])
        return await BHELService.post_to_bhel(request, environment=environment)
