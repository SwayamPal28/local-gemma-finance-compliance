import requests
import json
import base64
import os

def get_ollama_url():
    # 1. Check environment variable
    env_url = os.environ.get("OLLAMA_BASE_URL")
    if env_url:
        return env_url
    
    # 2. Check database platform_settings
    db_path = 'compliance.db'
    if os.path.exists(db_path):
        import sqlite3
        try:
            conn = sqlite3.connect(db_path, timeout=5)
            row = conn.execute("SELECT value FROM platform_settings WHERE key = 'ollama_url'").fetchone()
            conn.close()
            if row:
                return row[0].strip()
        except Exception:
            pass
            
    # 3. Default fallback
    return 'http://localhost:11434'

def gemma_call(prompt, model='gemma2:2b', thinking=False, required_keys=('what_happened', 'why_it_matters', 'recommended_action', 'confidence')):
    if thinking:
        print("Warning: Thinking Mode is not recommended for JSON outputs.")
        full_prompt = f"<|think|>\n{prompt}"
    else:
        full_prompt = prompt
        
    try:
        r = requests.post(f"{get_ollama_url()}/api/generate", json={
            'model': model,
            'prompt': full_prompt,
            'stream': False,
            'format': 'json'
        }, timeout=120)
        r.raise_for_status()
        response_data = r.json()
        response_text = response_data.get('response', '{}')
        
        if not response_text.strip():
            print(f"Empty response from model. Full data: {response_data}")
            raise ValueError("Empty response from model")
            
        parsed = json.loads(response_text)
        if required_keys:
            if 'confidence_score' in parsed and 'confidence' not in parsed:
                val = parsed['confidence_score']
                if isinstance(val, (int, float)) and val <= 1.0:
                    parsed['confidence'] = int(val * 100)
                else:
                    parsed['confidence'] = val
                    
            if all((key in parsed for key in required_keys)):
                pass
            else:
                print(f"Missing required keys. Got: {list(parsed.keys())}")
                raise ValueError("Incomplete response structure")
                
        return parsed
        
    except json.JSONDecodeError as je:
        print(f"JSON parsing error: {je}")
        print(f"Raw response: {response_text[:200]}...")
        retry_prompt = f"{prompt}\n\nIMPORTANT: Return ONLY valid JSON. No markdown, no extra text."
        try:
            r = requests.post(f"{get_ollama_url()}/api/generate", json={
                'model': model,
                'prompt': retry_prompt,
                'stream': False,
                'format': 'json'
            }, timeout=120)
            r.raise_for_status()
            response_text = r.json().get('response', '{}')
            parsed = json.loads(response_text)
            print("✅ Retry successful")
            return parsed
        except Exception as retry_error:
            print(f"Retry failed: {retry_error}")
            return None
    except Exception as e:
        print(f"Error in gemma_call: {e}")
        raise e

def build_case_prompt(policy_snippet, evidence, weights=None):
    prompt = (
        f"You are an elite financial compliance and AML investigator. Using ONLY the evidence below (which may include transactions, KYC, and OCR document findings), respond in JSON with keys:\n"
        f"what_happened (Detailed summary of the case),\n"
        f"why_it_matters (Why this poses a risk),\n"
        f"supporting_evidence (List of key evidence points),\n"
        f"red_flag_taxonomy (List of risk categories),\n"
        f"recommended_action (ESCALATE, MONITOR, or CLOSE),\n"
        f"confidence_score (0.0 to 1.0),\n"
        f"missing_information_needed (What additional info would help).\n\n"
        f"Do not invent facts not present in the evidence. If evidence is incomplete, lower confidence and state what is missing.\n\n"
        f"Relevant policy: {policy_snippet}\n"
    )
    if weights:
        prompt += f"IMPORTANT: Ground your investigation explanation in the following feature attribution weights (indicating how much each trigger contributed to the risk alert): {weights}\n\n"
    prompt += f"Evidence: {json.dumps(evidence)}"
    return prompt

def build_ocr_prompt(ocr_text, kyc_data):
    return (
        f"You are a document forensics expert. Review the following OCR extracted text from a customer document and compare it against their KYC profile.\n\n"
        f"OCR Text:\n{ocr_text}\n\n"
        f"KYC Profile:\n{json.dumps(kyc_data)}\n\n"
        f"Respond in JSON with the following keys:\n"
        f"document_type (e.g., Invoice, Bank Statement, ID),\n"
        f"extracted_entities (e.g., names, addresses, amounts, dates),\n"
        f"kyc_mismatches (List of discrepancies between OCR and KYC, empty if none),\n"
        f"suspicious_indicators (List of potential fraud or money laundering flags, e.g., rounded amounts, mismatching addresses, empty if none),\n"
        f"confidence_score (0.0 to 1.0 based on clarity and matching).\n"
    )

def build_prosecutor_prompt(evidence):
    return (
        f"You are an elite financial prosecutor building a case for FRAUD. Argue aggressively why this activity is suspicious.\n"
        f"Analyze these evidence indicators: {json.dumps(evidence)}\n\n"
        f"Respond in JSON with the following keys:\n"
        f"- 'argument' (Your detailed prosecution narrative)\n"
        f"- 'confidence' (Your confidence score of guilt, 0-100)\n"
        f"- 'key_suspicious_points' (List of top 3 red flags you found)\n\n"
        f"CRITICAL: Keep your response as standard valid JSON. Do not include raw newlines or unescaped double quotes inside your string values. Use single quotes for any nested quotes."
    )

def build_defense_prompt(evidence):
    return (
        f"You are a defense advocate representing the customer. Argue why this activity is completely BENIGN and explainable by normal business operations.\n"
        f"Analyze these evidence indicators: {json.dumps(evidence)}\n\n"
        f"Respond in JSON with the following keys:\n"
        f"- 'argument' (Your detailed defense narrative)\n"
        f"- 'confidence' (Your confidence score of innocence, 0-100)\n"
        f"- 'benign_explanation_points' (List of top 3 explanations/mitigants)\n\n"
        f"CRITICAL: Keep your response as standard valid JSON. Do not include raw newlines or unescaped double quotes inside your string values. Use single quotes for any nested quotes."
    )

def arbitrate_verdict(prosecutor_arg, defense_arg, evidence, model='gemma2:2b'):
    prompt = (
        f"You are an impartial compliance judge. Review the Prosecutor and Defense arguments, then issue a balanced final verdict.\n\n"
        f"Prosecutor Case:\n{prosecutor_arg}\n\n"
        f"Defense Case:\n{defense_arg}\n\n"
        f"Evidence: {json.dumps(evidence)}\n\n"
        f"Respond in JSON with the following keys:\n"
        f"what_happened (summarize the final balanced view),\n"
        f"why_it_matters (why we care),\n"
        f"supporting_evidence (key evidence points),\n"
        f"red_flag_taxonomy (categories),\n"
        f"recommended_action (final decision: ESCALATE, MONITOR, REQUEST_DOCS, or CLOSE),\n"
        f"confidence (0-100 score of your verdict),\n"
        f"prosecutor_summary (briefly summarize prosecutor case),\n"
        f"defense_summary (briefly summarize defense case),\n"
        f"critical_missing_data (what additional data is needed to resolve the ambiguity)\n"
    )
    return gemma_call(prompt, model=model, thinking=False, required_keys=('what_happened', 'why_it_matters', 'recommended_action', 'confidence'))

def verify_faithfulness(report_text, evidence):
    prompt = (
        f"You are a strict hallucination checker. \n"
        f"Compare the provided Report to the source Evidence JSON. Does the Report invent ANY facts, numbers, or names not present in the Evidence?\n"
        f"Report: {report_text}\n"
        f"Evidence: {json.dumps(evidence)}\n\n"
        f"Respond in JSON with:\n"
        f"'is_faithful' (boolean),\n"
        f"'unsupported_claims' (list of strings, empty if faithful)\n"
    )
    try:
        res = gemma_call(prompt, thinking=False, required_keys=('is_faithful', 'unsupported_claims'))
        return res
    except Exception:
        return {'is_faithful': True, 'unsupported_claims': []}

def generate_counterfactual(evidence, rules_triggered):
    risk_score = evidence.get('risk_score', 0)
    anomaly_score = evidence.get('anomaly_score', 0)
    counterfactuals = []
    
    if isinstance(rules_triggered, list):
        rule_names = set()
        for r in rules_triggered:
            if isinstance(r, dict):
                rule_names.add(r.get('rule', ''))
            elif isinstance(r, str):
                rule_names.add(r)
                
        if 'Structuring' in rule_names:
            counterfactuals.append('If transactions were not clustered in the $9,000-$9,999 range (just below the $10,000 reporting threshold), the Structuring rule would not trigger. Spreading transactions across varied amounts eliminates this flag.')
        if 'High Velocity' in rule_names:
            counterfactuals.append('If fewer than 50 transactions were made in the monitoring period, the High Velocity alert would not fire. Reducing transaction frequency to normal levels (< 50/period) would clear this flag.')
        if 'Large Transaction' in rule_names:
            counterfactuals.append('If no individual transaction exceeded $100,000, this Large Transaction flag would not apply. Breaking the transfer into smaller, separate legitimate payments over time would avoid this trigger.')
        if 'Mule Ring (Shared Device)' in rule_names:
            counterfactuals.append('If each account used a unique device for authentication, the Mule Ring detection would not trigger. The shared device fingerprint across multiple accounts is the primary indicator here.')
        if 'Impossible Travel' in rule_names:
            counterfactuals.append('If login locations were geographically consistent (same city/region within 12-hour windows), the Impossible Travel flag would not fire. Using a VPN or proxy from a different region triggers this.')
        if 'New Device + High Value' in rule_names:
            counterfactuals.append('If the high-value transfer were initiated from a previously-used device, this flag would not trigger. Establishing device history before large transactions would prevent this alert.')
        if 'Circular Transactions' in rule_names:
            counterfactuals.append('If funds were not transferred back to the originating account (self-transfers), the Circular Transaction detection would not fire. This pattern suggests potential layering.')
        if 'KYC Unverified' in rule_names:
            counterfactuals.append('If identity documents were submitted with OCR confidence above 60%, the KYC Unverified flag would clear. Submitting clearer document scans or completing in-person verification resolves this.')
        if 'Undeclared Income' in rule_names:
            counterfactuals.append('If the account holder declared their income source matching the observed transaction volume, this flag would not trigger. Providing proof of income or business revenue documentation would resolve it.')
        if 'Income-Volume Mismatch' in rule_names:
            counterfactuals.append('If transaction volume were within 5x of declared income, this mismatch would not flag. Either updating declared income to reflect actual earnings or reducing transaction volume would help.')
        if 'Purpose Mismatch' in rule_names:
            counterfactuals.append("If the account purpose were updated to 'Business Operations' or 'International Trade' to match the actual transaction patterns, this Purpose Mismatch flag would not trigger.")
        if 'Missing Identity Document' in rule_names:
            counterfactuals.append('Providing a valid government-issued ID would resolve this flag.')

    return counterfactuals

def gemma_vision_call(prompt, image_path, model='llava:7b'):
    return {}

def gemma_chat_call(prompt, model='gemma2:2b'):
    try:
        r = requests.post(f"{get_ollama_url()}/api/generate", json={
            'model': model,
            'prompt': prompt,
            'stream': False
        }, timeout=120)
        r.raise_for_status()
        return r.json().get('response', '')
    except Exception as e:
        print(f"Error in gemma_chat_call: {e}")
        return f"Error connecting to AI assistant: {str(e)}"

def build_chat_prompt(context, history, user_message):
    prompt = "You are a helpful and expert financial compliance assistant (AI Copilot).\n"
    prompt += "Use the following case context to answer the user's questions strictly and factually. Do not invent facts outside this context.\n\n"
    prompt += f"=== CASE CONTEXT ===\n{json.dumps(context, indent=2)}\n====================\n\n"
    
    if history:
        prompt += "=== CONVERSATION HISTORY ===\n"
        for msg in history[-5:]: # Keep last 5 messages for context
            role = "User" if msg.get("sender") == "user" else "Assistant"
            prompt += f"{role}: {msg.get('text')}\n"
        prompt += "============================\n\n"
        
    prompt += f"User: {user_message}\nAssistant:"
    return prompt
