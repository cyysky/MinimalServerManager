from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

class LogSource(Base):
    __tablename__ = 'log_sources'
    
    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey('servers.id'))
    name = Column(String(100), nullable=False)
    source_type = Column(String(50), nullable=False)  # 'journalctl', 'file', 'docker'
    source_path = Column(Text, nullable=False)
    enabled = Column(Boolean, default=True)
    
    # Relationships
    server = relationship("Server", back_populates="log_sources")
    entries = relationship("LogEntry", back_populates="source")

class LogEntry(Base):
    __tablename__ = 'log_entries'
    
    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey('log_sources.id'))
    timestamp = Column(DateTime, default=datetime.utcnow)
    level = Column(String(20))  # 'INFO', 'WARNING', 'ERROR', 'CRITICAL'
    message = Column(Text)
    
    # Relationships
    source = relationship("LogSource", back_populates="entries")