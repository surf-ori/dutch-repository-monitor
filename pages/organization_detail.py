
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

def show_page(data_manager, api_client):
    """Show detailed organization information"""
    
    st.header("🏛️ Organization Details")
    
    # Load organizations data
    if data_manager.organizations_df.empty:
        st.error("No organizations data available")
        return
    
    # Organization selector
    org_options = {}
    for idx, org in data_manager.organizations_df.iterrows():
        display_name = f"{org['acronym_EN']} - {org['full_name_in_English']}"
        org_options[display_name] = org
    
    selected_org_name = st.selectbox(
        "Select Organization",
        options=list(org_options.keys())
    )
    
    if not selected_org_name:
        return
    
    selected_org = org_options[selected_org_name]
    
    # Get organization data
    ror_link = selected_org['ROR_LINK']
    org_id = api_client.get_organization_id(ror_link)
    
    if not org_id:
        st.error("Could not retrieve OpenAIRE organization ID")
        return
    
    # Display organization info
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader(f"📋 {selected_org['full_name_in_English']}")
        st.write(f"**Acronym:** {selected_org['acronym_EN']}")
        st.write(f"**Group:** {selected_org['main_grouping']}")
        st.write(f"**ROR ID:** {selected_org['ROR']}")
        st.write(f"**OpenAIRE ID:** {org_id}")
    
    with col2:
        # Get current stats
        with st.spinner("Loading current statistics..."):
            current_stats = api_client.get_organization_stats(org_id)
            
            if current_stats:
                # Status indicator
                health = current_stats.get('repository_health', 'unknown')
                if health == 'healthy':
                    st.success("🟢 Repository Healthy")
                elif health == 'warning':
                    st.warning("🟡 Repository Warning")
                elif health == 'critical':
                    st.error("🔴 Repository Critical")
                else:
                    st.info("⚪ Repository Status Unknown")
                
                # Key metrics
                st.metric("Total Publications", current_stats.get('publications_total', 0))
                st.metric("Recent Publications", current_stats.get('publications_recent', 0))
                st.metric("Data Sources", current_stats.get('data_sources_count', 0))
                
                freshness_days = current_stats.get('data_freshness_days')
                if freshness_days is not None:
                    st.metric("Days Since Last Publication", freshness_days)
    
    # Historical trends
    st.subheader("📈 Historical Trends")
    
    # Get historical data for this organization
    historical_data = data_manager.get_historical_data(90)  # Last 90 days
    
    if not historical_data.empty:
        org_historical = historical_data[historical_data['org_id'] == org_id]
        
        if not org_historical.empty:
            # Sort by date
            org_historical = org_historical.sort_values('date')
            org_historical['date'] = pd.to_datetime(org_historical['date'])
            
            # Create trend charts
            col1, col2 = st.columns(2)
            
            with col1:
                # Publications trend
                fig_pubs = go.Figure()
                
                fig_pubs.add_trace(go.Scatter(
                    x=org_historical['date'],
                    y=org_historical['publications_total'],
                    mode='lines+markers',
                    name='Total Publications',
                    line=dict(color='#1f77b4', width=3)
                ))
                
                fig_pubs.add_trace(go.Scatter(
                    x=org_historical['date'],
                    y=org_historical['publications_recent'],
                    mode='lines+markers',
                    name='Recent Publications',
                    line=dict(color='#ff7f0e', width=2)
                ))
                
                fig_pubs.update_layout(
                    title="Publications Over Time",
                    xaxis_title="Date",
                    yaxis_title="Number of Publications",
                    hovermode='x unified'
                )
                
                st.plotly_chart(fig_pubs, use_container_width=True)
            
            with col2:
                # Data freshness trend
                fig_fresh = px.line(
                    org_historical,
                    x='date',
                    y='data_freshness_days',
                    title="Data Freshness Over Time",
                    labels={'data_freshness_days': 'Days Since Last Publication'},
                    color_discrete_sequence=['#17becf']
                )
                
                # Add threshold lines
                fig_fresh.add_hline(y=7, line_dash="dash", line_color="green", 
                                  annotation_text="Healthy threshold")
                fig_fresh.add_hline(y=30, line_dash="dash", line_color="orange", 
                                  annotation_text="Warning threshold")
                
                st.plotly_chart(fig_fresh, use_container_width=True)
            
            # Repository health over time
            st.subheader("🏥 Repository Health Over Time")
            
            health_mapping = {'healthy': 3, 'warning': 2, 'critical': 1, 'unknown': 0}
            org_historical['health_numeric'] = org_historical['repository_health'].map(health_mapping)
            
            fig_health = px.scatter(
                org_historical,
                x='date',
                y='health_numeric',
                color='repository_health',
                color_discrete_map={'healthy': '#28a745', 'warning': '#ffc107', 'critical': '#dc3545', 'unknown': '#6c757d'},
                title="Repository Health Status Over Time",
                labels={'health_numeric': 'Health Status'}
            )
            
            fig_health.update_layout(
                yaxis=dict(
                    tickmode='array',
                    tickvals=[0, 1, 2, 3],
                    ticktext=['Unknown', 'Critical', 'Warning', 'Healthy']
                )
            )
            
            st.plotly_chart(fig_health, use_container_width=True)
            
        else:
            st.info("No historical data available for this organization")
    else:
        st.info("No historical data available")
    
    # Data sources section
    st.subheader("💾 Data Sources")
    
    with st.spinner("Loading data sources..."):
        data_sources = api_client.get_data_sources(org_id)
        
        if data_sources and 'results' in data_sources:
            sources_list = data_sources['results']
            
            if sources_list:
                # Create data sources dataframe
                sources_data = []
                for source in sources_list:
                    sources_data.append({
                        'Name': source.get('officialname', 'Unknown'),
                        'Type': source.get('datasourcetype', {}).get('classname', 'Unknown'),
                        'Content Types': ', '.join([ct.get('classname', '') for ct in source.get('contenttypes', [])]),
                        'URL': source.get('websiteurl', ''),
                        'Status': source.get('status', 'Unknown')
                    })
                
                sources_df = pd.DataFrame(sources_data)
                st.dataframe(sources_df, use_container_width=True, hide_index=True)
                
                # Data source types chart
                if not sources_df.empty:
                    type_counts = sources_df['Type'].value_counts()
                    fig_types = px.pie(
                        values=type_counts.values,
                        names=type_counts.index,
                        title="Data Source Types Distribution"
                    )
                    st.plotly_chart(fig_types, use_container_width=True)
            else:
                st.info("No data sources found for this organization")
        else:
            st.warning("Could not retrieve data sources information")
    
    # Recent publications section
    st.subheader("📚 Recent Publications")
    
    with st.spinner("Loading recent publications..."):
        publications = api_client.get_organization_publications(org_id)
        
        if publications and 'results' in publications:
            pubs_list = publications['results'][:10]  # Show first 10
            
            if pubs_list:
                pubs_data = []
                for pub in pubs_list:
                    pubs_data.append({
                        'Title': pub.get('title', {}).get('value', 'No title')[:100] + '...' if len(pub.get('title', {}).get('value', '')) > 100 else pub.get('title', {}).get('value', 'No title'),
                        'Type': pub.get('resulttype', {}).get('classname', 'Unknown'),
                        'Publication Date': pub.get('dateofacceptance', {}).get('value', 'Unknown')[:10] if pub.get('dateofacceptance', {}).get('value') else 'Unknown',
                        'Collection Date': pub.get('dateofcollection', 'Unknown')[:10] if pub.get('dateofcollection') else 'Unknown'
                    })
                
                pubs_df = pd.DataFrame(pubs_data)
                st.dataframe(pubs_df, use_container_width=True, hide_index=True)
            else:
                st.info("No recent publications found")
        else:
            st.warning("Could not retrieve publications information")
    
    # Export organization data
    if st.button("📥 Export Organization Data"):
        export_data = {
            'organization_info': selected_org.to_dict(),
            'current_stats': current_stats if current_stats else {},
            'historical_data': org_historical.to_dict('records') if not org_historical.empty else []
        }
        
        import json
        json_str = json.dumps(export_data, indent=2, default=str)
        
        st.download_button(
            label="💾 Download JSON",
            data=json_str,
            file_name=f"{selected_org['acronym_EN']}_data_{datetime.now().strftime('%Y%m%d')}.json",
            mime="application/json"
        )
