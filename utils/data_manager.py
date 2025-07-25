
import pandas as pd
import os
import json
from datetime import datetime, timedelta
from pathlib import Path
import logging
import shutil

class DataManager:
    """Manages data storage and retrieval for the monitoring system"""
    
    def __init__(self, data_dir="data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        (self.data_dir / "daily").mkdir(exist_ok=True)
        (self.data_dir / "organizations").mkdir(exist_ok=True)
        (self.data_dir / "alerts").mkdir(exist_ok=True)
        (self.data_dir / "exports").mkdir(exist_ok=True)
        
        self.logger = logging.getLogger(__name__)
        
        # Load organizations data
        self.organizations_df = self.load_organizations_data()
    
    def load_organizations_data(self):
        """Load the Dutch organizations data"""
        try:
            # First try to load from data directory
            org_file = self.data_dir / "nl-orgs-baseline.xlsx"
            if not org_file.exists():
                # Copy from uploads if available
                upload_file = Path("/home/ubuntu/Uploads/nl-orgs-baseline.xlsx")
                if upload_file.exists():
                    shutil.copy2(upload_file, org_file)
            
            if org_file.exists():
                df = pd.read_excel(org_file, engine='openpyxl')
                self.logger.info(f"Loaded {len(df)} organizations")
                return df
            else:
                self.logger.error("Organizations file not found")
                return pd.DataFrame()
                
        except Exception as e:
            self.logger.error(f"Error loading organizations data: {e}")
            return pd.DataFrame()
    
    def save_daily_data(self, date, org_stats_list):
        """Save daily statistics for all organizations"""
        try:
            filename = f"daily_stats_{date.strftime('%Y%m%d')}.csv"
            filepath = self.data_dir / "daily" / filename
            
            # Convert to DataFrame
            df = pd.DataFrame(org_stats_list)
            df['date'] = date.strftime('%Y-%m-%d')
            
            # Save to CSV
            df.to_csv(filepath, index=False)
            self.logger.info(f"Saved daily data to {filepath}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving daily data: {e}")
            return False
    
    def load_daily_data(self, date=None):
        """Load daily data for a specific date or the most recent"""
        try:
            if date is None:
                # Get most recent file
                daily_files = list((self.data_dir / "daily").glob("daily_stats_*.csv"))
                if not daily_files:
                    return pd.DataFrame()
                
                latest_file = max(daily_files, key=os.path.getctime)
                return pd.read_csv(latest_file)
            else:
                filename = f"daily_stats_{date.strftime('%Y%m%d')}.csv"
                filepath = self.data_dir / "daily" / filename
                
                if filepath.exists():
                    return pd.read_csv(filepath)
                else:
                    return pd.DataFrame()
                    
        except Exception as e:
            self.logger.error(f"Error loading daily data: {e}")
            return pd.DataFrame()
    
    def get_historical_data(self, days=30):
        """Get historical data for the last N days"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            all_data = []
            current_date = start_date
            
            while current_date <= end_date:
                daily_data = self.load_daily_data(current_date)
                if not daily_data.empty:
                    daily_data['date'] = current_date.strftime('%Y-%m-%d')
                    all_data.append(daily_data)
                current_date += timedelta(days=1)
            
            if all_data:
                return pd.concat(all_data, ignore_index=True)
            else:
                return pd.DataFrame()
                
        except Exception as e:
            self.logger.error(f"Error getting historical data: {e}")
            return pd.DataFrame()
    
    def get_organization_trend(self, org_id, metric='publications_total', days=30):
        """Get trend data for a specific organization and metric"""
        try:
            historical_data = self.get_historical_data(days)
            if historical_data.empty:
                return pd.DataFrame()
            
            org_data = historical_data[historical_data['org_id'] == org_id]
            if org_data.empty:
                return pd.DataFrame()
            
            # Sort by date and get the specified metric
            org_data = org_data.sort_values('date')
            trend_data = org_data[['date', metric]].copy()
            trend_data['date'] = pd.to_datetime(trend_data['date'])
            
            return trend_data
            
        except Exception as e:
            self.logger.error(f"Error getting organization trend: {e}")
            return pd.DataFrame()
    
    def collect_daily_data(self, api_client):
        """Collect daily data for all organizations"""
        try:
            if self.organizations_df.empty:
                self.logger.error("No organizations data available")
                return False
            
            today = datetime.now().date()
            org_stats_list = []
            
            self.logger.info(f"Starting daily data collection for {len(self.organizations_df)} organizations")
            
            for idx, org in self.organizations_df.iterrows():
                try:
                    # Get OpenAIRE org ID
                    ror_link = org['ROR_LINK']
                    org_id = api_client.get_organization_id(ror_link)
                    
                    if org_id:
                        # Get organization statistics
                        stats = api_client.get_organization_stats(org_id)
                        if stats:
                            # Add organization metadata
                            stats.update({
                                'organization_name': org['full_name_in_English'],
                                'acronym': org['acronym_EN'],
                                'main_grouping': org['main_grouping'],
                                'ror_id': org['ROR'],
                                'ror_link': ror_link
                            })
                            org_stats_list.append(stats)
                            
                    # Small delay to avoid overwhelming the API
                    import time
                    time.sleep(0.5)
                    
                except Exception as e:
                    self.logger.error(f"Error collecting data for {org['acronym_EN']}: {e}")
                    continue
            
            # Save the collected data
            if org_stats_list:
                success = self.save_daily_data(datetime.now(), org_stats_list)
                self.logger.info(f"Collected data for {len(org_stats_list)} organizations")
                return success
            else:
                self.logger.warning("No data collected")
                return False
                
        except Exception as e:
            self.logger.error(f"Error in daily data collection: {e}")
            return False
    
    def get_last_update_time(self):
        """Get the timestamp of the last data update"""
        try:
            daily_files = list((self.data_dir / "daily").glob("daily_stats_*.csv"))
            if not daily_files:
                return None
            
            latest_file = max(daily_files, key=os.path.getctime)
            return datetime.fromtimestamp(os.path.getctime(latest_file))
            
        except Exception as e:
            self.logger.error(f"Error getting last update time: {e}")
            return None
    
    def get_system_stats(self):
        """Get overall system statistics"""
        try:
            stats = {
                'total_orgs': len(self.organizations_df),
                'total_data_points': 0,
                'days_of_data': 0
            }
            
            # Count data points
            daily_files = list((self.data_dir / "daily").glob("daily_stats_*.csv"))
            total_points = 0
            
            for file in daily_files:
                try:
                    df = pd.read_csv(file)
                    total_points += len(df)
                except:
                    pass
            
            stats['total_data_points'] = total_points
            stats['days_of_data'] = len(daily_files)
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting system stats: {e}")
            return {}
    
    def export_all_data(self):
        """Export all data to a single file"""
        try:
            export_dir = self.data_dir / "exports"
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            export_file = export_dir / f"full_export_{timestamp}.xlsx"
            
            with pd.ExcelWriter(export_file, engine='openpyxl') as writer:
                # Export organizations
                if not self.organizations_df.empty:
                    self.organizations_df.to_excel(writer, sheet_name='Organizations', index=False)
                
                # Export recent daily data
                recent_data = self.get_historical_data(30)
                if not recent_data.empty:
                    recent_data.to_excel(writer, sheet_name='Recent_Data', index=False)
                
                # Export historical summary
                historical_data = self.get_historical_data(90)
                if not historical_data.empty:
                    historical_data.to_excel(writer, sheet_name='Historical_Data', index=False)
            
            return str(export_file)
            
        except Exception as e:
            self.logger.error(f"Error exporting data: {e}")
            return None
    
    def clean_old_data(self, days_to_keep=90):
        """Clean data older than specified days"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            daily_dir = self.data_dir / "daily"
            
            cleaned_count = 0
            for file in daily_dir.glob("daily_stats_*.csv"):
                file_date = datetime.fromtimestamp(os.path.getctime(file))
                if file_date < cutoff_date:
                    file.unlink()
                    cleaned_count += 1
            
            return cleaned_count
            
        except Exception as e:
            self.logger.error(f"Error cleaning old data: {e}")
            return 0
