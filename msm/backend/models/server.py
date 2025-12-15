from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from ..database import Base

class Server(Base):
    __tablename__ = 'servers'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), index=True)
    ip = Column(String(50))
    port = Column(Integer, default=22)
    user = Column(String(50))
    ssh_key_path = Column(String(255))
    password_encrypted = Column(String(255))
    use_key = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
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
    os_name = Column(String(50))
    os_version = Column(String(50))
    kernel_version = Column(String(50))
    uptime = Column(String(50))
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    server = relationship("Server", back_populates="specs")

class CustomCommand(Base):
    __tablename__ = 'custom_commands'
    
    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey('servers.id'))
    name = Column(String(100))
    command = Column(String(255))
    regex_pattern = Column(String(255))
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    server = relationship("Server", back_populates="commands")
    results = relationship("CommandResult", back_populates="command")

class CommandResult(Base):
    __tablename__ = 'command_results'
    
    id = Column(Integer, primary_key=True, index=True)
    command_id = Column(Integer, ForeignKey('custom_commands.id'))
    output = Column(String(1000))
    parsed_value = Column(String(255))
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    command = relationship("CustomCommand", back_populates="results")

class LogSource(Base):
    __tablename__ = 'log_sources'
    
    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey('servers.id'))
    name = Column(String(100))
    source_type = Column(String(50))  # 'journalctl', 'file', 'docker'
    source_path = Column(String(255))
    enabled = Column(Boolean, default=True)
    
    server = relationship("Server", back_populates="log_sources")

class Alert(Base):
    __tablename__ = 'alerts'
    
    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey('servers.id'))
    name = Column(String(100))
    condition_type = Column(String(50))  # 'cpu', 'ram', 'disk', 'custom'
    condition_value = Column(String(100))
    threshold = Column(String(50))
    comparison = Column(String(20))  # '>', '<', '=', '>=', '<='
    enabled = Column(Boolean, default=True)
    telegram_notify = Column(Boolean, default=False)
    
    server = relationship("Server", back_populates="alerts")

class Metric(Base):
    __tablename__ = 'metrics'
    
    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey('servers.id'))
    metric_type = Column(String(50))  # 'cpu', 'ram', 'disk', 'network'
    value = Column(String(50))
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    server = relationship("Server", back_populates="metrics")

class AlertHistory(Base):
    __tablename__ = 'alert_history'
    
    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(Integer, ForeignKey('alerts.id'))
    triggered_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime)
    notification_sent = Column(Boolean, default=False)
    
    alert = relationship("Alert")

class TelegramConfig(Base):
    __tablename__ = 'telegram_config'
    
    id = Column(Integer, primary_key=True, index=True)
    bot_token = Column(String(100))
    chat_id = Column(String(50))
    enabled = Column(Boolean, default=False)
    last_test = Column(DateTime)
