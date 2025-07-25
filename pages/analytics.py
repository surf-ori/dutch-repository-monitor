
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np

def show_page(data_manager):
    """Show analytics and trends page"""
    
    st.header("📈 Analytics & Trends")
    
    # Load historical data
    historical_data = data_manager.get_historical_data(90)  # Last 90 days
    
    if historical_data.empty:
        st.warning("No historical data available for analysis.")
        return
    
    # Data preparation
    historical_data['date'] = pd.to_datetime(historical_data['date'])
    historical_data = historical_data.sort_values(['date', 'organization_name'])
    
    # Time period selector
    col1, col2 = st.columns(2)
    
    with col1:
        period_options = {
            "Last 7 days": 7,
            "Last 30 days": 30,
            "Last 60 days": 60,
            "Last 90 days": 90
        }
        selected_period = st.selectbox("Analysis Period", list(period_options.keys()), index=1)
        days = period_options[selected_period]
    
    with col2:
        # Metric selector
        metric_options = {
            "Total Publications": "publications_total",
            "Recent Publications": "publications_recent",
            "Data Sources Count": "data_sources_count",
            "Data Freshness (Days)": "data_freshness_days"
        }
        selected_metric = st.selectbox("Primary Metric", list(metric_options.keys()))
        metric_column = metric_options[selected_metric]
    
    # Filter data by selected period
    cutoff_date = historical_data['date'].max() - timedelta(days=days)
    period_data = historical_data[historical_data['date'] >= cutoff_date]
    
    # Overview metrics
    st.subheader("📊 Overview Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_orgs = period_data['organization_name'].nunique()
        st.metric("Organizations Monitored", total_orgs)
    
    with col2:
        total_data_points = len(period_data)
        st.metric("Data Points Collected", f"{total_data_points:,}")
    
    with col3:
        avg_publications = period_data['publications_total'].mean()
        st.metric("Avg Publications per Org", f"{avg_publications:.0f}")
    
    with col4:
        healthy_pct = (period_data['repository_health'] == 'healthy').mean() * 100
        st.metric("Healthy Repositories %", f"{healthy_pct:.1f}%")
    
    # Time series analysis
    st.subheader("📈 Time Series Analysis")
    
    # Aggregate daily data
    daily_aggregates = period_data.groupby('date').agg({
        'publications_total': ['sum', 'mean'],
        'publications_recent': ['sum', 'mean'],
        'data_sources_count': ['sum', 'mean'],
        'data_freshness_days': 'mean',
        'organization_name': 'count'
    }).round(2)
    
    # Flatten column names
    daily_aggregates.columns = ['_'.join(col).strip() for col in daily_aggregates.columns]
    daily_aggregates = daily_aggregates.reset_index()
    
    # Create time series chart
    fig_timeseries = go.Figure()
    
    if metric_column == 'publications_total':
        fig_timeseries.add_trace(go.Scatter(
            x=daily_aggregates['date'],
            y=daily_aggregates['publications_total_sum'],
            mode='lines+markers',
            name='Total Publications (Sum)',
            line=dict(color='#1f77b4', width=3)
        ))
        
        fig_timeseries.add_trace(go.Scatter(
            x=daily_aggregates['date'],
            y=daily_aggregates['publications_total_mean'],
            mode='lines+markers',
            name='Avg Publications per Org',
            line=dict(color='#ff7f0e', width=2),
            yaxis='y2'
        ))
        
        fig_timeseries.update_layout(
            title="Publications Trends Over Time",
            xaxis_title="Date",
            yaxis_title="Total Publications",
            yaxis2=dict(title="Average Publications per Org", overlaying='y', side='right')
        )
    
    elif metric_column == 'publications_recent':
        fig_timeseries.add_trace(go.Scatter(
            x=daily_aggregates['date'],
            y=daily_aggregates['publications_recent_sum'],
            mode='lines+markers',
            name='Recent Publications (Sum)',
            line=dict(color='#2ca02c', width=3)
        ))
        
        fig_timeseries.update_layout(
            title="Recent Publications Trends Over Time",
            xaxis_title="Date",
            yaxis_title="Recent Publications"
        )
    
    elif metric_column == 'data_sources_count':
        fig_timeseries.add_trace(go.Scatter(
            x=daily_aggregates['date'],
            y=daily_aggregates['data_sources_count_sum'],
            mode='lines+markers',
            name='Total Data Sources',
            line=dict(color='#d62728', width=3)
        ))
        
        fig_timeseries.update_layout(
            title="Data Sources Count Over Time",
            xaxis_title="Date",
            yaxis_title="Total Data Sources"
        )
    
    else:  # data_freshness_days
        fig_timeseries.add_trace(go.Scatter(
            x=daily_aggregates['date'],
            y=daily_aggregates['data_freshness_days_mean'],
            mode='lines+markers',
            name='Avg Data Freshness',
            line=dict(color='#9467bd', width=3)
        ))
        
        # Add threshold lines
        fig_timeseries.add_hline(y=7, line_dash="dash", line_color="green", 
                                annotation_text="Healthy threshold")
        fig_timeseries.add_hline(y=30, line_dash="dash", line_color="orange", 
                                annotation_text="Warning threshold")
        
        fig_timeseries.update_layout(
            title="Data Freshness Trends Over Time",
            xaxis_title="Date",
            yaxis_title="Average Days Since Last Publication"
        )
    
    fig_timeseries.update_layout(hovermode='x unified')
    st.plotly_chart(fig_timeseries, use_container_width=True)
    
    # Organization comparison
    st.subheader("🏛️ Organization Comparison")
    
    # Get latest data for each organization
    latest_data = period_data.groupby('organization_name').last().reset_index()
    
    # Top performers
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🏆 Top Performers by Publications")
        top_pubs = latest_data.nlargest(10, 'publications_total')[
            ['organization_name', 'acronym', 'publications_total', 'publications_recent']
        ]
        top_pubs.columns = ['Organization', 'Acronym', 'Total Pubs', 'Recent Pubs']
        st.dataframe(top_pubs, hide_index=True)
    
    with col2:
        st.subheader("⚠️ Organizations Needing Attention")
        # Organizations with critical or warning status
        attention_needed = latest_data[
            (latest_data['repository_health'].isin(['critical', 'warning'])) |
            (latest_data['data_freshness_days'] > 14)
        ].nlargest(10, 'data_freshness_days')[
            ['organization_name', 'acronym', 'repository_health', 'data_freshness_days']
        ]
        attention_needed.columns = ['Organization', 'Acronym', 'Health Status', 'Days Since Update']
        st.dataframe(attention_needed, hide_index=True)
    
    # Correlation analysis
    st.subheader("🔗 Correlation Analysis")
    
    # Calculate correlations
    numeric_columns = ['publications_total', 'publications_recent', 'data_sources_count', 'data_freshness_days']
    correlation_data = latest_data[numeric_columns].corr()
    
    # Create correlation heatmap
    fig_corr = px.imshow(
        correlation_data,
        text_auto=True,
        aspect="auto",
        title="Correlation Matrix of Key Metrics",
        color_continuous_scale='RdBu_r'
    )
    fig_corr.update_layout(height=400)
    st.plotly_chart(fig_corr, use_container_width=True)
    
    # Group analysis
    st.subheader("🏢 Group Analysis")
    
    # Analysis by main grouping
    group_analysis = latest_data.groupby('main_grouping').agg({
        'organization_name': 'count',
        'publications_total': ['sum', 'mean'],
        'publications_recent': ['sum', 'mean'],
        'data_sources_count': ['sum', 'mean'],
        'data_freshness_days': 'mean'
    }).round(2)
    
    # Flatten column names
    group_analysis.columns = ['_'.join(col).strip() for col in group_analysis.columns]
    group_analysis = group_analysis.reset_index()
    
    # Rename columns for display
    display_columns = {
        'main_grouping': 'Group',
        'organization_name_count': 'Organizations Count',
        'publications_total_sum': 'Total Publications',
        'publications_total_mean': 'Avg Publications',
        'publications_recent_sum': 'Recent Publications',
        'publications_recent_mean': 'Avg Recent Pubs',
        'data_sources_count_sum': 'Total Data Sources',
        'data_sources_count_mean': 'Avg Data Sources',
        'data_freshness_days_mean': 'Avg Data Freshness (Days)'
    }
    
    group_analysis_display = group_analysis.rename(columns=display_columns)
    st.dataframe(group_analysis_display, hide_index=True, use_container_width=True)
    
    # Group comparison charts
    col1, col2 = st.columns(2)
    
    with col1:
        fig_group_pubs = px.bar(
            group_analysis,
            x='main_grouping',
            y='publications_total_sum',
            title="Total Publications by Group",
            labels={'publications_total_sum': 'Total Publications', 'main_grouping': 'Group'},
            color='publications_total_sum',
            color_continuous_scale='Blues'
        )
        st.plotly_chart(fig_group_pubs, use_container_width=True)
    
    with col2:
        fig_group_freshness = px.bar(
            group_analysis,
            x='main_grouping',
            y='data_freshness_days_mean',
            title="Average Data Freshness by Group",
            labels={'data_freshness_days_mean': 'Avg Days Since Update', 'main_grouping': 'Group'},
            color='data_freshness_days_mean',
            color_continuous_scale='Reds'
        )
        # Add threshold line
        fig_group_freshness.add_hline(y=14, line_dash="dash", line_color="orange", 
                                     annotation_text="Warning threshold")
        st.plotly_chart(fig_group_freshness, use_container_width=True)
    
    # Trend analysis
    st.subheader("📊 Trend Analysis")
    
    # Calculate growth rates
    if len(period_data['date'].unique()) >= 7:  # Need at least a week of data
        
        # Get first and last week data
        unique_dates = sorted(period_data['date'].unique())
        first_week_end = unique_dates[6] if len(unique_dates) > 6 else unique_dates[-1]
        last_week_start = unique_dates[-7] if len(unique_dates) > 6 else unique_dates[0]
        
        first_week_data = period_data[period_data['date'] <= first_week_end].groupby('organization_name').agg({
            'publications_total': 'mean'
        })
        
        last_week_data = period_data[period_data['date'] >= last_week_start].groupby('organization_name').agg({
            'publications_total': 'mean'
        })
        
        # Calculate growth rates
        growth_data = []
        for org in first_week_data.index:
            if org in last_week_data.index:
                first_val = first_week_data.loc[org, 'publications_total']
                last_val = last_week_data.loc[org, 'publications_total']
                
                if first_val > 0:
                    growth_rate = ((last_val - first_val) / first_val) * 100
                    growth_data.append({
                        'Organization': org,
                        'First Week Avg': first_val,
                        'Last Week Avg': last_val,
                        'Growth Rate (%)': growth_rate
                    })
        
        if growth_data:
            growth_df = pd.DataFrame(growth_data)
            growth_df = growth_df.sort_values('Growth Rate (%)', ascending=False)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📈 Fastest Growing Organizations")
                top_growth = growth_df.head(10)
                st.dataframe(top_growth, hide_index=True)
            
            with col2:
                st.subheader("📉 Declining Organizations")
                declining = growth_df[growth_df['Growth Rate (%)'] < 0].head(10)
                if not declining.empty:
                    st.dataframe(declining, hide_index=True)
                else:
                    st.info("No declining organizations detected in this period.")
    
    # Export analytics data
    if st.button("📥 Export Analytics Data"):
        
        # Prepare comprehensive analytics export
        export_data = {
            'daily_aggregates': daily_aggregates.to_dict('records'),
            'latest_organization_data': latest_data.to_dict('records'),
            'group_analysis': group_analysis.to_dict('records'),
            'correlation_matrix': correlation_data.to_dict(),
        }
        
        if 'growth_df' in locals():
            export_data['growth_analysis'] = growth_df.to_dict('records')
        
        import json
        json_str = json.dumps(export_data, indent=2, default=str)
        
        st.download_button(
            label="💾 Download Analytics JSON",
            data=json_str,
            file_name=f"dutch_research_analytics_{datetime.now().strftime('%Y%m%d')}.json",
            mime="application/json"
        )
