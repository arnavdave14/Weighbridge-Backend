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
        
        # Dynamic Fields
        pdf.set_font("Helvetica", "", 10)
        custom_data = receipt.custom_data or {}
        
        # Create a list of fields excluding remarks
        fields = [(k, v) for k, v in custom_data.items() if k.lower() != 'remarks']
        
        for i in range(0, len(fields), 2):
            k1, v1 = fields[i]
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(40, 8, f"{k1.upper()} : ", ln=False)
            pdf.set_font("Helvetica", "", 10)
            pdf.cell(50, 8, str(v1), ln=False)
            
            if i + 1 < len(fields):
                k2, v2 = fields[i+1]
                pdf.set_font("Helvetica", "B", 10)
                pdf.cell(40, 8, f"{k2.upper()} : ", ln=False)
                pdf.set_font("Helvetica", "", 10)
                pdf.cell(0, 8, str(v2), ln=True)
            else:
                pdf.ln(8)
                
        # rate/charges
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(40, 8, "CHARGES : ", ln=False)
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 8, f"Rs. {float(receipt.rate or 0):.2f}", ln=True)
        
        pdf.ln(2)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)
        
        # Weight Details
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(60, 10, f"GROSS WEIGHT : {float(receipt.gross_weight):.2f} KG", ln=True)
        pdf.cell(60, 10, f"TARE WEIGHT  : {float(receipt.tare_weight):.2f} KG", ln=True)
        
        net_weight = abs(float(receipt.gross_weight) - float(receipt.tare_weight))
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(60, 10, f"NET WEIGHT   : {net_weight:.2f} KG", ln=True)
        
        pdf.ln(5)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)
        
        # Remarks
        if custom_data.get("remarks"):
            pdf.set_font("Helvetica", "I", 10)
            pdf.multi_cell(0, 8, f"Remarks: {custom_data['remarks']}")
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
