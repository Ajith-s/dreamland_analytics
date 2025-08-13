import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

# Import all existing functions
from data_loading import load_data, get_customer_summary, get_daily_usage_summary
from stickiness import (
    calculate_action_stickiness, 
    get_weekly_new_users, 
    get_stickiness_insights,
    STICKINESS_THRESHOLDS
)
from visualizations import plot_overview_trends, show_product_metrics
from churn_analysis import calculate_churn_metrics, plot_churn_analysis,calculate_consolidated_churn_metrics,plot_consolidated_churn
from product_transitions import analyze_product_transitions, show_product_transitions
from purchase_funnel import create_funnel_figures
from utils import get_unique_products

def calculate_north_star_kpis(customers_df, usage_df):
    """Calculate North Star KPIs with enhanced stickiness metrics"""
    customer_summary = get_customer_summary(customers_df)
    daily_usage = get_daily_usage_summary(usage_df)
    
    # Calculate enhanced action-based stickiness
    stickiness_metrics, top_sticky_actions, product_stickiness, segments_df = calculate_action_stickiness(usage_df)
    
    # Calculate product transitions
    transition_data = analyze_product_transitions(usage_df)
    
    # Calculate weekly cancellations
    customer_summary['cancel_week'] = customer_summary['cancel_date'].dt.to_period('W')
    weekly_cancellations = (
        customer_summary[customer_summary['cancel_date'].notna()]
        .groupby(['cancel_week', 'first_signedup_product'])
        .agg({
            'customerid': 'nunique'  # Count unique cancelled users
        })
        .reset_index()
        .rename(columns={
            'first_signedup_product': 'product_name',
            'customerid': 'cancelled_users'
        })
    )
    weekly_cancellations['week'] = weekly_cancellations['cancel_week'].dt.start_time
    
    # Calculate weekly cross-product usage
    daily_usage['week'] = daily_usage['event_date'].dt.to_period('W')
    
    # For each week and product, find users who also used other products
    weekly_cross_product = []
    
    for week in sorted(daily_usage['week'].unique()):
        week_usage = daily_usage[daily_usage['week'] == week]
        
        # For each product
        for product in week_usage['product_name'].unique():
            # Get users of this product this week
            product_users = set(week_usage[
                week_usage['product_name'] == product
            ]['customerid'])
            
            if product_users:
                # Get users who used other products this week
                other_product_users = set(week_usage[
                    week_usage['product_name'] != product
                ]['customerid'])
                
                # Find intersection
                cross_product_users = product_users.intersection(other_product_users)
                
                weekly_cross_product.append({
                    'week': week,
                    'product_name': product,
                    'total_users': len(product_users),
                    'cross_product_users': len(cross_product_users),
                    'cross_product_rate': len(cross_product_users) / len(product_users)
                })
    
    cross_product_usage = pd.DataFrame(weekly_cross_product)
    cross_product_usage['week'] = cross_product_usage['week'].dt.start_time
    
    # Calculate cancellation rate
    total_users_by_product = customer_summary.groupby('first_signedup_product')['customerid'].nunique()
    weekly_cancellations['total_users'] = weekly_cancellations['product_name'].map(total_users_by_product)
    weekly_cancellations['cancellation_rate'] = (
        weekly_cancellations['cancelled_users'] / weekly_cancellations['total_users']
    )
    
    kpis = {}
    
    # 1. Core User Metrics
    # Calculate total unique customers across both datasets
    total_unique_customers = len(
        set(customer_summary['customerid']).union(set(daily_usage['customerid']))
    )
    
    kpis['total_unique_customers'] = total_unique_customers
    kpis['active_users_current'] = daily_usage['customerid'].nunique()
    kpis['cross_product_users'] = customer_summary['is_cross_product'].sum()
    kpis['cross_product_rate'] = customer_summary['is_cross_product'].mean()
    
    # Add multi-product metrics from transition analysis
    multi_product_users = transition_data['products_per_customer'][
        transition_data['products_per_customer']['num_products'] > 1
    ]['num_customers'].sum()
    
    kpis['multi_product_users'] = multi_product_users
    kpis['avg_products_per_user'] = (
        transition_data['products_per_customer']['num_products'] * 
        transition_data['products_per_customer']['num_customers']
    ).sum() / transition_data['total_customers']
    
    # Add weekly cross-product usage
    kpis['cross_product_usage'] = cross_product_usage
    
    # 2. Growth Metrics
    if len(daily_usage) > 0:
        current_month = daily_usage['event_date'].max().to_period('M')
        prev_month = current_month - 1
        
        current_month_active = daily_usage[
            daily_usage['event_date'].dt.to_period('M') == current_month
        ]['customerid'].nunique()
        
        prev_month_active = daily_usage[
            daily_usage['event_date'].dt.to_period('M') == prev_month
        ]['customerid'].nunique()
        
        if prev_month_active > 0:
            kpis['mom_active_user_growth'] = (current_month_active - prev_month_active) / prev_month_active
        else:
            kpis['mom_active_user_growth'] = 0
    else:
        kpis['mom_active_user_growth'] = 0
    
    # 3. Engagement Quality
    user_engagement = daily_usage.groupby('customerid').agg({
        'event_date': 'nunique',  # Active days
        'total_usage': 'sum',     # Total usage across all days
        'actions_taken': 'mean'   # Average actions per day
    }).reset_index()
    
    kpis['avg_active_days_per_user'] = user_engagement['event_date'].mean()
    kpis['avg_usage_per_active_user'] = user_engagement['total_usage'].mean()
    kpis['avg_actions_per_day'] = user_engagement['actions_taken'].mean()
    
    # 4. Enhanced Stickiness Metrics
    kpis['stickiness_metrics'] = stickiness_metrics
    kpis['top_sticky_actions'] = top_sticky_actions
    kpis['product_stickiness'] = product_stickiness
    kpis['segments_df'] = segments_df
    
    # 5. Product Transition Metrics
    kpis['transition_data'] = transition_data
    
    # 6. Weekly Cancellation Metrics
    kpis['weekly_cancellations'] = weekly_cancellations

        # Add consolidated churn metrics
    overall_churn, weekly_churn = calculate_consolidated_churn_metrics(daily_usage)
    kpis['overall_churn'] = overall_churn
    kpis['weekly_churn'] = weekly_churn
    
    return kpis, customer_summary, daily_usage

def show_stickiness_config(usage_df):
    """Display and handle stickiness configuration in sidebar"""
    st.sidebar.header("Stickiness Configuration")
    
    # Show current thresholds
    st.sidebar.subheader("Day Thresholds by Product")
    for product, threshold in STICKINESS_THRESHOLDS.items():
        st.sidebar.text(f"{product}: {threshold} days")
    
    # Action percentile threshold
    action_percentile = st.sidebar.slider(
        "Action Count Percentile Threshold",
        min_value=50,
        max_value=90,
        value=70,
        step=5,
        help="Percentile threshold for action counts to determine power users"
    )
    
    return action_percentile

def show_segment_analysis(segments_df, usage_df):
    """Display detailed segment analysis"""
    st.header("👥 User Segment Analysis")
    
    # Get insights
    insights_df = get_stickiness_insights(segments_df)
    
    # Show overall segment distribution
    products = sorted(segments_df['product_name'].unique())
    
    for product in products:
        st.subheader(f"{product} Segment Analysis")
        
        product_insights = insights_df[insights_df['product'] == product].iloc[0]
        
        # Create columns for metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Power Users",
                f"{product_insights['power_users_pct']:.1%}",
                help="Users meeting both day and action thresholds"
            )
        
        with col2:
            st.metric(
                "Frequent Light Users",
                f"{product_insights['frequent_light_pct']:.1%}",
                help="Users meeting day threshold but not action threshold"
            )
        
        with col3:
            st.metric(
                "Intensive Irregular Users",
                f"{product_insights['intensive_irregular_pct']:.1%}",
                help="Users meeting action threshold but not day threshold"
            )
        
        # Show opportunity insight
        st.info(f"💡 **Growth Opportunity**: {product_insights['opportunity']}")
        
        # Show segment trends
        product_segments = segments_df[segments_df['product_name'] == product]
        
        fig = go.Figure()
        
        # Add traces for each segment
        fig.add_trace(
            go.Bar(
                name="Power Users",
                x=product_segments['action_type_id'],
                y=product_segments['power_users_pct'],
                text=[f"{x:.1%}" for x in product_segments['power_users_pct']],
                textposition='auto',
            )
        )
        
        fig.add_trace(
            go.Bar(
                name="Frequent Light",
                x=product_segments['action_type_id'],
                y=product_segments['frequent_light_pct'],
                text=[f"{x:.1%}" for x in product_segments['frequent_light_pct']],
                textposition='auto',
            )
        )
        
        fig.add_trace(
            go.Bar(
                name="Intensive Irregular",
                x=product_segments['action_type_id'],
                y=product_segments['intensive_irregular_pct'],
                text=[f"{x:.1%}" for x in product_segments['intensive_irregular_pct']],
                textposition='auto',
            )
        )
        
        fig.update_layout(
            barmode='stack',
            title=f"User Segments by Action - {product}",
            xaxis_title="Action ID",
            yaxis_title="Percentage of Users",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)

def main():
    # Page config
    st.set_page_config(
        page_title="Dreamland Active User Growth Analytics",
        page_icon="🚀",
        layout="wide"
    )
    
    # Load data
    usage_df, customers_df = load_data()

    if usage_df is not None and customers_df is not None:
        st.title("🚀 Dreamland Active User Growth Analytics")
        
        # Date range filter in sidebar
        st.sidebar.header("Date Range Filter")
        
        if not usage_df.empty:
            min_date = usage_df['event_date'].min().date()
            max_date = usage_df['event_date'].max().date()
            
            date_range = st.sidebar.date_input(
                "Select Date Range",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date
            )
            
            if len(date_range) == 2:
                start_date, end_date = date_range
                usage_df = usage_df[
                    (usage_df['event_date'] >= pd.to_datetime(start_date)) & 
                    (usage_df['event_date'] <= pd.to_datetime(end_date))
                ]
        
        # Calculate metrics
        north_star_kpis, customer_summary, daily_usage = calculate_north_star_kpis(customers_df, usage_df)
        
        # NORTH STAR METRICS DASHBOARD
        st.header("🎯 North Star Metrics")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric(
                "Total Unique Customers",
                f"{north_star_kpis['total_unique_customers']:,}",
                help="Total number of unique customers across both customer and usage data"
            )
        
        with col2:
            st.metric(
                "Current Active Users",
                f"{north_star_kpis['active_users_current']:,}",
                help="Number of unique users who have performed at least one action in the current period"
            )
        
        with col3:
            mom_growth = north_star_kpis['mom_active_user_growth']
            st.metric(
                "MoM Active User Growth",
                f"{mom_growth:.1%}",
                help="Percentage change in active users compared to previous month"
            )
        
        with col4:
            st.metric(
                "Multi-Product Users",
                f"{north_star_kpis['multi_product_users']:,}",
                f"{north_star_kpis['multi_product_users']/north_star_kpis['total_unique_customers']:.1%} of total",
                help="Users who have performed actions in multiple Dreamland products"
            )
        
        with col5:
            st.metric(
                "Avg Products/User",
                f"{north_star_kpis['avg_products_per_user']:.2f}",
                help="Average number of products used per customer based on actual usage"
            )
        
        # Import channel analytics
        from channel_analytics import show_channel_analytics
        from cohort_analysis import show_cohort_analysis
        
        # Create tabs
        tab_names = [
            "Overview",
            "Product Details",
            "Channel Analysis", 
            "Product Transitions",
            "User Segments",
            "Cohort Analysis"
        ]
        (overview_tab, product_tab, channel_tab, transitions_tab, 
         segments_tab, cohort_tab) = st.tabs(tab_names)
        
        with overview_tab:
        
            # Prepare weekly metrics
            customer_summary['signup_week'] = customer_summary['signup_date'].dt.to_period('W')
            weekly_customer_metrics = customer_summary.groupby(['signup_week', 'first_signedup_product']).agg({
                'customerid': 'count',
                'is_cross_product': 'sum'
            }).reset_index()
            weekly_customer_metrics['cross_product_rate'] = (
                weekly_customer_metrics['is_cross_product'] / weekly_customer_metrics['customerid']
            )
            weekly_customer_metrics['signup_week'] = weekly_customer_metrics['signup_week'].dt.start_time
            
            # Calculate weekly new users
            weekly_new_users = get_weekly_new_users(daily_usage)
            
            # Weekly active users
            weekly_active_users = pd.DataFrame()
            if not daily_usage.empty:
                daily_usage['week'] = daily_usage['event_date'].dt.to_period('W')
                weekly_active_users = daily_usage.groupby(['week', 'product_name'])['customerid'].nunique().reset_index()
                weekly_active_users.columns = ['week', 'product_name', 'active_users']
                weekly_active_users['week'] = weekly_active_users['week'].dt.start_time

            # Calculate weekly purchases
            customer_summary['purchase_week'] = customer_summary['first_purchase_date'].dt.to_period('W')
            weekly_purchases = customer_summary.groupby(['purchase_week', 'first_signedup_product']).agg({
                'customerid': 'nunique'  # Count unique purchasing customers
            }).reset_index()
            weekly_purchases.columns = ['week', 'product_name', 'purchased_users']
            weekly_purchases['week'] = weekly_purchases['week'].dt.start_time
            
            # Show overview trends
            st.header("📈 Growth Metrics Trends")
            st.caption("Weekly trends showing key growth and engagement metrics across products")
            
            overview_fig = plot_overview_trends(
                weekly_customer_metrics,
                weekly_new_users,
                weekly_active_users,
                north_star_kpis['weekly_cancellations'],
                north_star_kpis['cross_product_usage'],
                weekly_purchases
            )
            st.plotly_chart(overview_fig, use_container_width=True)
            
            # Add Purchase Funnel Analysis
            st.header("🛒 Paid User Activation Funnel")
            st.caption("Analysis of customer journey from activation to purchase")
            
            # Create two columns for the funnels
            col1, col2 = st.columns(2)
            
            # Get funnel figures
            overall_fig, product_fig = create_funnel_figures()
            
            with col1:
                st.plotly_chart(overall_fig, use_container_width=True)
            
            with col2:
                st.plotly_chart(product_fig, use_container_width=True)

                # Add consolidated churn metrics
            st.header("🔄 Overall Customer Churn Rates")
            
            churn_col1, churn_col2, churn_col3 = st.columns(3)
            
            with churn_col1:
                st.metric(
                    "Overall Churn Rate",
                    f"{north_star_kpis['overall_churn']['churn_rate']:.1%}",
                    help="Percentage of users inactive for 21+ days across all products"
                )
            
            with churn_col2:
                st.metric(
                    "Total Churned Users",
                    f"{north_star_kpis['overall_churn']['churned_users']:,}",
                    help="Number of users inactive for 21+ days"
                )
            
            with churn_col3:
                st.metric(
                    "Avg Days Since Last Activity",
                    f"{north_star_kpis['overall_churn']['avg_days_since_last']:.1f}",
                    help="Average number of days since users' last activity"
                )
            
            # Show consolidated churn visualization
            churn_fig = plot_consolidated_churn(north_star_kpis['weekly_churn'])
            st.plotly_chart(churn_fig, use_container_width=True)
        
        # Channel Analysis Tab
        with channel_tab:
            show_channel_analytics(customer_summary)
        
        # Product Transitions Tab
        with transitions_tab:
            show_product_transitions(north_star_kpis['transition_data'])

        # User Segments Tab
        with segments_tab:
            st.header("🎯 User Segmentation Analysis")
            st.caption("""
            Users are segmented based on their activity patterns:
            - Frequency: Days active per week
            - Intensity: Actions per week
            - Variety: Number of different actions used
            - Volume: Total number of actions
            """)
            
            # Get unique products for selector
            products = sorted([p for p in usage_df['product_name'].unique() if pd.notna(p)])
            selected_product = st.selectbox(
                "Select Product",
                products,
                key="user_segments_tab_product_selector"
            )
            
            if selected_product:
                # Import user segmentation
                from user_segmentation import (
                    prepare_user_metrics,
                    cluster_users,
                    create_segment_visualizations,
                    get_segment_summary
                )
                
                # Prepare data and perform clustering
                user_metrics, total_weeks = prepare_user_metrics(usage_df, selected_product)
                user_segments = cluster_users(user_metrics)
                
                # Create visualizations
                fig_overview, fig_segments, fig_action_segments = create_segment_visualizations(
                    usage_df, user_segments, selected_product
                )
                
                # Show visualizations
                st.plotly_chart(fig_overview, use_container_width=True)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.plotly_chart(fig_segments, use_container_width=True)
                with col2:
                    # Show segment summary
                    st.subheader("📊 Segment Metrics")
                    summary = get_segment_summary(user_segments)
                    st.dataframe(summary)
                
                # Show action usage by segment
                st.plotly_chart(fig_action_segments, use_container_width=True)

        # Product Details Tab
        with product_tab:
            # Get unique products
            products = sorted(set(
                list(weekly_customer_metrics['first_signedup_product'].unique()) + 
                list(weekly_active_users['product_name'].unique())
            ))
            products = [p for p in products if pd.notna(p)]
            
            # Create product selector
            selected_product = st.selectbox(
                "Select Product",
                products,
                key="product_details_selector"  # Added unique key
            )
            
            if selected_product:
                # Calculate user engagement for selected product with proper columns
                user_engagement = (
                    daily_usage
                    .groupby(['customerid', 'product_name'])
                    .agg({
                        'event_date': lambda x: x.nunique(),  # Count unique days
                        'total_usage': 'sum',
                        'actions_taken': 'mean'
                    })
                    .reset_index()
                    .rename(columns={'event_date': 'active_days'})  # Rename to match expected column
                )
                
                # Filter for selected product
                user_engagement = user_engagement[user_engagement['product_name'] == selected_product]
                
                # Show product metrics
                show_product_metrics(
                    selected_product,
                    weekly_customer_metrics,
                    weekly_new_users,
                    weekly_active_users,
                    north_star_kpis['weekly_cancellations'],
                    daily_usage,
                    user_engagement,
                    weekly_purchases
                )
        
        # Cohort Analysis Tab
        with cohort_tab:
            # Get unique products using utility function
            products = get_unique_products(weekly_customer_metrics, weekly_active_users)
            
            # Create product selector
            selected_product = st.selectbox(
                "Select Product for Cohort Analysis",
                products,
                key="cohort_product_selector"
            )
            
            if selected_product:
                show_cohort_analysis(customer_summary, daily_usage, selected_product)

    else:
        st.error("Unable to load data. Please check your CSV files.")

if __name__ == "__main__":
    main()