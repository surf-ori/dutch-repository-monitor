
#!/usr/bin/env python3
"""
Daily data collection script for Dutch Research Monitor
This script can be run via cron for automated daily data collection
"""

import sys
import os
from pathlib import Path
import yaml
import logging
from datetime import datetime

# Add the project directory to Python path
project_dir = Path(__file__).parent
sys.path.append(str(project_dir))

from utils.api_client import OpenAIREClient
from utils.data_manager import DataManager
from utils.alert_system import AlertSystem

def main():
    """Main data collection function"""
    
    # Setup logging
    log_dir = project_dir / "logs"
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / f"data_collection_{datetime.now().strftime('%Y%m%d')}.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info("Starting daily data collection...")
    
    try:
        # Load configuration
        config_file = project_dir / "config.yaml"
        with open(config_file, 'r') as file:
            config = yaml.safe_load(file)
        
        logger.info(f"Using API endpoint: {config.get('OpenAIRE_API', 'Not configured')}")
        
        # Initialize components
        api_client = OpenAIREClient(config)
        data_manager = DataManager()
        alert_system = AlertSystem()
        
        # Test API connection
        logger.info("Testing API connection...")
        if not api_client.test_connection():
            logger.error("Failed to connect to OpenAIRE API - check logs for detailed error information")
            return False
        
        logger.info("API connection successful - comprehensive logging enabled")
        
        # Collect daily data
        logger.info("Starting comprehensive data collection with enhanced logging...")
        success = data_manager.collect_daily_data(api_client)
        
        if success:
            logger.info("Data collection completed successfully")
            
            # Check for alerts
            alerts = alert_system.check_alerts(data_manager)
            if alerts:
                logger.info(f"Generated {len(alerts)} alerts")
                for alert in alerts:
                    logger.warning(f"Alert: {alert['type']} - {alert['organization']} - {alert['message']}")
            else:
                logger.info("No alerts generated")
            
            return True
        else:
            logger.error("Data collection failed")
            return False
            
    except Exception as e:
        logger.error(f"Error in data collection: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
