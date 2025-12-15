# Database models initialization
# This file will be used to import all models and create database tables

from sqlalchemy.ext.declarative import declarative_base

# Create shared Base instance
Base = declarative_base()

# Import all server models
from .server_models import Server, ServerSpec, CustomCommand, CommandResult
from .server_models import LogSource, LogEntry, LogResult, Metric, TelegramConfig

# Import all alert models
from .alert_models import Alert, AlertHistory