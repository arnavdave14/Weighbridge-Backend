from fpdf import FPDF
from datetime import datetime
from typing import Dict, Any, List
from app.models.models import Receipt, Machine
import json

class PDFService:
    @staticmethod
    def generate_receipt_pdf(receipt: Receipt, machine: Machine = None) -> bytes:
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        
        # Load settings from machine if available
        settings = machine.settings if machine and machine.settings else {}
        
        # Header
        pdf.set_font("Helvetica", "B", 16)
        if settings.get("header1"):
            pdf.cell(0, 10, str(settings["header1"]).upper(), ln=True, align="C")
        
        pdf.set_font("Helvetica", "", 10)
        if settings.get("header2"):
            pdf.multi_cell(0, 5, str(settings["header2"]), align="C")
        if settings.get("header3"):
            pdf.multi_cell(0, 5, str(settings["header3"]), align="C")
        
        pdf.ln(5)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(2)
        
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 10, "WEIGHMENT TICKET", ln=True, align="C")
        pdf.ln(2)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)
        
        # RST and Date
        pdf.set_font("Helvetica", "B", 10)
        formatted_date = receipt.date_time.strftime("%d/%m/%Y")
        formatted_time = receipt.date_time.strftime("%I:%M %p")
        
        pdf.cell(100, 8, f"RST NO : {str(receipt.local_id).zfill(5)}", ln=False)
        pdf.cell(0, 8, f"DATE : {formatted_date}", ln=True, align="R")
        
        pdf.ln(2)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)
        
        # --- Core Data Extraction ---
        # Strategy: Use payload_json["data"] if available, fallback to legacy fields
        payload = receipt.payload_json or {}
        data = payload.get("data", {})
        
        # Fallback logic for legacy receipts not yet migrated or if payload is empty
        gross = data.get("gross", receipt.gross_weight or 0)
        tare = data.get("tare", receipt.tare_weight or 0)
        net = data.get("net", (float(gross) - float(tare)))
        rate = data.get("rate", receipt.rate or 0)
        
        # Collect dynamic fields (everything in data except core weights)
        core_keys = {"gross", "tare", "net", "rate", "remarks"}
        dynamic_fields = [(k, v) for k, v in data.items() if k.lower() not in core_keys]
        
        # If dynamic_fields is empty, fallback to old custom_data
        if not dynamic_fields and receipt.custom_data:
            dynamic_fields = [(k, v) for k, v in receipt.custom_data.items() if k.lower() != 'remarks']

        # Render dynamic fields in 2 columns
        pdf.set_font("Helvetica", "", 10)
        for i in range(0, len(dynamic_fields), 2):
            k1, v1 = dynamic_fields[i]
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(40, 8, f"{str(k1).replace('_', ' ').upper()} : ", ln=False)
            pdf.set_font("Helvetica", "", 10)
            pdf.cell(50, 8, str(v1), ln=False)
            
            if i + 1 < len(dynamic_fields):
                k2, v2 = dynamic_fields[i+1]
                pdf.set_font("Helvetica", "B", 10)
                pdf.cell(40, 8, f"{str(k2).replace('_', ' ').upper()} : ", ln=False)
                pdf.set_font("Helvetica", "", 10)
                pdf.cell(0, 8, str(v2), ln=True)
            else:
                pdf.ln(8)
                
        # Charges
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(40, 8, "CHARGES : ", ln=False)
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 8, f"Rs. {float(rate):.2f}", ln=True)
        
        pdf.ln(2)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)
        
        # Weight Details
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(60, 10, f"GROSS WEIGHT : {float(gross):.2f} KG", ln=True)
        pdf.cell(60, 10, f"TARE WEIGHT  : {float(tare):.2f} KG", ln=True)
        
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(60, 10, f"NET WEIGHT   : {float(net):.2f} KG", ln=True)
        
        pdf.ln(5)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)
        
        # Remarks
        remarks = data.get("remarks") or (receipt.custom_data.get("remarks") if receipt.custom_data else None)
        if remarks:
            pdf.set_font("Helvetica", "I", 10)
            pdf.multi_cell(0, 8, f"Remarks: {remarks}")
            pdf.ln(5)
            
        # Footer
        pdf.set_y(-40)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(90, 10, "DRIVER SIGNATURE", ln=False, align="L")
        pdf.cell(0, 10, "OPERATOR SIGNATURE", ln=True, align="R")
        
        if settings.get("footer"):
            pdf.set_font("Helvetica", "I", 8)
            pdf.set_y(-20)
            pdf.cell(0, 10, str(settings["footer"]), ln=True, align="C")
            
        return pdf.output()
