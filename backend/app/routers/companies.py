import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth_middleware import get_current_user
from app.models.company import Company
from app.models.user import User
from app.schemas.company import CompanyCreate, CompanyResponse, CompanyUpdate

router = APIRouter(prefix="/companies", tags=["Companies"])


@router.post("", response_model=CompanyResponse, status_code=201)
async def create_company(
    data: CompanyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompanyResponse:
    company = Company(
        name=data.name,
        cin=data.cin,
        pan=data.pan,
        industry=data.industry,
        created_by=current_user.id,
    )
    db.add(company)
    await db.flush()
    await db.refresh(company)
    return company  # type: ignore[return-value]


@router.get("", response_model=list[CompanyResponse])
async def list_companies(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CompanyResponse]:
    result = await db.execute(
        select(Company)
        .where(Company.created_by == current_user.id)
        .order_by(Company.created_at.desc())
    )
    return list(result.scalars().all())  # type: ignore[return-value]


@router.get("/{company_id}", response_model=CompanyResponse)
async def get_company(
    company_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompanyResponse:
    result = await db.execute(
        select(Company).where(Company.id == company_id)
    )
    company = result.scalars().first()
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    return company  # type: ignore[return-value]


@router.patch("/{company_id}", response_model=CompanyResponse)
async def update_company(
    company_id: str,
    data: CompanyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompanyResponse:
    result = await db.execute(
        select(Company).where(Company.id == company_id)
    )
    company = result.scalars().first()
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    update_dict = data.model_dump(exclude_none=True)
    for field, value in update_dict.items():
        setattr(company, field, value)
    db.add(company)
    await db.flush()
    await db.refresh(company)
    return company  # type: ignore[return-value]
