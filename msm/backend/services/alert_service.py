# Minimal Server Manager - Alert Service
# Handles alert generation, management and notifications

import threading
import time
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Server, Metric
from models import Alert as AlertCondition, AlertHistory

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class AlertService:
    """
    Service for managing and triggering alerts
    Handles alert conditions, notifications and history
    """
    
    def __init__(self, database_url: str, websocket_manager=None):
        self.logger = logging.getLogger('AlertService')
        self.database_url = database_url
        self.running = False
        self.websocket_manager = websocket_manager
        
        # Create database engine and session
        self.engine = create_engine(database_url, connect_args={"check_same_thread": False})
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.Session = SessionLocal
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Alert checking interval - reduced for more frequent checking
        self.check_interval = 30  # Check every 30 seconds instead of 60
        
        # Notification settings
        self.smtp_servers = {}
        self.email_from = None
        
        # Alert conditions cache
        self.alert_conditions = []
        self.last_alert_triggers = {}  # alert_id: last_trigger_time
        self.active_alerts = {}  # alert_id: alert_data for escalation
    
    def start(self) -> None:
        """
        Start the alert monitoring service
        """
        if self.running:
            return
            
        self.running = True
        self.logger.info("Starting alert service...")
        
        # Start alert checking thread
        alert_thread = threading.Thread(target=self._alert_monitoring_loop, daemon=True)
        alert_thread.start()
        
        # Start alert escalation thread
        escalation_thread = threading.Thread(target=self._alert_escalation_loop, daemon=True)
        escalation_thread.start()
        
        # Load current alert conditions
        self._load_alert_conditions()
    
    def stop(self) -> None:
        """
        Stop the alert service
        """
        self.running = False
        self.logger.info("Alert service stopped")
    
    def configure_email(self, smtp_server: str, port: int, username: str, 
                        password: str, email_from: str, use_tls: bool = True) -> None:
        """
        Configure email settings for alert notifications
        """
        self.smtp_servers['default'] = {
            'server': smtp_server,
            'port': port,
            'username': username,
            'password': password,
            'use_tls': use_tls
        }
        self.email_from = email_from
        self.logger.info("Email notification configured")
    
    def _load_alert_conditions(self) -> None:
        """
        Load all active alert conditions from database
        """
        db = self.Session()
        try:
            self.alert_conditions = db.query(AlertCondition).filter(
                AlertCondition.is_active == True
            ).all()
            self.logger.info(f"Loaded {len(self.alert_conditions)} active alert conditions")
        except Exception as e:
            self.logger.error(f"Error loading alert conditions: {e}")
        finally:
            db.close()
    
    def _alert_monitoring_loop(self) -> None:
        """
        Main alert monitoring loop that runs continuously
        """
        while self.running:
            try:
                self._check_alert_conditions()
                
                # Sleep until next check
                time.sleep(self.check_interval)
                
            except Exception as e:
                self.logger.error(f"Error in alert monitoring loop: {e}")
                time.sleep(30)  # Wait longer if error occurs
    
    def _alert_escalation_loop(self) -> None:
        """
        Handle alert escalation for unresolved alerts
        """
        while self.running:
            try:
                current_time = time.time()
                escalation_needed = []
                
                with self._lock:
                    for alert_id, alert_data in self.active_alerts.items():
                        # Check if alert needs escalation (after 15 minutes)
                        if current_time - alert_data['triggered_at'] > 900:  # 15 minutes
                            escalation_needed.append(alert_id)
                
                # Process escalations
                for alert_id in escalation_needed:
                    self._escalate_alert(alert_id)
                
                time.sleep(60)  # Check for escalations every minute
                
            except Exception as e:
                self.logger.error(f"Error in alert escalation loop: {e}")
                time.sleep(60)
    
    def _check_alert_conditions(self) -> None:
        """
        Check all alert conditions against current metrics
        """
        if not self.alert_conditions:
            return
        
        self.logger.info(f"Checking {len(self.alert_conditions)} alert conditions...")
        
        db = self.Session()
        try:
            for alert_cond in self.alert_conditions:
                try:
                    self._check_single_alert_condition(alert_cond)
                except Exception as e:
                    self.logger.error(f"Error checking alert {alert_cond.id}: {e}")
        finally:
            db.close()
    
    def _check_single_alert_condition(self, alert_cond: AlertCondition) -> None:
        """
        Check a single alert condition
        """
        # Skip if alert is disabled
        if not alert_cond.is_active:
            return
        
        # Check cooldown period to avoid duplicate alerts
        if alert_cond.id in self.last_alert_triggers:
            last_trigger = self.last_alert_triggers[alert_cond.id]
            cooldown = alert_cond.cooldown_minutes * 60
            if time.time() - last_trigger < cooldown:
                return
        
        # Get relevant metric for this alert
        metric_value = self._get_metric_value(alert_cond)
        if metric_value is None:
            self.logger.warning(f"No metric data available for alert {alert_cond.id}")
            return
        
        # Check condition
        trigger_alert = False
        message = f"Server {alert_cond.server_id}"
        
        if alert_cond.comparison == '>':
            if metric_value > alert_cond.threshold_value:
                trigger_alert = True
                message += f" {alert_cond.metric_type} {metric_value} > {alert_cond.threshold_value}"
        elif alert_cond.comparison == '<':
            if metric_value < alert_cond.threshold_value:
                trigger_alert = True
                message += f" {alert_cond.metric_type} {metric_value} < {alert_cond.threshold_value}"
        elif alert_cond.comparison == '==':
            if metric_value == alert_cond.threshold_value:
                trigger_alert = True
                message += f" {alert_cond.metric_type} {metric_value} == {alert_cond.threshold_value}"
        
        if trigger_alert:
            self._trigger_alert(alert_cond, message)
    
    def _get_metric_value(self, alert_cond: AlertCondition) -> Optional[float]:
        """
        Get the current value for the specified metric
        """
        db = self.Session()
        try:
            # Get the most recent metric for this server and type
            metric = db.query(Metric).filter(
                Metric.server_id == alert_cond.server_id,
                Metric.metric_type == alert_cond.metric_type
            ).order_by(Metric.timestamp.desc()).first()
            
            if metric:
                # Parse the stored JSON value
                try:
                    metric_data = json.loads(metric.value)
                    return float(metric_data[alert_cond.field])
                except (json.JSONDecodeError, KeyError, ValueError):
                    pass
            
            return None
        except Exception as e:
            self.logger.error(f"Error getting metric value: {e}")
            return None
        finally:
            db.close()
    
    def _trigger_alert(self, alert_cond: AlertCondition, message: str) -> None:
        """
        Trigger an alert and send notifications
        """
        db = self.Session()
        try:
            # Create alert history record
            alert_history = AlertHistory(
                alert_id=alert_cond.id,
                server_id=alert_cond.server_id,
                message=message,
                severity=alert_cond.severity,
                triggered_at=datetime.utcnow(),
                resolved=False
            )
            db.add(alert_history)
            db.commit()
            
            # Update last trigger time
            self.last_alert_triggers[alert_cond.id] = time.time()
            
            # Store in active alerts for escalation tracking
            with self._lock:
                self.active_alerts[alert_history.id] = {
                    'alert_id': alert_cond.id,
                    'server_id': alert_cond.server_id,
                    'severity': alert_cond.severity,
                    'triggered_at': time.time(),
                    'message': message
                }
            
            # Send notifications
            alert_message = f"🚨 ALERT: {alert_cond.name}\n" \
                          f"Severity: {alert_cond.severity}\n" \
                          f"Message: {message}\n" \
                          f"Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"
            
            self.logger.info(f"Alert triggered: {message}")
            
            # Broadcast via WebSocket immediately
            if self.websocket_manager:
                websocket_message = {
                    "type": "alert_triggered",
                    "alert_id": alert_history.id,
                    "alert_condition_id": alert_cond.id,
                    "server_id": alert_cond.server_id,
                    "name": alert_cond.name,
                    "severity": alert_cond.severity,
                    "message": message,
                    "timestamp": datetime.utcnow().isoformat()
                }
                self.websocket_manager.broadcast(json.dumps(websocket_message), "alert_update")
            
            # Send email notification if configured
            if self.email_from and 'default' in self.smtp_servers:
                self._send_email_notification(
                    alert_message,
                    f"Server Alert: {alert_cond.name}",
                    alert_cond.notification_emails
                )
            
        except Exception as e:
            db.rollback()
            self.logger.error(f"Error triggering alert: {e}")
        finally:
            db.close()
    
    def _escalate_alert(self, alert_history_id: int) -> None:
        """
        Escalate an unresolved alert
        """
        with self._lock:
            if alert_history_id not in self.active_alerts:
                return
            
            alert_data = self.active_alerts[alert_history_id]
            escalation_message = f"ESCALATION: Alert {alert_history_id} unresolved for 15+ minutes\n" \
                               f"Server: {alert_data['server_id']}\n" \
                               f"Severity: {alert_data['severity']}\n" \
                               f"Message: {alert_data['message']}"
            
            self.logger.warning(escalation_message)
            
            # Broadcast escalation via WebSocket
            if self.websocket_manager:
                escalation_ws_message = {
                    "type": "alert_escalated",
                    "alert_id": alert_history_id,
                    "server_id": alert_data['server_id'],
                    "severity": alert_data['severity'],
                    "message": alert_data['message'],
                    "timestamp": datetime.utcnow().isoformat()
                }
                self.websocket_manager.broadcast(json.dumps(escalation_ws_message), "alert_update")
            
            # Send escalation email
            if self.email_from and 'default' in self.smtp_servers:
                self._send_email_notification(
                    escalation_message,
                    f"ALERT ESCALATION: Server {alert_data['server_id']}",
                    None  # Send to admin email
                )
    
    def _send_email_notification(self, message: str, subject: str, 
                                recipients: Optional[str]) -> None:
        """
        Send email notification about an alert
        """
        if not recipients:
            return
        
        try:
            email_list = [email.strip() for email in recipients.split(',')]
            
            msg = MIMEMultipart()
            msg['From'] = self.email_from
            msg['To'] = ', '.join(email_list)
            msg['Subject'] = subject
            
            msg.attach(MIMEText(message, 'plain'))
            
            smtp_config = self.smtp_servers['default']
            
            with smtplib.SMTP(smtp_config['server'], smtp_config['port']) as server:
                if smtp_config['use_tls']:
                    server.starttls()
                if smtp_config['username'] and smtp_config['password']:
                    server.login(smtp_config['username'], smtp_config['password'])
                server.send_message(msg)
            
            self.logger.info(f"Alert email sent to {', '.join(email_list)}")
            
        except Exception as e:
            self.logger.error(f"Error sending email notification: {e}")
    
    def create_alert_condition(self, name: str, server_id: int, metric_type: str,
                             field: str, comparison: str, threshold_value: float,
                             severity: str = 'medium', cooldown_minutes: int = 10,
                             notification_emails: str = None, is_active: bool = True) -> bool:
        """
        Create a new alert condition
        """
        db = self.Session()
        try:
            alert_cond = AlertCondition(
                name=name,
                server_id=server_id,
                metric_type=metric_type,
                field=field,
                comparison=comparison,
                threshold_value=threshold_value,
                severity=severity,
                cooldown_minutes=cooldown_minutes,
                notification_emails=notification_emails,
                is_active=is_active
            )
            
            db.add(alert_cond)
            db.commit()
            
            # Reload alert conditions
            self._load_alert_conditions()
            
            self.logger.info(f"Created new alert condition: {name}")
            return True
            
        except Exception as e:
            db.rollback()
            self.logger.error(f"Error creating alert condition: {e}")
            return False
        finally:
            db.close()
    
    def get_active_alerts(self) -> List[AlertCondition]:
        """
        Get all active alert conditions
        """
        return self.alert_conditions
    
    def get_alert_history(self, limit: int = 100) -> List[AlertHistory]:
        """
        Get recent alert history
        """
        db = self.Session()
        try:
            history = db.query(AlertHistory).order_by(AlertHistory.triggered_at.desc()).limit(limit).all()
            return history
        except Exception as e:
            self.logger.error(f"Error getting alert history: {e}")
            return []
        finally:
            db.close()
    
    def mark_alert_resolved(self, alert_history_id: int) -> bool:
        """
        Mark an alert as resolved
        """
        db = self.Session()
        try:
            alert = db.query(AlertHistory).filter(AlertHistory.id == alert_history_id).first()
            if alert:
                alert.resolved = True
                alert.resolved_at = datetime.utcnow()
                db.commit()
                
                # Remove from active alerts
                with self._lock:
                    if alert_history_id in self.active_alerts:
                        del self.active_alerts[alert_history_id]
                
                # Broadcast resolution via WebSocket
                if self.websocket_manager:
                    resolution_message = {
                        "type": "alert_resolved",
                        "alert_id": alert_history_id,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    self.websocket_manager.broadcast(json.dumps(resolution_message), "alert_update")
                
                return True
            return False
        except Exception as e:
            db.rollback()
            self.logger.error(f"Error marking alert as resolved: {e}")
            return False
        finally:
            db.close()
    
    def get_unresolved_alerts(self) -> List[Dict[str, Any]]:
        """
        Get all currently unresolved alerts
        """
        with self._lock:
            return list(self.active_alerts.values())
    
    def acknowledge_alert(self, alert_history_id: int, acknowledged_by: str = None) -> bool:
        """
        Acknowledge an alert (mark as seen but not necessarily resolved)
        """
        # For now, this is the same as resolving
        # In a more advanced system, this would mark as acknowledged but not resolved
        return self.mark_alert_resolved(alert_history_id)

# Singleton instance
alert_service = None

def init_alert_service(database_url: str, websocket_manager=None):
    global alert_service
    if alert_service is None:
        alert_service = AlertService(database_url, websocket_manager)
    return alert_service