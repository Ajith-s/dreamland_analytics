import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def calculate_churn_metrics(usage_df, product, churn_threshold_days=21):
    """
    Calculate churn metrics for a specific product based on cohorts.
    
    Args:
        usage_df: DataFrame with columns ['customerid', 'product_name', 'event_date']
        product: str, name of the product to analyze
        churn_threshold_days: int, number of days of inactivity to consider a user churned
    
    Returns:
        DataFrame with cohort metrics including size and churn rate
    """
    # Filter for the specific product
    product_df = usage_df[usage_df['product_name'] == product].copy()
    
    # Get first usage date for each user
    first_usage = (
        product_df
        .groupby('customerid')['event_date']
        .min()
        .reset_index()
    )
    first_usage['cohort_week'] = first_usage['event_date'].dt.to_period('W')
    
    # Get last usage date for each user
    last_usage = (
        product_df
        .groupby('customerid')['event_date']
        .max()
        .reset_index()
    )
    
    # Combine first and last usage
    user_activity = pd.merge(
        first_usage,
        last_usage,
        on='customerid',
        suffixes=('_first', '_last')
    )
    
    # Get the latest date in the dataset
    max_date = usage_df['event_date'].max()
    
    # Calculate days since last activity
    user_activity['days_since_last'] = (max_date - user_activity['event_date_last']).dt.days
    
    # Mark users as churned if inactive for more than threshold days
    user_activity['is_churned'] = user_activity['days_since_last'] >= churn_threshold_days
    
    # Calculate metrics by cohort
    cohort_metrics = (
        user_activity
        .groupby('cohort_week')
        .agg({
            'customerid': 'count',  # cohort size
            'is_churned': 'sum'     # number of churned users
        })
        .reset_index()
    )
    
    # Calculate churn rate
    cohort_metrics['churn_rate'] = cohort_metrics['is_churned'] / cohort_metrics['customerid']
    
    # Convert period to timestamp for plotting
    cohort_metrics['cohort_week'] = cohort_metrics['cohort_week'].dt.start_time
    
    # Rename columns for clarity
    cohort_metrics = cohort_metrics.rename(columns={
        'customerid': 'cohort_size',
        'is_churned': 'churned_users'
    })
    
    return cohort_metrics

def calculate_consolidated_churn_metrics(usage_df, churn_threshold_days=21):
    """
    Calculate consolidated churn metrics across all products at customer level.
    
    Args:
        usage_df: DataFrame with columns ['customerid', 'event_date']
        churn_threshold_days: int, number of days of inactivity to consider a user churned
    
    Returns:
        Tuple containing:
        - overall_metrics: Dict with current consolidated metrics
        - weekly_metrics: DataFrame with weekly consolidated churn trends
    """
    # Get first and last usage dates across all products for each user
    first_usage = (
        usage_df
        .groupby('customerid')['event_date']
        .min()
        .reset_index()
    )
    first_usage['cohort_week'] = first_usage['event_date'].dt.to_period('W')
    
    last_usage = (
        usage_df
        .groupby('customerid')['event_date']
        .max()
        .reset_index()
    )
    
    # Combine first and last usage
    user_activity = pd.merge(
        first_usage,
        last_usage,
        on='customerid',
        suffixes=('_first', '_last')
    )
    
    # Get the latest date in the dataset
    max_date = usage_df['event_date'].max()
    
    # Calculate days since last activity
    user_activity['days_since_last'] = (max_date - user_activity['event_date_last']).dt.days
    
    # Mark users as churned if inactive for more than threshold days
    user_activity['is_churned'] = user_activity['days_since_last'] >= churn_threshold_days
    
    # Calculate overall metrics
    total_users = len(user_activity)
    churned_users = user_activity['is_churned'].sum()
    overall_churn_rate = churned_users / total_users if total_users > 0 else 0
    
    overall_metrics = {
        'total_users': total_users,
        'churned_users': churned_users,
        'churn_rate': overall_churn_rate,
        'avg_days_since_last': user_activity['days_since_last'].mean()
    }
    
    # Calculate weekly metrics
    weekly_metrics = (
        user_activity
        .groupby('cohort_week')
        .agg({
            'customerid': 'count',
            'is_churned': 'sum'
        })
        .reset_index()
    )
    
    weekly_metrics['churn_rate'] = weekly_metrics['is_churned'] / weekly_metrics['customerid']
    weekly_metrics['cohort_week'] = weekly_metrics['cohort_week'].dt.start_time
    
    weekly_metrics = weekly_metrics.rename(columns={
        'customerid': 'cohort_size',
        'is_churned': 'churned_users'
    })
    
    return overall_metrics, weekly_metrics


def plot_churn_analysis(cohort_metrics):
    """
    Create a subplot figure showing cohort size and churn rate.
    
    Args:
        cohort_metrics: DataFrame with columns ['cohort_week', 'cohort_size', 'churned_users', 'churn_rate']
    
    Returns:
        plotly Figure object
    """
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('Cohort Size by First Usage Week', 'Churn Rate by Cohort'),
        vertical_spacing=0.15
    )
    
    # Cohort size plot
    fig.add_trace(
        go.Bar(
            x=cohort_metrics['cohort_week'],
            y=cohort_metrics['cohort_size'],
            name='Cohort Size',
            marker_color='blue'
        ),
        row=1, col=1
    )
    
    # Churn rate plot
    fig.add_trace(
        go.Scatter(
            x=cohort_metrics['cohort_week'],
            y=cohort_metrics['churn_rate'],
            name='Churn Rate',
            mode='lines+markers',
            line=dict(color='red', width=2)
        ),
        row=2, col=1
    )
    
    # Update layout
    fig.update_layout(
        height=600,
        showlegend=True,
        title_text="Cohort Analysis with Churn Metrics"
    )
    
    # Update y-axes
    fig.update_yaxes(title_text="Number of Users", row=1, col=1)
    fig.update_yaxes(title_text="Churn Rate", tickformat='.1%', row=2, col=1)
    
    # Update x-axes
    fig.update_xaxes(title_text="Cohort Week", row=1, col=1)
    fig.update_xaxes(title_text="Cohort Week", row=2, col=1)
    
    return fig

def plot_consolidated_churn(weekly_metrics):
    """
    Create a visualization for consolidated churn metrics across all products.
    
    Args:
        weekly_metrics: DataFrame with columns ['cohort_week', 'cohort_size', 'churned_users', 'churn_rate']
    
    Returns:
        plotly Figure object
    """
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=(
            'Usage and and Churn by Week Across Products',
            'Consolidated Churn Rate Trend'
        ),
        vertical_spacing=0.3
    )
    
    # User counts plot
    fig.add_trace(
        go.Bar(
            x=weekly_metrics['cohort_week'],
            y=weekly_metrics['cohort_size'],
            name='Total Users',
            marker_color='blue'
        ),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Bar(
            x=weekly_metrics['cohort_week'],
            y=weekly_metrics['churned_users'],
            name='Churned Users',
            marker_color='red'
        ),
        row=1, col=1
    )
    
    # Churn rate trend
    fig.add_trace(
        go.Scatter(
            x=weekly_metrics['cohort_week'],
            y=weekly_metrics['churn_rate'],
            name='Churn Rate',
            mode='lines+markers',
            line=dict(color='red', width=2)
        ),
        row=2, col=1
    )
    
    # Update layout
    fig.update_layout(
        height=600,
        showlegend=True,
        title_text="Consolidated Churn Analysis (All Products)",
        barmode='group'
    )
    
    # Update axes
    fig.update_yaxes(title_text="Number of Users", row=1, col=1)
    fig.update_yaxes(title_text="Churn Rate", tickformat='.1%', row=2, col=1)
    fig.update_xaxes(title_text="Cohort Week", row=1, col=1)
    fig.update_xaxes(title_text="Week", row=2, col=1)
    
    return fig