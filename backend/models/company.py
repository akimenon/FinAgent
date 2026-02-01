from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(10), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    sector = Column(String(100))
    industry = Column(String(100))
    market_cap = Column(Float)
    exchange = Column(String(20))
    last_updated = Column(DateTime, default=datetime.utcnow)

    # Relationships
    quarterly_results = relationship("QuarterlyResult", back_populates="company", cascade="all, delete-orphan")
    earnings_surprises = relationship("EarningsSurprise", back_populates="company", cascade="all, delete-orphan")
    guidances = relationship("Guidance", back_populates="company", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Company {self.symbol}: {self.name}>"
