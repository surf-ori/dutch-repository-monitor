
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np

def show_page(data_manager, alert_system):
    """Show the main dashboard overview page"""
    
    st.header("📊 Dashboard Overview")
    
    # Get recent data
    recent_data = data_manager.load_daily_data()
    historical_data = data_manager.get_historical_data(30)
    
    if recent_data.empty:
        st.warning("No data available. Please run data collection first.")
        return
    
    # Check alerts
    alerts = alert_system.check_alerts(data_manager)
    alert_summary = alert_system.get_alert_summary()
    
    # Display alert banner if there are critical alerts
    critical_alerts = [a for a in alerts if a['severity'] == 'critical']
    if critical_alerts:
        st.error(f"🚨 **{len(critical_alerts)} Critical Alert(s)** - Immediate attention required!")
        for alert in critical_alerts[:3]:  # Show top 3
            st.error(f"**{alert['organization']}**: {alert['message']}")
    
    # Key metrics row
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        total_orgs = len(recent_data)
        st.metric("Total Organizations", total_orgs)
    
    with col2:
        total_publications = recent_data['publications_total'].sum()
        st.metric("Total Publications", f"{total_publications:,}")
    
    with col3:
        recent_publications = recent_data['publications_recent'].sum()
        st.metric("Recent Publications", recent_publications)
    
    with col4:
        healthy_orgs = len(recent_data[recent_data['repository_health'] == 'healthy'])
        st.metric("Healthy Repositories", healthy_orgs)
    
    with col5:
        active_alerts = alert_summary.get('total_alerts', 0)
        st.metric("Active Alerts", active_alerts, delta=alert_summary.get('critical_alerts', 0))
    
    # Charts row
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Repository Health Status")
        
        # Health status distribution
        health_counts = recent_data['repository_health'].value_counts()
        colors = {'healthy': '#28a745', 'warning': '#ffc107', 'critical': '#dc3545', 'unknown': '#6c757d'}
        
        fig_health = px.pie(
            values=health_counts.values,
            names=health_counts.index,
            color=health_counts.index,
            color_discrete_map=colors,
            title="Repository Health Distribution"
        )
        fig_health.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_health, use_container_width=True)
    
    with col2:
        st.subheader("Publications by Organization Group")
        
        # Group publications by main grouping
        group_pubs = recent_data.groupby('main_grouping')['publications_total'].sum().sort_values(ascending=True)
        
        fig_groups = px.bar(
            x=group_pubs.values,
            y=group_pubs.index,
            orientation='h',
            title="Total Publications by Group",
            color=group_pubs.values,
            color_continuous_scale='Blues'
        )
        fig_groups.update_layout(showlegend=False)
        st.plotly_chart(fig_groups, use_container_width=True)
    
    # Historical trends
    if not historical_data.empty:
        st.subheader("📈 Historical Trends (Last 30 Days)")
        
        # Aggregate daily totals
        daily_trends = historical_data.groupby('date').agg({
            'publications_total': 'sum',
            'publications_recent': 'sum',
            'data_sources_count': 'sum'
        }).reset_index()
        
        daily_trends['date'] = pd.to_datetime(daily_trends['date'])
        daily_trends = daily_trends.sort_values('date')
        
        # Create trend chart
        fig_trends = go.Figure()
        
        fig_trends.add_trace(go.Scatter(
            x=daily_trends['date'],
            y=daily_trends['publications_total'],
            mode='lines+markers',
            name='Total Publications',
            line=dict(color='#1f77b4', width=3)
        ))
        
        fig_trends.add_trace(go.Scatter(
            x=daily_trends['date'],
            y=daily_trends['publications_recent'],
            mode='lines+markers',
            name='Recent Publications',
            line=dict(color='#ff7f0e', width=2),
            yaxis='y2'
        ))
        
        fig_trends.update_layout(
            title="Publication Trends Over Time",
            xaxis_title="Date",
            yaxis_title="Total Publications",
            yaxis2=dict(title="Recent Publications", overlaying='y', side='right'),
            hovermode='x unified'
        )
        
        st.plotly_chart(fig_trends, use_container_width=True)
    
    # Organizations table
    st.subheader("🏛️ Organizations Status")
    
    # Prepare display data
    display_data = recent_data[[
        'organization_name', 'acronym', 'main_grouping', 
        'publications_total', 'publications_recent', 
        'data_sources_count', 'repository_health', 
        'data_freshness_days'
    ]].copy()
    
    # Add status indicators
    def get_status_indicator(health):
        if health == 'healthy':
            return "🟢"
        elif health == 'warning':
            return "🟡"
        elif health == 'critical':
            return "🔴"
        else:
            return "⚪"
    
    display_data['Status'] = display_data['repository_health'].apply(get_status_indicator)
    
    # Rename columns for display
    display_data = display_data.rename(columns={
        'organization_name': 'Organization',
        'acronym': 'Acronym',
        'main_grouping': 'Group',
        'publications_total': 'Total Pubs',
        'publications_recent': 'Recent Pubs',
        'data_sources_count': 'Data Sources',
        'data_freshness_days': 'Days Since Update'
    })
    
    # Add filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        group_filter = st.selectbox(
            "Filter by Group",
            options=['All'] + sorted(display_data['Group'].unique().tolist())
        )
    
    with col2:
        health_filter = st.selectbox(
            "Filter by Health",
            options=['All', 'healthy', 'warning', 'critical', 'unknown']
        )
    
    with col3:
        min_pubs = st.number_input(
            "Minimum Publications",
            min_value=0,
            value=0,
            step=1
        )
    
    # Apply filters
    filtered_data = display_data.copy()
    
    if group_filter != 'All':
        filtered_data = filtered_data[filtered_data['Group'] == group_filter]
    
    if health_filter != 'All':
        filtered_data = filtered_data[filtered_data['repository_health'] == health_filter]
    
    if min_pubs > 0:
        filtered_data = filtered_data[filtered_data['Total Pubs'] >= min_pubs]
    
    # Display filtered table
    st.dataframe(
        filtered_data.drop('repository_health', axis=1),
        use_container_width=True,
        hide_index=True
    )
    
    # Download data option
    if st.button("📥 Download Current Data"):
        csv = recent_data.to_csv(index=False)
        st.download_button(
            label="💾 Download CSV",
            data=csv,
            file_name=f"dutch_research_data_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    
    # System status
    st.subheader("⚙️ System Status")
    
    last_update = data_manager.get_last_update_time()
    system_stats = data_manager.get_system_stats()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if last_update:
            time_diff = datetime.now() - last_update
            if time_diff.total_seconds() < 3600:  # Less than 1 hour
                st.success(f"✅ System Healthy - Last update: {time_diff.seconds // 60} minutes ago")
            elif time_diff.total_seconds() < 86400:  # Less than 1 day
                st.warning(f"⚠️ System Warning - Last update: {time_diff.seconds // 3600} hours ago")
            else:
                st.error(f"❌ System Critical - Last update: {time_diff.days} days ago")
        else:
            st.error("❌ No update information available")
    
    with col2:
        st.info(f"📊 Total Data Points: {system_stats.get('total_data_points', 0):,}")
    
    with col3:
        st.info(f"📅 Days of Historical Data: {system_stats.get('days_of_data', 0)}")
