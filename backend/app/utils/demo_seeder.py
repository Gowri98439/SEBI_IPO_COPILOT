import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.company import Company
from app.models.workspace import Workspace
from app.models.document import Document
from app.models.compliance_check import ComplianceCheck
from app.models.validation_result import ValidationResult
from app.models.audit_event import AuditEvent

async def seed_demo_workspace(db: AsyncSession, user_id: str) -> Workspace:
    # 1. Create a dummy company
    company = Company(
        id=str(uuid.uuid4()),
        name="Aarav Manufacturing Solutions Pvt Ltd",
        industry="Precision Engineering",
        created_by=user_id
    )
    db.add(company)
    await db.flush()

    # 2. Create Workspace
    workspace = Workspace(
        id=str(uuid.uuid4()),
        company_id=company.id,
        name="Aarav SME IPO 2026",
        status="in_progress",
        created_by=user_id
    )
    # Add a realistic executive summary matching the new Big 4 schema
    import json
    workspace.executive_summary = json.dumps({  # type: ignore
        "executive_overview": "Aarav Manufacturing Solutions is a profitable precision engineering SME seeking Rs. 24 Crores for capital expenditure and working capital. The company shows strong revenue growth but requires significant compliance remediation before DRHP filing.",
        "business_risks": ["High customer concentration risk (Top 3 clients account for 68% of revenue)", "Volatility in raw material (steel and aluminum) prices"],
        "compliance_gaps": ["Missing restated financial statements for FY23", "Promoter contribution lock-in period incorrectly stated as 2 years instead of 3 years"],
        "critical_missing_information": ["Statutory Auditor's certificate on Promoter Contribution", "Quotations for proposed machinery purchases in Object of Issue"],
        "priority_actions": ["Upload audited financials for FY23-FY25 in SEBI restated format", "Revise Objects of Issue to include exact vendor quotations"],
        "estimated_filing_readiness": 45,
        "top_recommendations": [
            {"action": "Procure Auditor's Certificate for Promoter Contribution", "citation": "ICDR_REG_26_CERT"},
            {"action": "Correct Promoter Lock-in to 3 Years", "citation": "ICDR_REG_28"}
        ]
    })
    db.add(workspace)
    await db.flush()

    base_time = datetime.now(timezone.utc) - timedelta(days=5)

    # 3. Create mock documents
    docs = [
        {"name": "Draft_Red_Herring_Prospectus_v2.pdf", "type": "drhp"},
        {"name": "Aarav_Restated_Financials_FY25.pdf", "type": "financials"},
        {"name": "Promoter_Holding_Structure_Aarav.pdf", "type": "other"}
    ]
    
    doc_ids = []
    for i, d in enumerate(docs):
        doc = Document(
            id=str(uuid.uuid4()),
            workspace_id=workspace.id,
            name=d["name"],
            doc_type=d["type"],
            file_path="/mock/path.pdf",
            file_size=2048576, # 2MB
            mime_type="application/pdf",
            status="validated",
            uploaded_by=user_id,
            created_at=base_time + timedelta(hours=i)
        )
        db.add(doc)
        doc_ids.append(doc.id)
        
        # 4. Validation results
        vr = ValidationResult(
            id=str(uuid.uuid4()),
            document_id=doc.id,
            status="completed",
            issues=[
                {"type": "compliance", "severity": "high", "description": "Promoter lock-in stated as 2 years instead of required 3 years.", "rule": "ICDR_REG_28", "why": "Lock-in must be 3 years per ICDR", "evidence": "'Promoter contribution will be locked in for two years'", "confidence_score": 0.95, "source": "DRHP_v2, Page 42"}
            ],
            missing_info=[
                {"field": "Auditor Certificate", "section": "Other Disclosures", "required_by": "ICDR_REG_26", "description": "Auditor certificate for promoter contribution is missing"}
            ],
            summary="Document passed basic layout validation but has critical compliance gaps regarding promoter lock-in.",
            ai_model="gpt-4o",
            created_at=base_time + timedelta(hours=i, minutes=10)
        )
        db.add(vr)

    # 5. Compliance Checks
    checks = [
        {"reg": "ICDR_REG_6", "name": "SME IPO Eligibility — Capital Limit", "status": "pass", "reason": "Post-issue paid-up capital of Rs. 14.5 Crore is well within the Rs. 25 Crore limit.", "evidence": "Post-issue capital: Rs. 14,50,00,000", "citation": "ICDR_REG_6"},
        {"reg": "ICDR_REG_28", "name": "Lock-in of Minimum Promoters Contribution", "status": "fail", "reason": "The document incorrectly states a lock-in period of 2 years for minimum promoter contribution.", "evidence": "'The minimum promoters contribution shall be locked-in for a period of two years.'", "citation": "ICDR_REG_28"},
        {"reg": "ICDR_REG_46", "name": "Risk Factors", "status": "warning", "reason": "Risk factors regarding customer concentration are mentioned but lack quantitative impact analysis.", "evidence": "Section 4: Risk Factors", "citation": "ICDR_REG_46"}
    ]
    
    for i, c in enumerate(checks):
        chk = ComplianceCheck(
            id=str(uuid.uuid4()),
            workspace_id=workspace.id,
            check_type=c["reg"],
            regulation=c["name"],
            status=c["status"],
            evidence={"evidence": c.get("evidence", ""), "confidence": "strong", "regulation_reference": c["citation"], "category": "general", "severity": "high" if c["status"] == "fail" else "medium", "suggestions": []},
            ai_reasoning=c["reason"],
            created_at=base_time + timedelta(days=1, hours=i)
        )
        db.add(chk)

    # 6. Audit Events
    events = [
        {"action": "WORKSPACE_CREATED", "target_type": "workspace", "id": workspace.id, "time": base_time},
        {"action": "DOCUMENT_UPLOADED", "target_type": "document", "id": doc_ids[0], "time": base_time + timedelta(hours=1)},
        {"action": "VALIDATION_STARTED", "target_type": "document", "id": doc_ids[0], "time": base_time + timedelta(hours=1, minutes=5)},
        {"action": "COMPLIANCE_RUN_STARTED", "target_type": "workspace", "id": workspace.id, "time": base_time + timedelta(days=1)},
        {"action": "EXECUTIVE_SUMMARY_GENERATED", "target_type": "workspace", "id": workspace.id, "time": base_time + timedelta(days=1, hours=5)}
    ]
    
    for evt in events:
        ae = AuditEvent(
            id=str(uuid.uuid4()),
            workspace_id=workspace.id,
            user_id=user_id,
            action=evt["action"],
            target_id=evt["id"],
            target_type=evt["target_type"],
            status="success",
            details="Demo workflow execution",
            created_at=evt["time"]
        )
        db.add(ae)
        
    await db.commit()
    await db.refresh(workspace)
    return workspace
