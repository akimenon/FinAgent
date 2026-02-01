from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class EarningsSurprise(Base):
    __tablename__ = "earnings_surprises"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)

    # Period
    fiscal_year = Column(Integer, nullable=False)
    fiscal_quarter = Column(String(2), nullable=False)
    report_date = Column(DateTime, nullable=False)

    # EPS Comparison
    actual_eps = Column(Float, nullable=False)
    estimated_eps = Column(Float, nullable=False)
    eps_surprise = Column(Float)  # actual - estimated
    eps_surprise_percent = Column(Float)  # (actual - estimated) / |estimated| * 100

    # Revenue Comparison
    actual_revenue = Column(Float)
    estimated_revenue = Column(Float)
    revenue_surprise = Column(Float)
    revenue_surprise_percent = Column(Float)

    # Verdict
    beat_miss = Column(String(10))  # BEAT, MISS, MEET

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    company = relationship("Company", back_populates="earnings_surprises")

    __table_args__ = (
        UniqueConstraint("company_id", "fiscal_year", "fiscal_quarter", name="uq_earnings_surprise"),
    )

    def __repr__(self):
        return f"<EarningsSurprise {self.fiscal_year} {self.fiscal_quarter}: {self.beat_miss}>"
