"""
DRHP Generation Pydantic Schemas
SEBI ICDR Regulations 2018 — SME IPO Draft Red Herring Prospectus
"""
from pydantic import BaseModel, Field
from typing import List, Optional


class CompanyProfile(BaseModel):
    name: str = Field(..., description="Full legal name of the company")
    cin: str = Field(..., description="Corporate Identity Number")
    pan: str = Field(..., description="Permanent Account Number")
    incorporation_date: str = Field(..., description="Date of incorporation (YYYY-MM-DD)")
    registered_address: str
    sector: str
    sub_sector: Optional[str] = None
    website: Optional[str] = None
    description: str = Field(..., description="Business description (min 200 words recommended)")


class PromoterDetail(BaseModel):
    name: str
    designation: str
    qualification: Optional[str] = None
    holding_pct: float = Field(..., ge=0, le=100, description="Shareholding percentage")


class FinancialYear(BaseModel):
    year: str = Field(..., description="Financial year e.g. 2023-24")
    revenue: float = Field(0.0, description="Total revenue in INR Lakhs")
    net_profit: float = Field(0.0, description="Net profit/(loss) in INR Lakhs")
    total_assets: float = Field(0.0, description="Total assets in INR Lakhs")
    total_equity: float = Field(0.0, description="Net worth/equity in INR Lakhs")
    ebitda: float = Field(0.0, description="EBITDA in INR Lakhs")


class IssueDetails(BaseModel):
    issue_size_cr: float = Field(..., description="Total issue size in INR Crore")
    fresh_issue_cr: float = Field(0.0, description="Fresh issue component in INR Crore")
    ofs_cr: float = Field(0.0, description="Offer for sale component in INR Crore")
    price_band_low: float = Field(0.0, description="Floor price per share in INR")
    price_band_high: float = Field(..., description="Cap price per share in INR")
    face_value: float = Field(10.0, description="Face value per share in INR")
    lot_size: int = Field(0, description="Number of shares per lot")
    objects_of_issue: str = Field(..., description="Objects/purposes of the issue")
    use_of_proceeds: str = Field("", description="Detailed use of proceeds")
    merchant_banker: str = Field(..., description="SEBI-registered lead merchant banker")


class DrhpRequest(BaseModel):
    company: CompanyProfile
    promoters: List[PromoterDetail] = Field(default_factory=list)
    financials: List[FinancialYear] = Field(default_factory=list, min_length=1)
    issue: IssueDetails


class DrhpJobResponse(BaseModel):
    job_id: str
    status: str
    message: str


class DrhpStatusResponse(BaseModel):
    job_id: str
    status: str  # pending | processing | done | error
    progress_pct: int
    message: str
