
import pandas as pd
import json
from datetime import datetime, timedelta
from pathlib import Path
import logging

class AlertSystem:
    """Manages alerts and notifications for the monitoring system"""
    
    def __init__(self, data_dir="data"):
        self.data_dir = Path(data_dir)
        self.alerts_dir = self.data_dir / "alerts"
        self.alerts_dir.mkdir(exist_ok=True)
        
        self.logger = logging.getLogger(__name__)
        
        # Alert thresholds
        self.thresholds = {
            'publication_drop_percent': 20,  # Alert if publications drop by 20%
            'no_publications_days': 30,     # Alert if no publications for 30 days
            'data_freshness_days': 14,      # Alert if data is older than 14 days
            'system_unavailable_hours': 6   # Alert if system unavailable for 6 hours
        }
    
    def check_alerts(self, data_manager):
        """Check for various alert conditions"""
        try:
            alerts = []
            
            # Get recent data
            recent_data = data_manager.get_historical_data(30)
            if recent_data.empty:
                return alerts
            
            # Group by organization
            org_groups = recent_data.groupby('org_id')
            
            for org_id, org_data in org_groups:
                org_name = org_data.iloc[0].get('organization_name', 'Unknown')
                
                # Check for publication drops
                pub_drop_alert = self._check_publication_drop(org_data, org_name)
                if pub_drop_alert:
                    alerts.append(pub_drop_alert)
                
                # Check for stale data
                stale_data_alert = self._check_stale_data(org_data, org_name)
                if stale_data_alert:
                    alerts.append(stale_data_alert)
                
                # Check for system availability
                availability_alert = self._check_system_availability(org_data, org_name)
                if availability_alert:
                    alerts.append(availability_alert)
            
            # Save alerts
            if alerts:
                self._save_alerts(alerts)
            
            return alerts
            
        except Exception as e:
            self.logger.error(f"Error checking alerts: {e}")
            return []
    
    def _check_publication_drop(self, org_data, org_name):
        """Check for drops in publication numbers"""
        try:
            # Sort by date
            org_data = org_data.sort_values('date')
            
            if len(org_data) < 7:  # Need at least a week of data
                return None
            
            # Compare recent week to previous week
            recent_pubs = org_data.tail(7)['publications_recent'].mean()
            previous_pubs = org_data.iloc[-14:-7]['publications_recent'].mean()
            
            # Calculate percentage drop
            if previous_pubs > 0:
                drop_percent = ((previous_pubs - recent_pubs) / previous_pubs) * 100
                
                if drop_percent >= self.thresholds['publication_drop_percent']:
                    return {
                        'id': f"pub_drop_{org_data.iloc[0]['org_id']}",
                        'type': 'Publication Drop',
                        'severity': 'warning' if drop_percent < 50 else 'critical',
                        'organization': org_name,
                        'message': f"Publications dropped by {drop_percent:.1f}% ({previous_pubs:.1f} → {recent_pubs:.1f})",
                        'timestamp': datetime.now(),
                        'data': {
                            'drop_percent': drop_percent,
                            'previous_avg': previous_pubs,
                            'recent_avg': recent_pubs
                        }
                    }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error checking publication drop for {org_name}: {e}")
            return None
    
    def _check_stale_data(self, org_data, org_name):
        """Check for stale or outdated data"""
        try:
            # Get most recent data freshness
            latest_data = org_data.sort_values('date').iloc[-1]
            data_freshness_days = latest_data.get('data_freshness_days')
            
            if (data_freshness_days is not None and 
                data_freshness_days >= self.thresholds['data_freshness_days']):
                
                severity = 'warning' if data_freshness_days < 30 else 'critical'
                
                return {
                    'id': f"stale_data_{latest_data['org_id']}",
                    'type': 'Stale Data',
                    'severity': severity,
                    'organization': org_name,
                    'message': f"Data is {data_freshness_days} days old",
                    'timestamp': datetime.now(),
                    'data': {
                        'data_freshness_days': data_freshness_days,
                        'last_publication_date': latest_data.get('last_publication_date')
                    }
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error checking stale data for {org_name}: {e}")
            return None
    
    def _check_system_availability(self, org_data, org_name):
        """Check for system availability issues"""
        try:
            # Check if we have recent data
            latest_date = pd.to_datetime(org_data['date'].max())
            hours_since_update = (datetime.now() - latest_date).total_seconds() / 3600
            
            if hours_since_update >= self.thresholds['system_unavailable_hours']:
                return {
                    'id': f"unavailable_{org_data.iloc[0]['org_id']}",
                    'type': 'System Unavailable',
                    'severity': 'critical',
                    'organization': org_name,
                    'message': f"No data updates for {hours_since_update:.1f} hours",
                    'timestamp': datetime.now(),
                    'data': {
                        'hours_since_update': hours_since_update,
                        'last_update': latest_date
                    }
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error checking system availability for {org_name}: {e}")
            return None
    
    def _save_alerts(self, alerts):
        """Save alerts to file"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            alerts_file = self.alerts_dir / f"alerts_{timestamp}.json"
            
            # Convert datetime objects to strings for JSON serialization
            alerts_json = []
            for alert in alerts:
                alert_copy = alert.copy()
                alert_copy['timestamp'] = alert_copy['timestamp'].isoformat()
                alerts_json.append(alert_copy)
            
            with open(alerts_file, 'w') as f:
                json.dump(alerts_json, f, indent=2)
            
            self.logger.info(f"Saved {len(alerts)} alerts to {alerts_file}")
            
        except Exception as e:
            self.logger.error(f"Error saving alerts: {e}")
    
    def get_active_alerts(self, hours=24):
        """Get active alerts from the last N hours"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            active_alerts = []
            
            # Read all recent alert files
            for alert_file in self.alerts_dir.glob("alerts_*.json"):
                try:
                    file_time = datetime.fromtimestamp(alert_file.stat().st_mtime)
                    if file_time >= cutoff_time:
                        with open(alert_file, 'r') as f:
                            alerts = json.load(f)
                            for alert in alerts:
                                alert['timestamp'] = datetime.fromisoformat(alert['timestamp'])
                                if alert['timestamp'] >= cutoff_time:
                                    active_alerts.append(alert)
                except Exception as e:
                    self.logger.error(f"Error reading alert file {alert_file}: {e}")
                    continue
            
            # Sort by timestamp (newest first) and remove duplicates
            active_alerts.sort(key=lambda x: x['timestamp'], reverse=True)
            
            # Remove duplicate alerts (same ID)
            seen_ids = set()
            unique_alerts = []
            for alert in active_alerts:
                if alert['id'] not in seen_ids:
                    unique_alerts.append(alert)
                    seen_ids.add(alert['id'])
            
            return unique_alerts
            
        except Exception as e:
            self.logger.error(f"Error getting active alerts: {e}")
            return []
    
    def get_alert_summary(self):
        """Get summary of alert statistics"""
        try:
            active_alerts = self.get_active_alerts(24)
            
            summary = {
                'total_alerts': len(active_alerts),
                'critical_alerts': len([a for a in active_alerts if a['severity'] == 'critical']),
                'warning_alerts': len([a for a in active_alerts if a['severity'] == 'warning']),
                'alert_types': {}
            }
            
            # Count by type
            for alert in active_alerts:
                alert_type = alert['type']
                summary['alert_types'][alert_type] = summary['alert_types'].get(alert_type, 0) + 1
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error getting alert summary: {e}")
            return {}
    
    def dismiss_alert(self, alert_id):
        """Dismiss a specific alert"""
        # This could be implemented to mark alerts as dismissed
        # For now, we'll just log it
        self.logger.info(f"Alert dismissed: {alert_id}")
    
    def send_notification(self, alert):
        """Send notification for an alert (placeholder for future implementation)"""
        # This could be extended to send actual notifications via:
        # - Email
        # - Slack
        # - Push notifications
        # - SMS
        
        self.logger.info(f"Notification sent for alert: {alert['type']} - {alert['organization']}")
