import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def calculate_cohort_metrics(customer_summary, daily_usage, product):
    """Calculate cohort metrics based on first activation week"""
    
    # Filter for the product
    product_customers = customer_summary[
        customer_summary['first_signedup_product'] == product
    ].copy()
    
    # Add activation week
    product_customers['activation_week'] = product_customers['first_activation_date'].dt.to_period('W')
    
    # Get product usage data
    product_usage = daily_usage[daily_usage['product_name'] == product].copy()
    product_usage['week'] = product_usage['event_date'].dt.to_period('W')
    product_usage['month'] = product_usage['event_date'].dt.to_period('M')
    
    # Initialize cohort metrics
    cohorts = []
    
    # Process each activation week cohort
    for week in sorted(product_customers['activation_week'].unique()):
        if pd.isna(week):
            continue
            
        # Get customers in this cohort
        cohort_customers = product_customers[
            product_customers['activation_week'] == week
        ]
        cohort_ids = cohort_customers['customerid'].unique()
        
        # Get usage data for these customers
        cohort_usage = product_usage[
            product_usage['customerid'].isin(cohort_ids)
        ]
        
        # Calculate metrics
        total_customers = len(cohort_ids)
        
        # Actions per time period
        if not cohort_usage.empty:
            # Daily metrics
            daily_actions = cohort_usage.groupby('customerid')['actions_taken'].mean()
            avg_daily_actions = daily_actions.mean()
            
            # Weekly metrics
            weekly_actions = cohort_usage.groupby(['customerid', 'week'])['actions_taken'].sum().groupby('customerid').mean()
            avg_weekly_actions = weekly_actions.mean()
            
            # Monthly metrics
            monthly_actions = cohort_usage.groupby(['customerid', 'month'])['actions_taken'].sum().groupby('customerid').mean()
            avg_monthly_actions = monthly_actions.mean()
            
            # Active days
            weekly_active_days = cohort_usage.groupby(['customerid', 'week'])['event_date'].nunique().groupby('customerid').mean()
            avg_weekly_active_days = weekly_active_days.mean()
            
            monthly_active_days = cohort_usage.groupby(['customerid', 'month'])['event_date'].nunique().groupby('customerid').mean()
            avg_monthly_active_days = monthly_active_days.mean()
        else:
            avg_daily_actions = 0
            avg_weekly_actions = 0
            avg_monthly_actions = 0
            avg_weekly_active_days = 0
            avg_monthly_active_days = 0
        
        # Cancellation metrics
        cancelled_users = cohort_customers['cancel_date'].notna().sum()
        
        # Time to cancellation (excluding negative days)
        time_to_cancel = (
            cohort_customers[
                (cohort_customers['cancel_date'].notna()) &
                (cohort_customers['cancel_date'] > cohort_customers['first_activation_date'])
            ]['cancel_date'] - 
            cohort_customers[
                (cohort_customers['cancel_date'].notna()) &
                (cohort_customers['cancel_date'] > cohort_customers['first_activation_date'])
            ]['first_activation_date']
        ).dt.total_seconds() / (24 * 60 * 60)  # Convert to days
        
        median_time_to_cancel = time_to_cancel.median() if not time_to_cancel.empty else None
        avg_time_to_cancel = time_to_cancel.mean() if not time_to_cancel.empty else None
        
        # Multi-product usage
        multi_product_users = cohort_customers['is_cross_product'].sum()
        
        # Create cohort record
        cohort_metrics = {
            'activation_week': week.start_time,
            'cohort_size': total_customers,
            'avg_daily_actions': avg_daily_actions,
            'avg_weekly_actions': avg_weekly_actions,
            'avg_monthly_actions': avg_monthly_actions,
            'avg_weekly_active_days': avg_weekly_active_days,
            'avg_monthly_active_days': avg_monthly_active_days,
            'cancelled_users': cancelled_users,
            'cancellation_rate': cancelled_users / total_customers,
            'median_days_to_cancel': median_time_to_cancel,
            'avg_days_to_cancel': avg_time_to_cancel,
            'multi_product_users': multi_product_users,
            'multi_product_rate': multi_product_users / total_customers
        }
        
        cohorts.append(cohort_metrics)
    
    return pd.DataFrame(cohorts)

def show_cohort_analysis(customer_summary, daily_usage, product):
    """Display cohort analysis for a product"""
    st.header(f"👥 Cohort Analysis - {product}")
    st.caption("Analysis based on first activation week cohorts")
    
    # Calculate cohort metrics
    cohort_df = calculate_cohort_metrics(customer_summary, daily_usage, product)
    
    if cohort_df.empty:
        st.warning("No cohort data available for this product")
        return
    
    # Overview metrics
    st.subheader("Cohort Overview")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        total_cohorts = len(cohort_df)
        avg_cohort_size = cohort_df['cohort_size'].mean()
        st.metric("Number of Cohorts", f"{total_cohorts}")
        st.metric("Avg Cohort Size", f"{avg_cohort_size:.1f}")
    
    with col2:
        overall_cancel_rate = (
            cohort_df['cancelled_users'].sum() / 
            cohort_df['cohort_size'].sum()
        )
        st.metric("Overall Cancel Rate", f"{overall_cancel_rate:.1%}")
        avg_time_to_cancel = cohort_df['median_days_to_cancel'].mean()
        st.metric("Avg Days to Cancel", f"{avg_time_to_cancel:.1f}")
    
    with col3:
        overall_multi_product = (
            cohort_df['multi_product_users'].sum() / 
            cohort_df['cohort_size'].sum()
        )
        st.metric("Multi-product Rate", f"{overall_multi_product:.1%}")
    
    # Cohort size trend
    st.subheader("Cohort Metrics Over Time")
    
    # Create tabs for different metric views
    size_tab, actions_tab, active_tab, cancel_tab = st.tabs([
        "Cohort Size", "Actions", "Active Days", "Cancellation"
    ])
    
    with size_tab:
        fig = px.line(
            cohort_df,
            x='activation_week',
            y='cohort_size',
            title='Cohort Size by Activation Week'
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Show multi-product adoption
        fig = px.bar(
            cohort_df,
            x='activation_week',
            y=['cohort_size', 'multi_product_users'],
            title='Multi-product Usage by Cohort',
            barmode='overlay'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with actions_tab:
        # Actions per time period
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=cohort_df['activation_week'],
            y=cohort_df['avg_daily_actions'],
            name='Daily',
            mode='lines+markers'
        ))
        fig.add_trace(go.Scatter(
            x=cohort_df['activation_week'],
            y=cohort_df['avg_weekly_actions'],
            name='Weekly',
            mode='lines+markers'
        ))
        fig.add_trace(go.Scatter(
            x=cohort_df['activation_week'],
            y=cohort_df['avg_monthly_actions'],
            name='Monthly',
            mode='lines+markers'
        ))
        fig.update_layout(
            title='Average Actions by Time Period',
            xaxis_title='Activation Week',
            yaxis_title='Average Actions'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with active_tab:
        # Active days
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=cohort_df['activation_week'],
            y=cohort_df['avg_weekly_active_days'],
            name='Weekly',
            mode='lines+markers'
        ))
        fig.add_trace(go.Scatter(
            x=cohort_df['activation_week'],
            y=cohort_df['avg_monthly_active_days'],
            name='Monthly',
            mode='lines+markers'
        ))
        fig.update_layout(
            title='Average Active Days by Time Period',
            xaxis_title='Activation Week',
            yaxis_title='Average Active Days'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with cancel_tab:
        # Cancellation metrics
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=(
                'Cancellation Rate by Cohort',
                'Time to Cancel Distribution'
            )
        )
        
        fig.add_trace(
            go.Scatter(
                x=cohort_df['activation_week'],
                y=cohort_df['cancellation_rate'],
                mode='lines+markers',
                name='Cancel Rate'
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=cohort_df['activation_week'],
                y=cohort_df['median_days_to_cancel'],
                mode='lines+markers',
                name='Median Days'
            ),
            row=2, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=cohort_df['activation_week'],
                y=cohort_df['avg_days_to_cancel'],
                mode='lines+markers',
                name='Average Days'
            ),
            row=2, col=1
        )
        
        fig.update_layout(height=800)
        st.plotly_chart(fig, use_container_width=True)
    
    # Show raw data
    st.subheader("Detailed Cohort Data")
    st.dataframe(
        cohort_df.style.format({
            'cohort_size': '{:,.0f}',
            'avg_daily_actions': '{:.1f}',
            'avg_weekly_actions': '{:.1f}',
            'avg_monthly_actions': '{:.1f}',
            'avg_weekly_active_days': '{:.1f}',
            'avg_monthly_active_days': '{:.1f}',
            'cancelled_users': '{:,.0f}',
            'cancellation_rate': '{:.1%}',
            'median_days_to_cancel': '{:.1f}',
            'avg_days_to_cancel': '{:.1f}',
            'multi_product_users': '{:,.0f}',
            'multi_product_rate': '{:.1%}'
        })
    )