
#!/usr/bin/env python3
"""
Script to setup automated daily data collection via cron
"""

import os
import sys
from pathlib import Path
import subprocess

def setup_cron():
    """Setup cron job for daily data collection"""
    
    project_dir = Path(__file__).parent.absolute()
    collector_script = project_dir / "data_collector.py"
    
    # Make the collector script executable
    os.chmod(collector_script, 0o755)
    
    # Create cron entry (daily at 2 AM)
    cron_command = f"0 2 * * * cd {project_dir} && /usr/bin/python3 {collector_script}"
    
    print("Setting up daily data collection...")
    print(f"Project directory: {project_dir}")
    print(f"Collector script: {collector_script}")
    print(f"Cron command: {cron_command}")
    
    # Add to crontab
    try:
        # Get current crontab
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        current_cron = result.stdout if result.returncode == 0 else ""
        
        # Check if our cron job already exists
        if str(collector_script) in current_cron:
            print("Cron job already exists!")
            return True
        
        # Add our cron job
        new_cron = current_cron + f"\n{cron_command}\n"
        
        # Write new crontab
        process = subprocess.Popen(['crontab', '-'], stdin=subprocess.PIPE, text=True)
        process.communicate(input=new_cron)
        
        if process.returncode == 0:
            print("✅ Cron job set up successfully!")
            print("Daily data collection will run at 2:00 AM every day")
            return True
        else:
            print("❌ Failed to set up cron job")
            return False
            
    except Exception as e:
        print(f"❌ Error setting up cron job: {e}")
        return False

def remove_cron():
    """Remove the cron job"""
    try:
        project_dir = Path(__file__).parent.absolute()
        collector_script = project_dir / "data_collector.py"
        
        # Get current crontab
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        if result.returncode != 0:
            print("No crontab found")
            return True
        
        current_cron = result.stdout
        
        # Remove lines containing our script
        lines = current_cron.split('\n')
        filtered_lines = [line for line in lines if str(collector_script) not in line]
        new_cron = '\n'.join(filtered_lines)
        
        # Write new crontab
        process = subprocess.Popen(['crontab', '-'], stdin=subprocess.PIPE, text=True)
        process.communicate(input=new_cron)
        
        if process.returncode == 0:
            print("✅ Cron job removed successfully!")
            return True
        else:
            print("❌ Failed to remove cron job")
            return False
            
    except Exception as e:
        print(f"❌ Error removing cron job: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "remove":
        remove_cron()
    else:
        setup_cron()
