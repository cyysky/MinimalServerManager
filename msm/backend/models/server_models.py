from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, DateTime, Float
from sqlalchemy.orm import relationship
from datetime import datetime

# Import shared Base from __init__.py
from . import Base

class Server(Base):
    __tablename__ = 'servers'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    ip = Column(String(50), nullable=False)
    port = Column(Integer, default=22)
    user = Column(String(50), nullable=False)
    ssh_key_path = Column(Text)
    password_encrypted = Column(Text)
    use_key = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_connected = Column(DateTime)
    status = Column(String(50), default='unknown')
    
    # Relationships
    specs = relationship("ServerSpec", back_populates="server", uselist=False)
    commands = relationship("CustomCommand", back_populates="server")
    log_sources = relationship("LogSource", back_populates="server")
    alerts = relationship("Alert", back_populates="server")
    metrics = relationship("Metric", back_populates="server")

class ServerSpec(Base):
    __tablename__ = 'server_specs'
    
    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey('servers.id'), unique=True)
    cpu_model = Column(String(100))
    cpu_cores = Column(Integer)
    cpu_threads = Column(Integer)
    total_ram = Column(String(20))
    disk_info = Column(Text)
    gpu_info = Column(Text)
    os_info = Column(String(100))
    kernel_version = Column(String(50))
    last_updated = Column(DateTime)
    
    # Relationships
    server = relationship("Server", back_populates="specs")

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

class LogResult(Base):
    __tablename__ = 'log_results'
    
    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey('servers.id'))
    result_type = Column(String(50), nullable=False)
    result_value = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    server = relationship("Server")

class Metric(Base):
    __tablename__ = 'metrics'
    
    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey('servers.id'))
    metric_type = Column(String(50), nullable=False)  # 'cpu', 'ram', 'disk', 'network'
    value = Column(Text, nullable=False)  # Changed to Text to store JSON
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    server = relationship("Server", back_populates="metrics")

class TelegramConfig(Base):
    __tablename__ = 'telegram_config'
    
    id = Column(Integer, primary_key=True, index=True)
    bot_token = Column(String(100))
    chat_id = Column(String(50))
    enabled = Column(Boolean, default=False)
    last_test = Column(DateTime)
    last_notification = Column(DateTime)
    notification_count = Column(Integer, default=0)