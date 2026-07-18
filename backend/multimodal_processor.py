import os
import json
from gemma_client import gemma_vision_call

def process_document(image_path, context_data=None):
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")
        
    prompt = """
    Perform a complete Multimodal Document Processing and Forensics Analysis on this image.
    1. Layout Understanding & OCR: Extract key text fields and their approximate bounding boxes [x1, y1, x2, y2].
    2. Document Classification: Classify the document type (e.g., Invoice, KYC, Bank Statement, Mixed Layout).
    3. Adversarial Document Fraud Detection: Look for:
       - Font inconsistencies (e.g. amount or name in different font)
       - Spliced or copy-pasted regions (e.g. signature block)
       - Stamps or Watermarks indicating tampering or processing (e.g., 'APPROVED' stamp)
       - Metadata mismatch (if visible)
       - Deviations from standard historical vendor templates
       
    Respond strictly in JSON format with the following structure:
    {
        "document_type": "string",
        "extracted_data": [
            {"field": "string", "value": "string", "bbox": [x1, y1, x2, y2]}
        ],
        "forensics": {
            "fraud_detected": boolean,
            "anomalies": [
                {
                    "type": "string",
                    "description": "string",
                    "bbox": [x1, y1, x2, y2],
                    "severity": "High/Medium/Low"
                }
            ],
            "stamps_detected": [
                {
                    "text": "string",
                    "bbox": [x1, y1, x2, y2]
                }
            ],
            "template_deviation_score": float (0.0 to 1.0)
        },
        "confidence": integer (0-100),
        "recommendation": "string"
    }
    """
    results = gemma_vision_call(prompt, image_path, context_data=context_data)
    return results

if __name__ == '__main__':
    res = process_document('data/tampered_invoice.png')
    print(json.dumps(res, indent=2))
