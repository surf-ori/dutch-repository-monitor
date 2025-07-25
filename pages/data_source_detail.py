
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

def show_page(data_manager, api_client):
    """Show detailed data source information"""
    
    st.header("💾 Data Source Details")
    
    # Load recent data to get organizations with data sources
    recent_data = data_manager.load_daily_data()
    
    if recent_data.empty:
        st.warning("No data available. Please run data collection first.")
        return
    
    # Filter organizations with data sources
    orgs_with_sources = recent_data[recent_data['data_sources_count'] > 0]
    
    if orgs_with_sources.empty:
        st.info("No organizations with data sources found.")
        return
    
    # Organization selector
    org_options = {}
    for idx, org in orgs_with_sources.iterrows():
        display_name = f"{org['acronym']} - {org['organization_name']}"
        org_options[display_name] = org
    
    selected_org_name = st.selectbox(
        "Select Organization",
        options=list(org_options.keys())
    )
    
    if not selected_org_name:
        return
    
    selected_org = org_options[selected_org_name]
    org_id = selected_org['org_id']
    
    # Display organization info
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader(f"📋 {selected_org['organization_name']}")
        st.write(f"**Acronym:** {selected_org['acronym']}")
        st.write(f"**Group:** {selected_org['main_grouping']}")
        st.write(f"**Data Sources Count:** {selected_org['data_sources_count']}")
    
    with col2:
        # Current status
        health = selected_org.get('repository_health', 'unknown')
        if health == 'healthy':
            st.success("🟢 Repository Healthy")
        elif health == 'warning':
            st.warning("🟡 Repository Warning")
        elif health == 'critical':
            st.error("🔴 Repository Critical")
        else:
            st.info("⚪ Repository Status Unknown")
    
    # Load detailed data sources information
    st.subheader("💾 Data Sources Overview")
    
    with st.spinner("Loading data sources..."):
        data_sources = api_client.get_data_sources(org_id)
        
        if data_sources and 'results' in data_sources:
            sources_list = data_sources['results']
            
            if sources_list:
                # Create comprehensive data sources table
                sources_data = []
                for i, source in enumerate(sources_list):
                    # Extract content types
                    content_types = []
                    for ct in source.get('contenttypes', []):
                        content_types.append(ct.get('classname', ''))
                    
                    # Extract subjects
                    subjects = []
                    for subj in source.get('subjects', []):
                        subjects.append(subj.get('classname', ''))
                    
                    sources_data.append({
                        'ID': i + 1,
                        'Name': source.get('officialname', 'Unknown'),
                        'English Name': source.get('englishname', ''),
                        'Type': source.get('datasourcetype', {}).get('classname', 'Unknown'),
                        'Content Types': ', '.join(content_types) if content_types else 'Not specified',
                        'Subjects': ', '.join(subjects[:3]) if subjects else 'Not specified',  # Show first 3 subjects
                        'Website': source.get('websiteurl', ''),
                        'Status': source.get('status', 'Unknown'),
                        'Validated': source.get('validated', 'Unknown'),
                        'Collection Mode': source.get('collectionmode', 'Unknown'),
                        'Master': source.get('master', 'Unknown')
                    })
                
                sources_df = pd.DataFrame(sources_data)
                
                # Display summary metrics
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Total Data Sources", len(sources_df))
                
                with col2:
                    validated_count = len(sources_df[sources_df['Validated'] == 'true'])
                    st.metric("Validated Sources", validated_count)
                
                with col3:
                    unique_types = sources_df['Type'].nunique()
                    st.metric("Unique Source Types", unique_types)
                
                with col4:
                    active_sources = len(sources_df[sources_df['Status'] != 'disabled'])
                    st.metric("Active Sources", active_sources)
                
                # Data source type distribution
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("📊 Data Source Types")
                    type_counts = sources_df['Type'].value_counts()
                    fig_types = px.pie(
                        values=type_counts.values,
                        names=type_counts.index,
                        title="Distribution of Data Source Types"
                    )
                    st.plotly_chart(fig_types, use_container_width=True)
                
                with col2:
                    st.subheader("✅ Validation Status")
                    validation_counts = sources_df['Validated'].value_counts()
                    colors = {'true': '#28a745', 'false': '#dc3545', 'Unknown': '#6c757d'}
                    fig_validation = px.pie(
                        values=validation_counts.values,
                        names=validation_counts.index,
                        title="Validation Status Distribution",
                        color=validation_counts.index,
                        color_discrete_map=colors
                    )
                    st.plotly_chart(fig_validation, use_container_width=True)
                
                # Detailed data sources table
                st.subheader("📋 Detailed Data Sources Information")
                
                # Add filters
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    type_filter = st.selectbox(
                        "Filter by Type",
                        options=['All'] + sorted(sources_df['Type'].unique().tolist())
                    )
                
                with col2:
                    status_filter = st.selectbox(
                        "Filter by Status",
                        options=['All'] + sorted(sources_df['Status'].unique().tolist())
                    )
                
                with col3:
                    validated_filter = st.selectbox(
                        "Filter by Validation",
                        options=['All', 'true', 'false', 'Unknown']
                    )
                
                # Apply filters
                filtered_sources = sources_df.copy()
                
                if type_filter != 'All':
                    filtered_sources = filtered_sources[filtered_sources['Type'] == type_filter]
                
                if status_filter != 'All':
                    filtered_sources = filtered_sources[filtered_sources['Status'] == status_filter]
                
                if validated_filter != 'All':
                    filtered_sources = filtered_sources[filtered_sources['Validated'] == validated_filter]
                
                # Display filtered table
                st.dataframe(
                    filtered_sources,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Website": st.column_config.LinkColumn("Website")
                    }
                )
                
                # Content types analysis
                st.subheader("📑 Content Types Analysis")
                
                # Extract all content types
                all_content_types = []
                for content_types_str in sources_df['Content Types'].dropna():
                    if content_types_str != 'Not specified':
                        types_list = [ct.strip() for ct in content_types_str.split(',')]
                        all_content_types.extend(types_list)
                
                if all_content_types:
                    content_type_counts = pd.Series(all_content_types).value_counts()
                    
                    fig_content = px.bar(
                        x=content_type_counts.values,
                        y=content_type_counts.index,
                        orientation='h',
                        title="Content Types Distribution",
                        labels={'x': 'Number of Sources', 'y': 'Content Type'}
                    )
                    fig_content.update_layout(height=400)
                    st.plotly_chart(fig_content, use_container_width=True)
                
                # Historical data source trends
                st.subheader("📈 Data Source Trends")
                
                historical_data = data_manager.get_historical_data(30)
                if not historical_data.empty:
                    org_historical = historical_data[historical_data['org_id'] == org_id]
                    
                    if not org_historical.empty:
                        org_historical = org_historical.sort_values('date')
                        org_historical['date'] = pd.to_datetime(org_historical['date'])
                        
                        # Data sources count over time
                        fig_trend = px.line(
                            org_historical,
                            x='date',
                            y='data_sources_count',
                            title="Data Sources Count Over Time",
                            labels={'data_sources_count': 'Number of Data Sources'},
                            markers=True
                        )
                        st.plotly_chart(fig_trend, use_container_width=True)
                
                # Export data sources information
                if st.button("📥 Export Data Sources Information"):
                    csv = filtered_sources.to_csv(index=False)
                    st.download_button(
                        label="💾 Download Data Sources CSV",
                        data=csv,
                        file_name=f"{selected_org['acronym']}_data_sources_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
                
            else:
                st.info("No data sources found for this organization.")
        else:
            st.warning("Could not retrieve data sources information.")
    
    # System health indicators for data sources
    st.subheader("🏥 Data Source Health Indicators")
    
    if 'sources_df' in locals() and not sources_df.empty:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Validation health
            validated_pct = (sources_df['Validated'] == 'true').mean() * 100
            if validated_pct >= 80:
                st.success(f"✅ Validation Health: {validated_pct:.1f}% validated")
            elif validated_pct >= 60:
                st.warning(f"⚠️ Validation Health: {validated_pct:.1f}% validated")
            else:
                st.error(f"❌ Validation Health: {validated_pct:.1f}% validated")
        
        with col2:
            # Active sources health
            active_pct = (sources_df['Status'] != 'disabled').mean() * 100
            if active_pct >= 90:
                st.success(f"✅ Active Sources: {active_pct:.1f}%")
            elif active_pct >= 70:
                st.warning(f"⚠️ Active Sources: {active_pct:.1f}%")
            else:
                st.error(f"❌ Active Sources: {active_pct:.1f}%")
        
        with col3:
            # Diversity indicator (number of different types)
            diversity_score = sources_df['Type'].nunique()
            if diversity_score >= 3:
                st.success(f"✅ Source Diversity: {diversity_score} types")
            elif diversity_score >= 2:
                st.warning(f"⚠️ Source Diversity: {diversity_score} types")
            else:
                st.info(f"ℹ️ Source Diversity: {diversity_score} type(s)")
