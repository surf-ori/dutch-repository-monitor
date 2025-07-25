
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import yaml
import os
import json
import glob
import zipfile
import io
from pathlib import Path

# Import our custom modules
from utils.api_client import OpenAIREClient
from utils.data_manager import DataManager
from utils.alert_system import AlertSystem
from pages import overview, organization_detail, data_source_detail, analytics

# Page config
st.set_page_config(
    page_title="Dutch Research Monitor",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1f77b4 0%, #ff7f0e 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .status-indicator {
        display: inline-block;
        width: 12px;
        height: 12px;
        border-radius: 50%;
        margin-right: 8px;
    }
    
    .status-healthy { background-color: #28a745; }
    .status-warning { background-color: #ffc107; }
    .status-critical { background-color: #dc3545; }
    
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #1f77b4;
    }
    
    .alert-banner {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 5px;
        padding: 10px;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

def load_config():
    """Load configuration from yaml file"""
    try:
        with open('config.yaml', 'r') as file:
            return yaml.safe_load(file)
    except Exception as e:
        st.error(f"Error loading configuration: {e}")
        return None

def get_log_files():
    """Get list of available log files"""
    try:
        logs_dir = Path("logs")
        if not logs_dir.exists():
            return []
        
        log_files = []
        
        # Get API request logs
        api_logs = list(logs_dir.glob("api_requests_*.log"))
        for log_file in api_logs:
            log_files.append({
                'name': log_file.name,
                'path': str(log_file),
                'type': 'API Requests',
                'size': log_file.stat().st_size,
                'modified': datetime.fromtimestamp(log_file.stat().st_mtime),
                'date': log_file.name.replace('api_requests_', '').replace('.log', '')
            })
        
        # Get data collection logs
        data_logs = list(logs_dir.glob("data_collection_*.log"))
        for log_file in data_logs:
            log_files.append({
                'name': log_file.name,
                'path': str(log_file),
                'type': 'Data Collection',
                'size': log_file.stat().st_size,
                'modified': datetime.fromtimestamp(log_file.stat().st_mtime),
                'date': log_file.name.replace('data_collection_', '').replace('.log', '')
            })
        
        # Sort by modification time (newest first)
        log_files.sort(key=lambda x: x['modified'], reverse=True)
        return log_files
        
    except Exception as e:
        st.error(f"Error getting log files: {e}")
        return []

def read_log_file(file_path, max_lines=1000):
    """Read log file content with optional line limit"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        if len(lines) > max_lines:
            return {
                'content': ''.join(lines[-max_lines:]),
                'truncated': True,
                'total_lines': len(lines),
                'shown_lines': max_lines
            }
        else:
            return {
                'content': ''.join(lines),
                'truncated': False,
                'total_lines': len(lines),
                'shown_lines': len(lines)
            }
    except Exception as e:
        return {
            'content': f"Error reading file: {e}",
            'truncated': False,
            'total_lines': 0,
            'shown_lines': 0
        }

def parse_api_log_entries(file_path, max_entries=50):
    """Parse API log entries from JSON-formatted log file"""
    try:
        entries = []
        current_entry = ""
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('{'):
                    # Start of new JSON entry
                    if current_entry:
                        try:
                            entry = json.loads(current_entry)
                            entries.append(entry)
                            if len(entries) >= max_entries:
                                break
                        except json.JSONDecodeError:
                            pass
                    current_entry = line
                elif current_entry:
                    current_entry += line
            
            # Process last entry
            if current_entry:
                try:
                    entry = json.loads(current_entry)
                    entries.append(entry)
                except json.JSONDecodeError:
                    pass
        
        return entries[-max_entries:] if len(entries) > max_entries else entries
        
    except Exception as e:
        st.error(f"Error parsing API log entries: {e}")
        return []

def create_log_archive():
    """Create a ZIP archive of all log files"""
    try:
        logs_dir = Path("logs")
        if not logs_dir.exists():
            return None
        
        # Create in-memory ZIP file
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for log_file in logs_dir.glob("*.log"):
                zip_file.write(log_file, log_file.name)
        
        zip_buffer.seek(0)
        return zip_buffer.getvalue()
        
    except Exception as e:
        st.error(f"Error creating log archive: {e}")
        return None

def format_file_size(size_bytes):
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0B"
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    return f"{size_bytes:.1f} {size_names[i]}"

def initialize_app():
    """Initialize the application components"""
    # Load configuration
    config = load_config()
    if not config:
        st.error("Failed to load configuration. Please check config.yaml file.")
        st.stop()
    
    # Initialize components
    api_client = OpenAIREClient(config)
    data_manager = DataManager()
    alert_system = AlertSystem()
    
    return config, api_client, data_manager, alert_system

def main():
    # Initialize app components
    config, api_client, data_manager, alert_system = initialize_app()
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🔬 Dutch Research Monitor</h1>
        <p>Real-time monitoring of Dutch research organizations' repositories and CRIS systems</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    
    # Check for alerts
    alerts = alert_system.get_active_alerts()
    if alerts:
        st.sidebar.markdown("### 🚨 Active Alerts")
        for alert in alerts[:3]:  # Show top 3 alerts
            st.sidebar.error(f"**{alert['type']}**: {alert['message']}")
    
    # Navigation menu
    page_options = {
        "📊 Dashboard Overview": "overview",
        "🏛️ Organizations": "organizations", 
        "💾 Data Sources": "data_sources",
        "📈 Analytics & Trends": "analytics",
        "📝 Log Management": "logs",
        "⚙️ Settings": "settings"
    }
    
    selected_page = st.sidebar.selectbox(
        "Select Page",
        options=list(page_options.keys()),
        index=0
    )
    
    page = page_options[selected_page]
    
    # Display last update time
    last_update = data_manager.get_last_update_time()
    if last_update:
        st.sidebar.info(f"Last updated: {last_update.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Enhanced manual refresh button
    if st.sidebar.button("🔄 Refresh Data"):
        with st.spinner("Refreshing data..."):
            # Create progress placeholders
            progress_bar = st.sidebar.progress(0)
            status_text = st.sidebar.empty()
            
            # Initialize progress tracking
            if not data_manager.organizations_df.empty:
                total_orgs = len(data_manager.organizations_df)
                status_text.text(f"Starting data collection for {total_orgs} organizations...")
                
                # Test API connection first
                if api_client.test_connection():
                    status_text.text("API connection successful. Starting data collection...")
                    success = data_manager.collect_daily_data(api_client)
                    progress_bar.progress(100)
                    
                    if success:
                        st.sidebar.success("✅ Data refreshed successfully!")
                        status_text.text("Data collection completed.")
                        
                        # Show collection summary
                        log_files = get_log_files()
                        if log_files:
                            latest_log = log_files[0]
                            st.sidebar.info(f"📝 Latest log: {latest_log['name']} ({format_file_size(latest_log['size'])})")
                        
                        st.rerun()
                    else:
                        st.sidebar.error("❌ Failed to refresh data. Check logs for details.")
                        status_text.text("Data collection failed.")
                else:
                    st.sidebar.error("❌ API connection failed. Cannot refresh data.")
                    status_text.text("API connection test failed.")
            else:
                st.sidebar.error("❌ No organizations data available.")
                status_text.text("No organizations loaded.")
    
    # Route to appropriate page
    if page == "overview":
        overview.show_page(data_manager, alert_system)
    elif page == "organizations":
        organization_detail.show_page(data_manager, api_client)
    elif page == "data_sources":
        data_source_detail.show_page(data_manager, api_client)
    elif page == "analytics":
        analytics.show_page(data_manager)
    elif page == "logs":
        show_log_management_page()
    elif page == "settings":
        show_settings_page(config, data_manager)

def show_log_management_page():
    """Show comprehensive log management and monitoring page"""
    st.header("📝 Log Management & Monitoring")
    
    # Get available log files
    log_files = get_log_files()
    
    if not log_files:
        st.warning("No log files found. Logs will appear after data collection runs.")
        return
    
    # Log file summary
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_files = len(log_files)
        st.metric("Total Log Files", total_files)
    
    with col2:
        total_size = sum(log['size'] for log in log_files)
        st.metric("Total Size", format_file_size(total_size))
    
    with col3:
        api_logs = [log for log in log_files if log['type'] == 'API Requests']
        st.metric("API Request Logs", len(api_logs))
    
    with col4:
        data_logs = [log for log in log_files if log['type'] == 'Data Collection']
        st.metric("Data Collection Logs", len(data_logs))
    
    st.divider()
    
    # Create tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Log Files", "🔍 Log Viewer", "📊 API Requests", "📥 Downloads"])
    
    with tab1:
        st.subheader("Available Log Files")
        
        # Filter options
        col1, col2 = st.columns(2)
        with col1:
            log_type_filter = st.selectbox(
                "Filter by Type", 
                ["All", "API Requests", "Data Collection"]
            )
        
        with col2:
            date_filter = st.date_input(
                "Filter by Date (optional)",
                value=None,
                help="Filter logs by specific date"
            )
        
        # Apply filters
        filtered_logs = log_files
        if log_type_filter != "All":
            filtered_logs = [log for log in filtered_logs if log['type'] == log_type_filter]
        
        if date_filter:
            date_str = date_filter.strftime('%Y%m%d')
            filtered_logs = [log for log in filtered_logs if date_str in log['date']]
        
        # Display log files table
        if filtered_logs:
            df_logs = pd.DataFrame(filtered_logs)
            df_logs['Size'] = df_logs['size'].apply(format_file_size)
            df_logs['Modified'] = df_logs['modified'].dt.strftime('%Y-%m-%d %H:%M:%S')
            
            display_df = df_logs[['name', 'type', 'Size', 'Modified']].rename(columns={
                'name': 'File Name',
                'type': 'Type',
                'Modified': 'Last Modified'
            })
            
            st.dataframe(display_df, use_container_width=True)
        else:
            st.info("No log files match the selected filters.")
    
    with tab2:
        st.subheader("Log File Viewer")
        
        if log_files:
            # Select log file to view
            selected_log = st.selectbox(
                "Select log file to view",
                options=[f"{log['name']} ({log['type']}, {format_file_size(log['size'])})" for log in log_files],
                format_func=lambda x: x
            )
            
            if selected_log:
                # Find selected log
                log_name = selected_log.split(' (')[0]
                selected_log_info = next((log for log in log_files if log['name'] == log_name), None)
                
                if selected_log_info:
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        max_lines = st.slider("Max lines to display", 100, 5000, 1000)
                    
                    with col2:
                        # Download individual file button
                        if st.button("📥 Download File"):
                            try:
                                with open(selected_log_info['path'], 'rb') as f:
                                    st.download_button(
                                        label=f"Download {selected_log_info['name']}",
                                        data=f.read(),
                                        file_name=selected_log_info['name'],
                                        mime="text/plain"
                                    )
                            except Exception as e:
                                st.error(f"Error preparing download: {e}")
                    
                    # Read and display log content
                    log_content = read_log_file(selected_log_info['path'], max_lines)
                    
                    if log_content['truncated']:
                        st.warning(f"⚠️ Showing last {log_content['shown_lines']} lines of {log_content['total_lines']} total lines")
                    
                    st.text_area(
                        f"Content of {selected_log_info['name']}",
                        value=log_content['content'],
                        height=400,
                        disabled=True
                    )
    
    with tab3:
        st.subheader("API Request Analysis")
        
        # Get API log files
        api_log_files = [log for log in log_files if log['type'] == 'API Requests']
        
        if api_log_files:
            selected_api_log = st.selectbox(
                "Select API log file",
                options=[f"{log['name']} ({format_file_size(log['size'])})" for log in api_log_files]
            )
            
            if selected_api_log:
                api_log_name = selected_api_log.split(' (')[0]
                selected_api_log_info = next((log for log in api_log_files if log['name'] == api_log_name), None)
                
                if selected_api_log_info:
                    # Parse API log entries
                    with st.spinner("Parsing API log entries..."):
                        entries = parse_api_log_entries(selected_api_log_info['path'], max_entries=100)
                    
                    if entries:
                        st.success(f"Found {len(entries)} API request entries")
                        
                        # Summary metrics
                        success_count = sum(1 for entry in entries if entry.get('success', False))
                        failed_count = len(entries) - success_count
                        avg_response_time = sum(entry.get('response_time_ms', 0) for entry in entries) / len(entries)
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Successful Requests", success_count)
                        with col2:
                            st.metric("Failed Requests", failed_count)
                        with col3:
                            st.metric("Avg Response Time", f"{avg_response_time:.1f}ms")
                        
                        # Display entries
                        st.subheader("Recent API Requests")
                        
                        for i, entry in enumerate(reversed(entries[-10:])):  # Show last 10 entries
                            with st.expander(
                                f"{'✅' if entry.get('success') else '❌'} {entry.get('method', 'GET')} - "
                                f"{entry.get('context', {}).get('operation', 'Unknown')} "
                                f"({entry.get('response_time_ms', 0):.1f}ms)"
                            ):
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    st.write("**Request Details:**")
                                    st.code(f"URL: {entry.get('url', 'N/A')}")
                                    st.code(f"Method: {entry.get('method', 'N/A')}")
                                    if entry.get('parameters'):
                                        st.code(f"Parameters: {json.dumps(entry['parameters'], indent=2)}")
                                
                                with col2:
                                    st.write("**Response Details:**")
                                    st.code(f"Status Code: {entry.get('status_code', 'N/A')}")
                                    st.code(f"Response Time: {entry.get('response_time_ms', 'N/A')}ms")
                                    if entry.get('response_summary'):
                                        st.code(f"Summary: {json.dumps(entry['response_summary'], indent=2)}")
                                    
                                    if entry.get('error'):
                                        st.error(f"Error: {entry['error']}")
                    else:
                        st.info("No API request entries found in the selected log file.")
        else:
            st.info("No API request log files available.")
    
    with tab4:
        st.subheader("Download Options")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Individual Files**")
            if log_files:
                for log_file in log_files[:5]:  # Show first 5 files
                    try:
                        with open(log_file['path'], 'rb') as f:
                            st.download_button(
                                label=f"📥 {log_file['name']} ({format_file_size(log_file['size'])})",
                                data=f.read(),
                                file_name=log_file['name'],
                                mime="text/plain",
                                key=f"download_{log_file['name']}"
                            )
                    except Exception as e:
                        st.error(f"Error with {log_file['name']}: {e}")
                
                if len(log_files) > 5:
                    st.info(f"... and {len(log_files) - 5} more files")
        
        with col2:
            st.write("**Complete Archive**")
            if st.button("📦 Create Complete Log Archive"):
                with st.spinner("Creating archive..."):
                    archive_data = create_log_archive()
                    
                    if archive_data:
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        st.download_button(
                            label="📥 Download Complete Archive",
                            data=archive_data,
                            file_name=f"dutch_monitor_logs_{timestamp}.zip",
                            mime="application/zip"
                        )
                        st.success("✅ Archive created successfully!")
                    else:
                        st.error("❌ Failed to create archive")
            
            st.info("The complete archive includes all log files in a single ZIP download.")

def show_settings_page(config, data_manager):
    """Show settings and configuration page"""
    st.header("⚙️ Settings & Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("System Information")
        st.info(f"**API Endpoint**: {config.get('OpenAIRE_API', 'Not configured')}")
        st.info(f"**Organizations File**: {config.get('Org_data_file', 'Not configured')}")
        
        # Data statistics
        stats = data_manager.get_system_stats()
        st.metric("Total Organizations", stats.get('total_orgs', 0))
        st.metric("Data Points Collected", stats.get('total_data_points', 0))
        st.metric("Days of Historical Data", stats.get('days_of_data', 0))
    
    with col2:
        st.subheader("Data Management")
        
        # Export data
        if st.button("📁 Export All Data"):
            export_path = data_manager.export_all_data()
            if export_path:
                st.success(f"Data exported to: {export_path}")
            else:
                st.error("Failed to export data")
        
        # Clear old data
        days_to_keep = st.number_input("Days of data to keep", min_value=30, max_value=365, value=90)
        if st.button("🗑️ Clean Old Data"):
            cleaned = data_manager.clean_old_data(days_to_keep)
            st.success(f"Cleaned {cleaned} old records")
        
        # Force data collection
        if st.button("🔄 Force Full Data Collection"):
            with st.spinner("Collecting data for all organizations..."):
                # This would trigger a full data collection cycle
                st.info("Full data collection initiated. This may take several minutes.")

if __name__ == "__main__":
    main()
