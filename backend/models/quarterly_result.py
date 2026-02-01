from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class QuarterlyResult(Base):
    __tablename__ = "quarterly_results"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)

    # Period
    fiscal_year = Column(Integer, nullable=False)
    fiscal_quarter = Column(String(2), nullable=False)  # Q1, Q2, Q3, Q4
    period_end_date = Column(DateTime, nullable=False)
    report_date = Column(DateTime)

    # Income Statement
    revenue = Column(Float)
    cost_of_revenue = Column(Float)
    gross_profit = Column(Float)
    operating_income = Column(Float)
    net_income = Column(Float)
    eps = Column(Float)
    eps_diluted = Column(Float)

    # Calculated Margins
    gross_margin = Column(Float)
    operating_margin = Column(Float)
    net_margin = Column(Float)

    # Growth Rates (YoY)
    revenue_growth_yoy = Column(Float)
    eps_growth_yoy = Column(Float)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    company = relationship("Company", back_populates="quarterly_results")

    __table_args__ = (
        UniqueConstraint("company_id", "fiscal_year", "fiscal_quarter", name="uq_quarterly_result"),
    )

    def __repr__(self):
        return f"<QuarterlyResult {self.fiscal_year} {self.fiscal_quarter}>"
