from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

# Import shared Base from __init__.py
from . import Base

class Alert(Base):
    __tablename__ = 'alerts'
    
    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey('servers.id'))
    name = Column(String(100), nullable=False)
    metric_type = Column(String(50), nullable=False)  # 'cpu', 'memory', 'disk', etc.
    field = Column(String(50), nullable=False)  # 'totalUsage', 'usage_percent', etc.
    comparison = Column(String(20), nullable=False)  # '>', '<', '=='
    threshold_value = Column(Integer, nullable=False)
    severity = Column(String(20), default='medium')
    cooldown_minutes = Column(Integer, default=10)
    notification_emails = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    server = relationship("Server", back_populates="alerts")
    history = relationship("AlertHistory", back_populates="alert")

class AlertHistory(Base):
    __tablename__ = 'alert_history'
    
    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(Integer, ForeignKey('alerts.id'))
    server_id = Column(Integer, ForeignKey('servers.id'))
    message = Column(Text)
    severity = Column(String(20))
    triggered_at = Column(DateTime, default=datetime.utcnow)
    resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime)
    
    # Relationships
    alert = relationship("Alert", back_populates="history")
    server = relationship("Server")