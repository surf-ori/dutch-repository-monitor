
# Dutch Research Monitor Dashboard

A comprehensive Streamlit dashboard for monitoring Dutch research organizations' repositories and CRIS systems using the OpenAIRE Graph API.

## Features

### 🔍 Real-time Monitoring
- **Daily Data Collection**: Automated collection of research metrics for 93+ Dutch organizations
- **Repository Health Tracking**: Monitor data freshness, publication counts, and system availability
- **Data Source Monitoring**: Track individual repository and CRIS system status

### 📊 Comprehensive Dashboard
- **Overview Page**: System-wide status with key metrics and alerts
- **Organization Details**: Deep dive into individual organization performance
- **Data Source Analysis**: Detailed view of repositories and CRIS systems
- **Analytics & Trends**: Historical analysis and trend identification

### 🚨 Alert System
- **Smart Notifications**: Alerts for publication drops, stale data, and system issues
- **Configurable Thresholds**: Customizable alert conditions
- **Historical Alert Tracking**: Complete audit trail of system issues

### 📈 Advanced Analytics
- **Trend Analysis**: Publication growth, data freshness trends
- **Comparative Analysis**: Organization and group performance comparisons
- **Correlation Studies**: Identify relationships between different metrics
- **Export Capabilities**: Download data for further analysis

## Installation

### Prerequisites
- Python 3.8+
- OpenAIRE API credentials (register at https://develop.openaire.eu/)

### Setup
1. **Clone or download the project**
```bash
cd /home/ubuntu/dutch_research_monitor
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure credentials**
   - Update `config.yaml` with your OpenAIRE API credentials
   - Ensure the organization data file is in the correct location

4. **Initialize data collection**
```bash
python data_collector.py
```

5. **Setup automated collection (optional)**
```bash
python setup_cron.py
```

## Usage

### Running the Dashboard
```bash
streamlit run app.py
```

The dashboard will be available at `http://localhost:8501`

### Manual Data Collection
```bash
python data_collector.py
```

### Setting up Automated Collection
```bash
# Setup daily collection at 2 AM
python setup_cron.py

# Remove automated collection
python setup_cron.py remove
```

## Project Structure

```
dutch_research_monitor/
├── app.py                  # Main Streamlit application
├── config.yaml            # API credentials and configuration
├── requirements.txt        # Python dependencies
├── data_collector.py       # Automated data collection script
├── setup_cron.py          # Cron job setup utility
├── utils/                  # Core utilities
│   ├── api_client.py      # OpenAIRE API integration
│   ├── data_manager.py    # Data storage and retrieval
│   └── alert_system.py    # Alert management
├── pages/                  # Dashboard pages
│   ├── overview.py        # Main dashboard
│   ├── organization_detail.py  # Organization details
│   ├── data_source_detail.py   # Data source analysis
│   └── analytics.py       # Advanced analytics
├── data/                   # Data storage
│   ├── daily/             # Daily statistics
│   ├── organizations/     # Organization metadata
│   ├── alerts/           # Alert history
│   └── exports/          # Data exports
└── logs/                  # Application logs
```

## Configuration

### API Configuration (`config.yaml`)
```yaml
CLIENT_ID: "your-client-id"
CLIENT_SECRET: "your-client-secret"
OpenAIRE_API: "https://api-beta.openaire.eu/graph/"
auth_url: "https://aai.openaire.eu/oidc/token"
Org_data_file: "data/nl-orgs-baseline.xlsx"
```

### Alert Thresholds
The alert system monitors:
- **Publication Drops**: 20% decrease in publications
- **Stale Data**: No publications for 30+ days
- **Data Freshness**: Data older than 14 days
- **System Availability**: No updates for 6+ hours

## Data Sources

### Monitored Organizations
- **93 Dutch Research Organizations**
- **Major Groups**: KNAW, NFU, NWO, TO2, Universities
- **Data Points**: Publications, repositories, CRIS systems

### Collected Metrics
- Total publications count
- Recent publications (last 30 days)
- Data source counts
- Data freshness indicators
- Repository health status
- System availability metrics

## API Integration

### OpenAIRE Graph API
- **Authentication**: OAuth2 client credentials flow
- **Endpoints**: Organizations, Publications, Data Sources
- **Rate Limiting**: Built-in delays to respect API limits
- **Error Handling**: Comprehensive retry and fallback mechanisms

## Deployment

### Local Development
```bash
streamlit run app.py --server.port 8501
```

### Production Deployment
1. **Configure reverse proxy** (nginx, Apache)
2. **Set up process manager** (systemd, supervisor)
3. **Configure SSL certificate**
4. **Set up monitoring** (logs, health checks)

### Docker Deployment (Optional)
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.address", "0.0.0.0"]
```

## Monitoring & Maintenance

### Daily Operations
- **Automated Data Collection**: Runs daily at 2 AM via cron
- **Alert Monitoring**: Check dashboard for active alerts
- **Data Quality**: Monitor collection success rates

### Weekly Maintenance
- **Log Review**: Check collection logs for errors
- **Performance Monitoring**: Monitor API response times
- **Data Export**: Backup critical data

### Monthly Tasks
- **Alert Threshold Review**: Adjust based on patterns
- **Data Cleanup**: Remove old temporary files
- **Performance Optimization**: Review and optimize queries

## Troubleshooting

### Common Issues

#### API Connection Errors
```bash
# Test API connection
python -c "from utils.api_client import OpenAIREClient; import yaml; config = yaml.safe_load(open('config.yaml')); client = OpenAIREClient(config); print('Connection:', client.test_connection())"
```

#### Data Collection Failures
- Check API credentials in `config.yaml`
- Verify internet connectivity
- Review logs in `logs/` directory

#### Dashboard Loading Issues
- Ensure all dependencies are installed
- Check data directory permissions
- Verify Streamlit is properly installed

### Log Files
- **Application Logs**: `logs/data_collection_YYYYMMDD.log`
- **Streamlit Logs**: Console output during dashboard operation
- **System Logs**: `/var/log/cron` for automated collection

## Contributing

### Development Setup
1. Fork the repository
2. Create a feature branch
3. Make changes with appropriate tests
4. Submit a pull request

### Coding Standards
- **Python**: PEP 8 compliance
- **Documentation**: Docstrings for all functions
- **Error Handling**: Comprehensive try-catch blocks
- **Logging**: Appropriate log levels and messages

## Support

### Resources
- **OpenAIRE API Documentation**: https://graph.openaire.eu/docs/
- **Streamlit Documentation**: https://docs.streamlit.io/
- **Project Issues**: GitHub issues tracker

### Getting Help
1. Check the troubleshooting section
2. Review log files for error details
3. Consult OpenAIRE API documentation
4. Submit issue with detailed error information

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- **OpenAIRE**: For providing the comprehensive research graph API
- **Dutch Research Organizations**: For their commitment to open science
- **Streamlit Community**: For the excellent dashboard framework
