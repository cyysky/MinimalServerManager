from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

class Metric(Base):
    __tablename__ = 'metrics'
    
    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey('servers.id'))
    metric_type = Column(String(50), nullable=False)  # 'cpu', 'ram', 'disk', 'network'
    value = Column(String(50), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    server = relationship("Server", back_populates="metrics")