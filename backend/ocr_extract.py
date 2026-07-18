import json
import os
from gemma_client import gemma_vision_call

def extract_kyc_data(account_id):
    image_path = f'data/kyc_images/{account_id}.png'
    if os.path.exists(image_path):
        prompt = 'Extract the following fields from this KYC document image: \nname, dob, address, id_number, employer, declared_purpose, declared_income.\nReturn strictly as a JSON object with these keys. Do not include markdown formatting or tags.'
        try:
            return gemma_vision_call(prompt, image_path, fallback_type='ocr')
        except Exception as e:
            print(f'OCR Extraction failed: {e}')
            return None
    return None
