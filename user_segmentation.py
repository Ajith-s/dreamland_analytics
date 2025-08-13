import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def prepare_user_metrics(usage_df, product):
    """Prepare user metrics for clustering analysis."""
    # Filter for product and remove any NaN values
    product_df = usage_df[
        (usage_df['product_name'] == product) & 
        (usage_df['product_name'].notna())
    ].copy()
    
    if product_df.empty:
        raise ValueError(f"No valid data found for product: {product}")
    
    # Get date range for the product
    product_df['week'] = product_df['event_date'].dt.to_period('W')
    total_weeks = product_df['week'].nunique()
    
    # Calculate user metrics
    user_metrics = (
        product_df
        .groupby('customerid')
        .agg({
            'event_date': 'nunique',  # days active
            'week': 'nunique',        # weeks active
            'action_type_id': 'nunique',  # different actions used
            'usage_count': 'sum'      # total actions
        })
        .reset_index()
        .rename(columns={
            'event_date': 'days_active',
            'week': 'weeks_active',
            'action_type_id': 'action_variety',
            'usage_count': 'total_actions'
        })
    )
    
    # Calculate derived metrics
    user_metrics['days_per_week'] = user_metrics['days_active'] / user_metrics['weeks_active']
    user_metrics['actions_per_week'] = user_metrics['total_actions'] / user_metrics['weeks_active']
    
    return user_metrics, total_weeks

def cluster_users(user_metrics, n_clusters=3):
    """Cluster users based on their activity patterns."""
    # Features for clustering
    features = [
        'days_per_week',    # Frequency of use
        'actions_per_week', # Intensity of use
        'action_variety',   # Variety of actions
        'total_actions'     # Overall volume
    ]
    
    X = user_metrics[features].copy()
    
    # Handle any NaN values
    X = X.fillna(X.mean())
    
    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Perform clustering
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    user_metrics['cluster'] = kmeans.fit_predict(X_scaled)
    
    # Label clusters based on activity level
    cluster_centers = pd.DataFrame(
        scaler.inverse_transform(kmeans.cluster_centers_),
        columns=features
    )
    
    # Sort clusters by overall activity
    activity_score = (
        cluster_centers['days_per_week'] * 
        cluster_centers['actions_per_week']
    )
    
    cluster_map = dict(
        zip(
            activity_score.argsort(),
            ['Infrequent Users', 'Regular Users', 'Power Users']
        )
    )
    
    user_metrics['segment'] = user_metrics['cluster'].map(cluster_map)
    
    return user_metrics

def create_segment_visualizations(usage_df, user_segments, product):
    """Create clear visualizations for user segments."""
    # 1. Action Overview - Users and Usage
    action_metrics = (
        usage_df[usage_df['product_name'] == product]
        .groupby('action_type_id')
        .agg({
            'customerid': 'nunique',
            'usage_count': 'sum'
        })
        .reset_index()
        .rename(columns={
            'customerid': 'unique_users',
            'usage_count': 'total_actions'
        })
    )
    
    fig_overview = make_subplots(
        rows=1, cols=2,
        subplot_titles=('Users per Action', 'Total Actions per Action Type'),
        horizontal_spacing=0.1
    )
    
    # Users per action
    fig_overview.add_trace(
        go.Bar(
            x=action_metrics['action_type_id'],
            y=action_metrics['unique_users'],
            name='Unique Users',
            text=action_metrics['unique_users'],
            textposition='auto'
        ),
        row=1, col=1
    )
    
    # Actions per type
    fig_overview.add_trace(
        go.Bar(
            x=action_metrics['action_type_id'],
            y=action_metrics['total_actions'],
            name='Total Actions',
            text=action_metrics['total_actions'],
            textposition='auto'
        ),
        row=1, col=2
    )
    
    fig_overview.update_layout(
        height=400,
        showlegend=False,
        title_text="Action Usage Overview"
    )
    
    fig_overview.update_xaxes(title_text="Action ID", row=1, col=1)
    fig_overview.update_xaxes(title_text="Action ID", row=1, col=2)
    fig_overview.update_yaxes(title_text="Number of Users", row=1, col=1)
    fig_overview.update_yaxes(title_text="Total Actions", row=1, col=2)
    
    # 2. Segment Distribution
    segment_dist = user_segments['segment'].value_counts()
    
    fig_segments = go.Figure(data=[
        go.Pie(
            labels=segment_dist.index,
            values=segment_dist.values,
            hole=0.4,
            text=segment_dist.values,
            textinfo='label+value'
        )
    ])
    
    fig_segments.update_layout(
        title_text="User Segment Distribution",
        height=400
    )
    
    # 3. Action Usage by Segment
    segment_action_metrics = (
        usage_df[usage_df['product_name'] == product]
        .merge(user_segments[['customerid', 'segment']], on='customerid')
        .groupby(['action_type_id', 'segment'])
        .agg({
            'customerid': 'nunique',
            'usage_count': 'sum'
        })
        .reset_index()
    )
    
    fig_action_segments = go.Figure()
    
    for segment in ['Power Users', 'Regular Users', 'Infrequent Users']:
        segment_data = segment_action_metrics[
            segment_action_metrics['segment'] == segment
        ]
        
        fig_action_segments.add_trace(
            go.Bar(
                name=segment,
                x=segment_data['action_type_id'],
                y=segment_data['customerid'],
                text=segment_data['customerid'],
                textposition='auto'
            )
        )
    
    fig_action_segments.update_layout(
        barmode='stack',
        title='Action Usage by User Segment',
        xaxis_title='Action ID',
        yaxis_title='Number of Users',
        height=400,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    return fig_overview, fig_segments, fig_action_segments

def get_segment_summary(user_metrics):
    """Get summary statistics for each segment."""
    summary = user_metrics.groupby('segment').agg({
        'customerid': 'count',
        'days_per_week': 'mean',
        'actions_per_week': 'mean',
        'action_variety': 'mean',
        'total_actions': 'mean'
    }).round(2)
    
    summary.columns = [
        'User Count',
        'Avg Days/Week',
        'Avg Actions/Week',
        'Avg Action Types Used',
        'Avg Total Actions'
    ]
    
    return summary