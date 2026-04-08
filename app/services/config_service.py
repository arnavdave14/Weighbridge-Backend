import logging
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.admin_repo import AdminRepo
from app.core.validation_engine import get_etag
from app.models.admin_models import ActivationKey

logger = logging.getLogger(__name__)

class ConfigService:
    @staticmethod
    async def get_machine_config(db: AsyncSession, key: ActivationKey) -> Dict[str, Any]:
        """
        Fetches the latest configuration for a machine.
        Includes branding, headers, footers, and latest labels.
        """
        latest_schema = await AdminRepo.get_latest_schema(db, key.id)
        
        config = {
            "company_name": key.company_name,
            "logo_url": key.logo_url,
            "bill_header_1": key.bill_header_1,
            "bill_header_2": key.bill_header_2,
            "bill_header_3": key.bill_header_3,
            "bill_footer": key.bill_footer,
            "labels": latest_schema.labels if latest_schema else [],
            "version": key.current_version,
            "expiry_date": key.expiry_date.isoformat(),
            "status": key.status
        }
        
        # Calculate ETag for the config
        etag = get_etag(config)
        config["etag"] = etag
        
        return config
