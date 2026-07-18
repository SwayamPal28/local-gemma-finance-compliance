import sqlite3
import difflib
import json
import gemma_client

def init_sanctions_table(conn):
    """Creates and seeds a mock sanctions list in compliance.db if it does not exist."""
    conn.execute("""
    CREATE TABLE IF NOT EXISTS sanctions_list (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        country TEXT,
        sdn_number TEXT,
        reason TEXT
    )
    """)
    # Seed mock data
    mock_sdns = [
        ("Mohammad Hussaini", "Syria", "SDN-10291", "Terrorist financing and illicit arms procurement"),
        ("Vladimir Petrov", "Russia", "SDN-39481", "Avoidance of secondary sovereign financial sanctions"),
        ("Maria Santos", "Venezuela", "SDN-40284", "State asset misappropriation and public corruption"),
        ("Li Wei", "North Korea", "SDN-18471", "Dual-use technology and missile procurement networks"),
        ("Samir Al-Fayed", "Iran", "SDN-28491", "State-sponsored cyber espionage and infrastructure hacking")
    ]
    for name, country, sdn, reason in mock_sdns:
        try:
            conn.execute("INSERT INTO sanctions_list (name, country, sdn_number, reason) VALUES (?, ?, ?, ?)",
                         (name, country, sdn, reason))
        except sqlite3.IntegrityError:
            pass
    conn.commit()

def check_sanctions(customer_name, customer_country, conn, model='gemma2:2b'):
    """
    Screens a customer against the sanctions list.
    If similarity ratio > 0.65, triggers Gemma to disambiguate the match.
    """
    init_sanctions_table(conn)
    
    if not customer_name:
        return {"has_match": False}
        
    sdns = conn.execute("SELECT * FROM sanctions_list").fetchall()
    
    best_ratio = 0.0
    best_sdn = None
    
    c_name_lower = customer_name.lower().strip()
    for sdn in sdns:
        sdn_name_lower = sdn['name'].lower().strip()
        # SequenceMatcher fuzzy comparison ratio
        ratio = difflib.SequenceMatcher(None, c_name_lower, sdn_name_lower).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_sdn = sdn
            
    # Trigger Gemma assessment if similarity > 65%
    if best_ratio > 0.65 and best_sdn:
        similarity_pct = int(best_ratio * 100)
        
        prompt = (
            f"You are a sanctions compliance analyst checking transactions for matches against Specially Designated Nationals (SDNs).\n\n"
            f"Customer details:\n"
            f"- Name: {customer_name}\n"
            f"- Country: {customer_country or 'Unknown'}\n\n"
            f"Sanctioned SDN Profile:\n"
            f"- Name: {best_sdn['name']}\n"
            f"- Country: {best_sdn['country']}\n"
            f"- SDN Number: {best_sdn['sdn_number']}\n"
            f"- Sanction Reason: {best_sdn['reason']}\n\n"
            f"Fuzzy match similarity score is: {similarity_pct}%\n\n"
            f"Please assess if this is a plausible match (true positive) or a false positive due to a common name/transliteration overlap.\n"
            f"Respond in JSON with the following keys:\n"
            f"- 'is_true_positive' (boolean)\n"
            f"- 'explanation' (1-2 sentences justifying your choice)\n"
            f"- 'recommended_action' (BLOCK, HOLD, or CLEAR)\n"
        )
        try:
            res = gemma_client.gemma_call(prompt, model=model, thinking=False, required_keys=('is_true_positive', 'explanation'))
            if res:
                is_tp = res.get('is_true_positive', False)
                rec_act = res.get('recommended_action', 'BLOCK' if is_tp else 'HOLD')
                return {
                    "has_match": True,
                    "matched_sdn": best_sdn['name'],
                    "sdn_number": best_sdn['sdn_number'],
                    "sdn_country": best_sdn['country'],
                    "sdn_reason": best_sdn['reason'],
                    "similarity_score": best_ratio,
                    "is_true_positive": is_tp,
                    "gemma_assessment": res.get('explanation', 'Fuzzy match verification completed.'),
                    "recommended_action": rec_act
                }
        except Exception as e:
            print(f"Gemma sanctions verify failed: {e}")
            # Fallback if LLM call fails
            return {
                "has_match": True,
                "matched_sdn": best_sdn['name'],
                "sdn_number": best_sdn['sdn_number'],
                "sdn_country": best_sdn['country'],
                "sdn_reason": best_sdn['reason'],
                "similarity_score": best_ratio,
                "is_true_positive": best_ratio > 0.85, # basic fallback threshold
                "gemma_assessment": f"Fuzzy matching indicates high structural name overlap ({similarity_pct}%). Manual verification recommended.",
                "recommended_action": "BLOCK" if best_ratio > 0.85 else "HOLD"
            }
            
    return {"has_match": False}
