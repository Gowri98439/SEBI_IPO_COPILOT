import io
import json
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.platypus.doctemplate import BaseDocTemplate, PageTemplate
from reportlab.platypus.frames import Frame

class ReportService:
    @staticmethod
    def _create_footer(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 9)
        canvas.setFillColor(colors.gray)
        canvas.drawString(40, 20, f"IPO Copilot AI - Confidential & Proprietary | Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        canvas.drawRightString(letter[0] - 40, 20, f"Page {doc.page}")
        canvas.restoreState()

    @staticmethod
    def generate_workspace_report(workspace, company, documents, compliance_checks, validation_results, audit_events) -> bytes:
        buffer = io.BytesIO()
        
        # Define PageTemplate with footer
        frame = Frame(40, 40, letter[0] - 80, letter[1] - 80, id='normal')
        template = PageTemplate(id='test', frames=frame, onPage=ReportService._create_footer)
        
        doc = BaseDocTemplate(
            buffer, pagesize=letter,
            rightMargin=40, leftMargin=40,
            topMargin=40, bottomMargin=40
        )
        doc.addPageTemplates([template])

        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='CoverTitle', fontSize=28, leading=32, spaceAfter=30, textColor=colors.HexColor('#002b49'), alignment=1))
        styles.add(ParagraphStyle(name='CoverSubtitle', fontSize=18, leading=22, spaceAfter=20, textColor=colors.HexColor('#004f86'), alignment=1))
        styles.add(ParagraphStyle(name='Heading1', fontSize=18, leading=22, spaceAfter=15, textColor=colors.HexColor('#002b49')))
        styles.add(ParagraphStyle(name='Heading2', fontSize=14, leading=18, spaceAfter=10, textColor=colors.HexColor('#004f86')))
        styles.add(ParagraphStyle(name='Heading3', fontSize=12, leading=14, spaceAfter=8, textColor=colors.HexColor('#333333')))
        styles.add(ParagraphStyle(name='NormalStyle', fontSize=10, leading=14, spaceAfter=10))

        elements = []

        # -----------------------------------------------------
        # 1. Cover Page
        # -----------------------------------------------------
        elements.append(Spacer(1, 150))
        elements.append(Paragraph("IPO Copilot AI", styles['CoverTitle']))
        elements.append(Paragraph("Executive Compliance Report", styles['CoverSubtitle']))
        elements.append(Spacer(1, 50))
        elements.append(Paragraph(f"<b>Workspace:</b> {workspace.name}", styles['CoverSubtitle']))
        elements.append(Paragraph(f"<b>Company:</b> {company.name if company else 'N/A'}", styles['CoverSubtitle']))
        elements.append(Spacer(1, 100))
        elements.append(Paragraph(f"<b>Date:</b> {datetime.now().strftime('%Y-%m-%d')}", styles['CoverSubtitle']))
        elements.append(PageBreak())

        # -----------------------------------------------------
        # 2. Executive Summary
        # -----------------------------------------------------
        elements.append(Paragraph("Executive Summary", styles['Heading1']))
        if workspace.executive_summary:
            try:
                summary_data = json.loads(workspace.executive_summary)
                elements.append(Paragraph(f"<b>Executive Overview:</b> {summary_data.get('executive_overview', 'N/A')}", styles['NormalStyle']))
                elements.append(Paragraph(f"<b>Estimated Filing Readiness:</b> {summary_data.get('estimated_filing_readiness', 0)}%", styles['NormalStyle']))
                
                elements.append(Paragraph("<b>Business Risks:</b>", styles['NormalStyle']))
                for risk in summary_data.get('business_risks', []):
                    elements.append(Paragraph(f"• {risk}", styles['NormalStyle']))

                elements.append(Paragraph("<b>Compliance Gaps:</b>", styles['NormalStyle']))
                for gap in summary_data.get('compliance_gaps', []):
                    elements.append(Paragraph(f"• {gap}", styles['NormalStyle']))

                elements.append(Paragraph("<b>Priority Actions:</b>", styles['NormalStyle']))
                for action in summary_data.get('priority_actions', []):
                    elements.append(Paragraph(f"• {action}", styles['NormalStyle']))
            except Exception:
                elements.append(Paragraph(str(workspace.executive_summary), styles['NormalStyle']))
        else:
            elements.append(Paragraph("No executive summary generated yet.", styles['NormalStyle']))
        
        elements.append(PageBreak())

        # -----------------------------------------------------
        # 3. Compliance Matrix (Table with color coding)
        # -----------------------------------------------------
        elements.append(Paragraph("Compliance Matrix", styles['Heading1']))
        passed = sum(1 for c in compliance_checks if c.status == 'pass')
        failed = sum(1 for c in compliance_checks if c.status == 'fail')
        warnings = sum(1 for c in compliance_checks if c.status == 'warning')
        elements.append(Paragraph(f"Total Checks: {len(compliance_checks)} | Passed: {passed} | Failed: {failed} | Warnings: {warnings}", styles['NormalStyle']))
        
        if compliance_checks:
            data = [["Regulation / Title", "Status", "Confidence"]]
            table_styles = [
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#002b49')),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0,0), (-1,0), 12),
                ('GRID', (0,0), (-1,-1), 1, colors.black),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ]
            
            for idx, c in enumerate(compliance_checks, start=1):
                status_str = c.status.upper()
                bg_color = colors.white
                if c.status == 'pass':
                    bg_color = colors.HexColor('#e6f4ea') # light green
                elif c.status == 'fail':
                    bg_color = colors.HexColor('#fce8e6') # light red
                elif c.status == 'warning':
                    bg_color = colors.HexColor('#fef7e0') # light yellow
                    
                title_text = f"{c.regulation}"
                
                data.append([
                    Paragraph(title_text, styles['NormalStyle']),
                    status_str,
                    f"{int(c.confidence_score * 100)}%" if c.confidence_score else "N/A"
                ])
                # Add background color for the row
                table_styles.append(('BACKGROUND', (0, idx), (-1, idx), bg_color))

            t = Table(data, colWidths=[350, 100, 80])
            t.setStyle(TableStyle(table_styles))
            elements.append(t)
        
        elements.append(PageBreak())

        # -----------------------------------------------------
        # 4. Detailed Findings
        # -----------------------------------------------------
        elements.append(Paragraph("Detailed Findings", styles['Heading1']))
        for c in compliance_checks:
            if c.status != 'pass':
                elements.append(Paragraph(f"Rule: {c.regulation}", styles['Heading2']))
                elements.append(Paragraph(f"<b>Status:</b> {c.status.upper()}", styles['NormalStyle']))
                elements.append(Paragraph(f"<b>Confidence:</b> {int(c.confidence_score * 100)}%" if c.confidence_score else "<b>Confidence:</b> N/A", styles['NormalStyle']))
                elements.append(Paragraph("<b>AI Reasoning:</b>", styles['Heading3']))
                elements.append(Paragraph(c.ai_reasoning or "No reasoning provided.", styles['NormalStyle']))
                elements.append(Spacer(1, 15))
        
        elements.append(PageBreak())

        # -----------------------------------------------------
        # 5. Appendix (Audit Trail)
        # -----------------------------------------------------
        elements.append(Paragraph("Appendix A: Audit Trail", styles['Heading1']))
        if audit_events:
            data = [["Timestamp", "Action", "Status", "User IP"]]
            for evt in audit_events[:30]:
                dt_str = evt.created_at.strftime("%Y-%m-%d %H:%M") if evt.created_at else "N/A"
                data.append([dt_str, evt.action, evt.status, evt.ip_address or "N/A"])
            
            t = Table(data, colWidths=[100, 240, 80, 110])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#002b49')),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('GRID', (0,0), (-1,-1), 1, colors.black),
                ('FONTSIZE', (0,0), (-1,-1), 8),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ]))
            elements.append(t)
        else:
            elements.append(Paragraph("No audit events found.", styles['NormalStyle']))

        doc.build(elements)
        
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes
