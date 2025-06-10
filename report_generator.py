# report_generator.py
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.platypus.tableofcontents import TableOfContents
from datetime import datetime
from pathlib import Path
from typing import Dict

from models import AnalysisRequest, AnalysisReport
from config import Config

class ReportGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()
        
    def setup_custom_styles(self):
        """Define custom styles for the report"""
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Title'],
            fontSize=24,
            textColor=colors.HexColor('#1a472a'),
            spaceAfter=30
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionHeading',
            parent=self.styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#1a472a'),
            spaceAfter=12
        ))
        
        self.styles.add(ParagraphStyle(
            name='SubHeading',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#2d5016'),
            spaceAfter=10
        ))
        
    def generate_report(self, request: AnalysisRequest, analysis_result: Dict) -> Path:
        """Generate PDF report from analysis results"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"archopinion_report_{timestamp}.pdf"
        filepath = Config.OUTPUT_DIR / filename
        
        doc = SimpleDocTemplate(
            str(filepath),
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        
        # Build the story
        story = []
        
        # Title Page
        story.append(Paragraph("ARCHOPINION", self.styles['CustomTitle']))
        story.append(Paragraph("AI Architectural Review Report", self.styles['Heading2']))
        story.append(Spacer(1, 1*cm))
        
        # Project Information
        story.append(Paragraph("Project Information", self.styles['SectionHeading']))
        project_data = [
            ["Address:", request.project_info.address],
            ["Project Type:", request.project_info.project_type],
            ["Local Authority:", request.project_info.council or "Not specified"],
            ["Planning Reference:", request.project_info.planning_reference or "None"],
            ["Analysis Date:", datetime.now().strftime("%d %B %Y")]
        ]
        
        project_table = Table(project_data, colWidths=[5*cm, 12*cm])
        project_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
        ]))
        story.append(project_table)
        story.append(Spacer(1, 1*cm))
        
        # AI Review Framework
        story.append(Paragraph("Regulatory Framework Analysis", self.styles['SectionHeading']))
        for framework in analysis_result.get('aiReviewFramework', []):
            story.append(Paragraph(framework['framework'], self.styles['SubHeading']))
            story.append(Paragraph(f"<b>Key Considerations:</b> {framework['keyConsiderations']}", 
                                 self.styles['Normal']))
            
            policies_text = "Relevant Policies: " + ", ".join(framework['relevantPolicies'])
            story.append(Paragraph(policies_text, self.styles['Normal']))
            story.append(Spacer(1, 0.5*cm))
        
        # Plan by Plan Review
        story.append(PageBreak())
        story.append(Paragraph("Plan-by-Plan Review", self.styles['SectionHeading']))
        
        for plan in analysis_result.get('planByPlanReview', []):
            story.append(Paragraph(plan['planType'], self.styles['SubHeading']))
            
            # Positives
            story.append(Paragraph("<b>Positives:</b>", self.styles['Normal']))
            for positive in plan['positives']:
                story.append(Paragraph(f"• {positive}", self.styles['Normal']))
            story.append(Spacer(1, 0.3*cm))
            
            # Observations
            story.append(Paragraph("<b>Areas for Consideration:</b>", self.styles['Normal']))
            for observation in plan['observations']:
                story.append(Paragraph(f"• {observation}", self.styles['Normal']))
            story.append(Spacer(1, 0.3*cm))
            
            # Compliance Notes
            story.append(Paragraph(f"<b>Compliance Notes:</b> {plan['complianceNotes']}", 
                                 self.styles['Normal']))
            story.append(Spacer(1, 0.5*cm))
        
        # Policy Compatibility Summary
        story.append(PageBreak())
        story.append(Paragraph("Policy Compatibility Summary", self.styles['SectionHeading']))
        
        # Create summary table
        summary_data = [["Policy Area", "Status", "Details"]]
        for policy in analysis_result.get('policyCompatibilitySummary', []):
            status = policy['status']
            # Color code status
            if status == "Compliant":
                status_color = colors.green
            elif status == "Partially Compliant":
                status_color = colors.orange
            else:
                status_color = colors.red
                
            summary_data.append([
                policy['policyArea'],
                policy['status'],
                policy['details'][:100] + "..." if len(policy['details']) > 100 else policy['details']
            ])
        
        summary_table = Table(summary_data, colWidths=[4*cm, 3*cm, 10*cm])
        summary_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a472a')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 1*cm))
        
        # Detailed Policy Analysis
        for policy in analysis_result.get('policyCompatibilitySummary', []):
            story.append(Paragraph(policy['policyArea'], self.styles['SubHeading']))
            story.append(Paragraph(f"<b>Status:</b> {policy['status']}", self.styles['Normal']))
            story.append(Paragraph(f"<b>Details:</b> {policy['details']}", self.styles['Normal']))
            
            if policy.get('recommendations'):
                story.append(Paragraph("<b>Recommendations:</b>", self.styles['Normal']))
                for rec in policy['recommendations']:
                    story.append(Paragraph(f"• {rec}", self.styles['Normal']))
            story.append(Spacer(1, 0.5*cm))
        
        # AI Recommendations Summary
        story.append(PageBreak())
        story.append(Paragraph("AI Recommendations Summary", self.styles['SectionHeading']))
        
        summary_text = analysis_result.get('aiRecommendationSummary', '')
        # Split into paragraphs
        for para in summary_text.split('\n\n'):
            if para.strip():
                story.append(Paragraph(para, self.styles['Normal']))
                story.append(Spacer(1, 0.3*cm))
        
        # Disclaimer
        story.append(Spacer(1, 2*cm))
        disclaimer_style = ParagraphStyle(
            'Disclaimer',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.grey
        )
        disclaimer_text = """
        <b>Disclaimer:</b> This AI-generated report is for informational purposes only and should not be considered 
        as professional architectural or planning advice. Always consult with qualified professionals and your 
        local planning authority before proceeding with any development.
        """
        story.append(Paragraph(disclaimer_text, disclaimer_style))
        
        # Build PDF
        doc.build(story)
        return filepath