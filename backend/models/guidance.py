from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class Guidance(Base):
    __tablename__ = "guidances"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)

    # When guidance was issued
    guidance_date = Column(DateTime, nullable=False)

    # Target period
    target_fiscal_year = Column(Integer, nullable=False)
    target_fiscal_quarter = Column(String(2))  # Null for full-year guidance

    # Revenue Guidance
    revenue_guidance_low = Column(Float)
    revenue_guidance_high = Column(Float)
    revenue_guidance_mid = Column(Float)

    # EPS Guidance
    eps_guidance_low = Column(Float)
    eps_guidance_high = Column(Float)
    eps_guidance_mid = Column(Float)

    # Actual Results (populated after earnings)
    actual_revenue = Column(Float)
    actual_eps = Column(Float)

    # Comparison
    guidance_met = Column(Boolean)  # Did actual meet guidance range?
    revenue_vs_guidance = Column(String(10))  # ABOVE, WITHIN, BELOW
    eps_vs_guidance = Column(String(10))  # ABOVE, WITHIN, BELOW

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    company = relationship("Company", back_populates="guidances")

    def __repr__(self):
        return f"<Guidance {self.target_fiscal_year} {self.target_fiscal_quarter or 'FY'}>"
