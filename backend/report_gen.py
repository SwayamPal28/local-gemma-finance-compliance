import sqlite3
import json
import os
import datetime
from fpdf import FPDF

class ComplianceReportPDF(FPDF):
    """Custom PDF class for AML Compliance Reports."""
    
    def header(self):
        self.set_font('Helvetica', 'B', 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, 'VERITAS AML | CONFIDENTIAL COMPLIANCE REPORT', align='C')
        self.ln(4)
        self.set_draw_color(0, 123, 255)
        self.set_line_width(0.8)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(6)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f'Page {self.page_no()}/{{nb}} | Generated {datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")} | PIN-PROTECTED', align='C')

    def section_title(self, title):
        self.set_font('Helvetica', 'B', 13)
        self.set_text_color(0, 90, 200)
        self.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(0, 90, 200)
        self.set_line_width(0.4)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def section_body(self, text):
        self.set_font('Helvetica', '', 10)
        self.set_text_color(30, 30, 30)
        self.multi_cell(0, 6, text)
        self.ln(3)

    def key_value(self, key, value):
        self.set_font('Helvetica', 'B', 10)
        self.set_text_color(60, 60, 60)
        self.cell(55, 7, key + ":")
        self.set_font('Helvetica', '', 10)
        self.set_text_color(30, 30, 30)
        self.cell(0, 7, str(value), new_x="LMARGIN", new_y="NEXT")

    def badge(self, label, color):
        r, g, b = color
        self.set_fill_color(r, g, b)
        self.set_text_color(255, 255, 255)
        self.set_font('Helvetica', 'B', 11)
        w = self.get_string_width(label) + 12
        self.cell(w, 8, label, fill=True, align='C')
        self.set_text_color(30, 30, 30)
        self.ln(10)

    def bar_chart(self, data, max_val=1.0):
        """Draw simple horizontal bars for feature attributions."""
        bar_max_w = 100
        for name, val in data.items():
            self.set_font('Helvetica', '', 9)
            self.set_text_color(60, 60, 60)
            display_name = name.replace('_', ' ').title()
            self.cell(55, 7, display_name)
            
            pct = (val / max_val) * 100 if max_val > 0 else 0
            bar_w = (pct / 100) * bar_max_w
            
            y = self.get_y()
            x = self.get_x()
            # Background bar
            self.set_fill_color(230, 230, 230)
            self.rect(x, y + 1, bar_max_w, 5, 'F')
            # Value bar
            self.set_fill_color(0, 123, 255)
            if bar_w > 0:
                self.rect(x, y + 1, bar_w, 5, 'F')
            
            self.set_x(x + bar_max_w + 3)
            self.set_font('Helvetica', 'B', 9)
            self.set_text_color(0, 90, 200)
            self.cell(0, 7, f"{val:.2f}", new_x="LMARGIN", new_y="NEXT")
        self.ln(3)


def generate_report_pdf(case_id, tenant_id, pin=None):
    """Generate a properly formatted PDF compliance report, optionally encrypted with a PIN."""
    conn = sqlite3.connect('compliance.db', timeout=10)
    conn.row_factory = sqlite3.Row
    report = conn.execute("SELECT * FROM gemma_reports WHERE case_id = ? AND tenant_id = ?", (case_id, tenant_id)).fetchone()
    case = conn.execute("SELECT * FROM case_scores WHERE case_id = ? AND tenant_id = ?", (case_id, tenant_id)).fetchone()
    kyc = None
    if case:
        kyc = conn.execute("SELECT * FROM kyc_records WHERE account_id = ?", (case['account_id'],)).fetchone()
    conn.close()

    # Convert sqlite3.Row objects to plain dicts for .get() support
    report = dict(report) if report else None
    case = dict(case) if case else None
    kyc = dict(kyc) if kyc else None

    pdf = ComplianceReportPDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # ─── Title Block ───
    pdf.set_font('Helvetica', 'B', 20)
    pdf.set_text_color(0, 50, 120)
    pdf.cell(0, 12, 'Compliance Case Report', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    # ─── Case Overview ───
    pdf.section_title('1. Case Overview')
    pdf.key_value('Case ID', case_id)
    pdf.key_value('Tenant', tenant_id)
    if case:
        risk = case['risk_score']
        pdf.key_value('Account ID', case['account_id'])
        pdf.key_value('Risk Score', f"{risk * 100:.1f}%")
        pdf.key_value('Anomaly Score', f"{case['anomaly_score']:.3f}")
        pdf.key_value('Status', case['status'] or 'NEW')
        pdf.key_value('Assigned Queue', case['assigned_queue'] or 'Triage')
        pdf.ln(2)
        # Risk badge
        if risk >= 0.8:
            pdf.badge('HIGH RISK', (220, 53, 69))
        elif risk >= 0.4:
            pdf.badge('MEDIUM RISK', (255, 165, 0))
        else:
            pdf.badge('LOW RISK', (40, 167, 69))
    pdf.ln(2)

    # ─── KYC Summary ───
    if kyc:
        pdf.section_title('2. KYC Customer Profile')
        pdf.key_value('Customer Name', kyc['name'] or 'Unknown')
        pdf.key_value('Address', kyc['address'] or 'N/A')
        pdf.key_value('Date of Birth', kyc['dob'] or 'N/A')
        pdf.key_value('ID Number', kyc['id_number'] or 'N/A')
        pdf.key_value('Employer', kyc['employer'] or 'N/A')
        pdf.key_value('Declared Income', f"${kyc['declared_income']:,.2f}" if kyc['declared_income'] else 'N/A')
        pdf.key_value('Declared Purpose', kyc['declared_purpose'] or 'N/A')
        try:
            pdf.key_value('Account Type', kyc['account_type'] or 'N/A')
        except (IndexError, KeyError):
            pass
        try:
            pdf.key_value('OCR Confidence', f"{kyc['ocr_confidence']:.1f}%" if kyc['ocr_confidence'] else 'N/A')
        except (IndexError, KeyError):
            pass
        pdf.ln(4)

    # ─── AI Investigation Summary ───
    section_num = 3 if kyc else 2
    pdf.section_title(f'{section_num}. AI Investigation Summary')
    if report:
        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_text_color(60, 60, 60)
        pdf.cell(0, 7, 'Confidence Score:', new_x="LMARGIN", new_y="NEXT")
        conf = report['confidence']
        if conf >= 0.8:
            pdf.badge(f"{conf * 100:.0f}% CONFIDENCE", (40, 167, 69))
        elif conf >= 0.5:
            pdf.badge(f"{conf * 100:.0f}% CONFIDENCE", (255, 165, 0))
        else:
            pdf.badge(f"{conf * 100:.0f}% CONFIDENCE", (220, 53, 69))
        pdf.ln(2)

        pdf.set_font('Helvetica', 'B', 11)
        pdf.set_text_color(0, 70, 140)
        pdf.cell(0, 8, 'What Happened', new_x="LMARGIN", new_y="NEXT")
        pdf.section_body(report['what_happened'] or 'N/A')

        pdf.set_font('Helvetica', 'B', 11)
        pdf.set_text_color(0, 70, 140)
        pdf.cell(0, 8, 'Why It Matters', new_x="LMARGIN", new_y="NEXT")
        pdf.section_body(report['why_it_matters'] or 'N/A')

        pdf.set_font('Helvetica', 'B', 11)
        pdf.set_text_color(0, 70, 140)
        pdf.cell(0, 8, 'Recommended Action', new_x="LMARGIN", new_y="NEXT")
        action = (report['recommended_action'] or 'N/A').upper()
        if 'ESCALATE' in action:
            pdf.badge(action, (220, 53, 69))
        elif 'MONITOR' in action:
            pdf.badge(action, (255, 165, 0))
        else:
            pdf.badge(action, (40, 167, 69))
        pdf.ln(2)

        # Missing info
        missing = report.get('missing_information_needed', '') or ''
        if missing and missing.strip() and missing.strip().lower() != 'none' and missing.strip().lower() != 'none.':
            pdf.set_font('Helvetica', 'B', 11)
            pdf.set_text_color(200, 120, 0)
            pdf.cell(0, 8, 'Missing Information Needed', new_x="LMARGIN", new_y="NEXT")
            pdf.section_body(missing)
    else:
        pdf.section_body('No AI report has been generated yet for this case. Please generate a report from the Case Investigation tab first.')

    # ─── XAI Feature Attribution ───
    fa_raw = None
    if report:
        try:
            fa_raw = report['feature_attributions']
        except (IndexError, KeyError):
            pass
    
    fa = {}
    if fa_raw:
        try:
            fa = json.loads(fa_raw) if isinstance(fa_raw, str) else fa_raw
        except Exception:
            pass

    if fa and len(fa) > 0:
        section_num += 1
        pdf.section_title(f'{section_num}. Explainable AI (XAI) Feature Attribution')
        pdf.section_body('The following chart shows the normalized contribution weight of each triggered rule relative to the final risk score:')
        max_val = max(fa.values()) if fa.values() else 1.0
        pdf.bar_chart(fa, max_val=max_val)

    # ─── Triggered Rules ───
    if case:
        try:
            rule_flags = json.loads(case.get('rule_flags', '[]') or '[]')
            if rule_flags and len(rule_flags) > 0:
                section_num += 1
                pdf.section_title(f'{section_num}. Triggered Rules')
                for i, rule in enumerate(rule_flags, 1):
                    if isinstance(rule, dict):
                        rule_name = rule.get('rule', 'Unknown')
                        rule_detail = rule.get('detail', rule.get('details', ''))
                        pdf.set_font('Helvetica', 'B', 10)
                        pdf.set_text_color(220, 53, 69)
                        pdf.cell(0, 7, f"  {i}. {rule_name}", new_x="LMARGIN", new_y="NEXT")
                        if rule_detail:
                            pdf.set_font('Helvetica', '', 9)
                            pdf.set_text_color(80, 80, 80)
                            pdf.multi_cell(0, 5, f"     {rule_detail}")
                            pdf.ln(2)
                    elif isinstance(rule, str):
                        pdf.set_font('Helvetica', 'B', 10)
                        pdf.set_text_color(220, 53, 69)
                        pdf.cell(0, 7, f"  {i}. {rule}", new_x="LMARGIN", new_y="NEXT")
                pdf.ln(3)
        except Exception:
            pass

    # ─── Disclaimer ───
    section_num += 1
    pdf.section_title(f'{section_num}. Disclaimer')
    pdf.set_font('Helvetica', 'I', 9)
    pdf.set_text_color(120, 120, 120)
    pdf.multi_cell(0, 5, (
        'This report was automatically generated by the Veritas AML intelligent compliance assistant using the Gemma language model. '
        'The analysis is based on available transaction data, KYC records, and OCR document findings at the time of generation. '
        'This report is intended to assist human compliance analysts and should not be treated as a final regulatory determination. '
        'All findings must be independently verified by a qualified compliance officer before any enforcement action is taken.'
    ))

    # ─── Save the PDF ───
    raw_path = f"{case_id}_report.pdf"
    pdf.output(raw_path)

    # ─── Encrypt with PIN if provided ───
    if pin:
        try:
            from PyPDF2 import PdfReader, PdfWriter
            reader = PdfReader(raw_path)
            writer = PdfWriter()
            for page in reader.pages:
                writer.add_page(page)
            writer.encrypt(user_password=str(pin), owner_password=str(pin), use_128bit=True)
            encrypted_path = f"{case_id}_report_secured.pdf"
            with open(encrypted_path, 'wb') as f:
                writer.write(f)
            # Clean up unencrypted version
            os.remove(raw_path)
            print(f"PIN-protected compliance report generated for {case_id}")
            return encrypted_path
        except Exception as e:
            print(f"Encryption failed, returning unencrypted PDF: {e}")
            return raw_path
    
    print(f"Compliance report generated for {case_id}")
    return raw_path
