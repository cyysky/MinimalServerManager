from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

class CustomCommand(Base):
    __tablename__ = 'custom_commands'
    
    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey('servers.id'))
    name = Column(String(100), nullable=False)
    command = Column(Text, nullable=False)
    regex_pattern = Column(Text)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    server = relationship("Server", back_populates="commands")
    results = relationship("CommandResult", back_populates="command")

class CommandResult(Base):
    __tablename__ = 'command_results'
    
    id = Column(Integer, primary_key=True, index=True)
    command_id = Column(Integer, ForeignKey('custom_commands.id'))
    output = Column(Text)
    parsed_value = Column(String(255))
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    command = relationship("CustomCommand", back_populates="results")