from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from datetime import datetime

class TelegramConfig(Base):
    __tablename__ = 'telegram_config'
    
    id = Column(Integer, primary_key=True, index=True)
    bot_token = Column(String(100))
    chat_id = Column(String(50))
    enabled = Column(Boolean, default=False)
    last_test = Column(DateTime)
    last_notification = Column(DateTime)
    notification_count = Column(Integer, default=0)