import httpx
import logging
from app.core.config import settings
from app.core.exceptions import ExternalAPIException

logger = logging.getLogger(__name__)

class PMKisanService:
    def __init__(self):
        self.api_key = settings.DATA_GOV_IN_API_KEY
        # Hypothetical endpoint based on data.gov.in standards
        self.base_url = "https://api.data.gov.in/resource" 

    async def get_pmkisan_status(self, registration_number: str) -> str:
        """
        Check PM-KISAN beneficiary status using data.gov.in API.
        """
        if not self.api_key:
            logger.warning("DATA_GOV_IN_API_KEY not set. Using mock PM-KISAN data.")
            return f"PM-KISAN Status for {registration_number}: The 14th installment of Rs. 2000 has been credited to your linked bank account."
            
        # Example data.gov.in resource ID for PM-KISAN (hypothetical)
        resource_id = "pmkisan_beneficiary_dataset_id"
        
        params = {
            "api-key": self.api_key,
            "format": "json",
            "filters[registration_no]": registration_number
        }
        
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0, read=30.0)) as client:
                response = await client.get(f"{self.base_url}/{resource_id}", params=params)
                response.raise_for_status()
                data = response.json()
                
                records = data.get("records", [])
                if not records:
                    return f"No PM-KISAN records found for registration number {registration_number}. Please verify the number or contact your local agriculture office."
                    
                record = records[0]
                status = record.get("installment_status", "Unknown")
                amount = record.get("amount", "0")
                
                return f"PM-KISAN Status for {registration_number}: Your recent installment status is '{status}'. Amount: Rs. {amount}."
                
        except httpx.HTTPStatusError as e:
            logger.error(f"PM-KISAN API HTTP error: {e.response.text}")
            return "Failed to fetch PM-KISAN data due to a server error."
        except Exception as e:
            logger.error(f"PM-KISAN API unexpected error: {str(e)}")
            return "Unable to check PM-KISAN status at this time. Please try again later."

pmkisan_service = PMKisanService()
