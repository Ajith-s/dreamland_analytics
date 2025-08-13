import pandas as pd
import numpy as np

# Define product-specific day thresholds
STICKINESS_THRESHOLDS = {
    'QuickBooks': 5,  # Financial software - expected frequent use
    'TurboTax': 2,   # Seasonal product - fewer uses expected
    'Mint': 4,       # Personal finance - regular check-ins expected
    'default': 3     # Default threshold
}

def get_action_thresholds(usage_df):
    """Calculate 70th percentile thresholds for each product-action combination"""
    # Group by user, product, and action to get total actions per user
    user_action_totals = (
        usage_df
        .groupby(['customerid', 'product_name', 'action_type_id'])['usage_count']
        .sum()
        .reset_index()
    )
    
    # Calculate 70th percentile for each product-action combination
    action_thresholds = (
        user_action_totals
        .groupby(['product_name', 'action_type_id'])['usage_count']
        .quantile(0.7)
        .reset_index()
        .rename(columns={'usage_count': 'action_threshold'})
    )
    
    return action_thresholds

def analyze_user_segments(usage_df, action_thresholds):
    """Analyze user segments based on day and action thresholds"""
    segments = []
    
    for product in usage_df['product_name'].unique():
        if pd.isna(product):
            continue
            
        day_threshold = STICKINESS_THRESHOLDS.get(product, STICKINESS_THRESHOLDS['default'])
        product_users = usage_df[usage_df['product_name'] == product]
        
        for action_id in product_users['action_type_id'].unique():
            action_data = product_users[product_users['action_type_id'] == action_id]
            action_threshold = action_thresholds[
                (action_thresholds['product_name'] == product) & 
                (action_thresholds['action_type_id'] == action_id)
            ]['action_threshold'].iloc[0]
            
            # Calculate metrics for each user
            user_metrics = (
                action_data
                .groupby('customerid')
                .agg({
                    'event_date': 'nunique',
                    'usage_count': 'sum'
                })
                .reset_index()
            )
            
            total_users = len(user_metrics)
            if total_users == 0:
                continue
                
            # Segment users
            meets_days = user_metrics['event_date'] >= day_threshold
            meets_actions = user_metrics['usage_count'] >= action_threshold
            
            power_users = (meets_days & meets_actions).sum()
            frequent_light = (meets_days & ~meets_actions).sum()
            intensive_irregular = (~meets_days & meets_actions).sum()
            
            segments.append({
                'product_name': product,
                'action_type_id': action_id,
                'day_threshold': day_threshold,
                'action_threshold': action_threshold,
                'total_users': total_users,
                'power_users': power_users,
                'power_users_pct': power_users / total_users,
                'frequent_light_users': frequent_light,
                'frequent_light_pct': frequent_light / total_users,
                'intensive_irregular_users': intensive_irregular,
                'intensive_irregular_pct': intensive_irregular / total_users,
                'median_days': user_metrics['event_date'].median(),
                'median_actions': user_metrics['usage_count'].median()
            })
    
    return pd.DataFrame(segments)

def calculate_action_stickiness(usage_df):
    """Calculate enhanced stickiness metrics using both day and action thresholds"""
    
    # Get action thresholds
    action_thresholds = get_action_thresholds(usage_df)
    
    # Calculate user segments
    segments_df = analyze_user_segments(usage_df, action_thresholds)
    
    # Calculate stickiness metrics
    stickiness_metrics = segments_df.copy()
    stickiness_metrics['stickiness_ratio'] = stickiness_metrics['power_users_pct']
    
    # Get top action per product
    top_sticky_actions = (
        stickiness_metrics
        .sort_values('power_users_pct', ascending=False)
        .groupby('product_name')
        .first()
        .reset_index()
    )
    
    # Calculate overall product stickiness based on most sticky action
    product_stickiness = dict(zip(
        top_sticky_actions['product_name'],
        top_sticky_actions['power_users_pct']
    ))
    
    return stickiness_metrics, top_sticky_actions, product_stickiness, segments_df

def calculate_time_based_stickiness(usage_df):
    """Calculate stickiness metrics over time with enhanced definition"""
    
    # Add week field
    usage_df = usage_df.copy()
    usage_df['week'] = usage_df['event_date'].dt.to_period('W')
    
    weekly_stickiness = []
    
    # Calculate stickiness for each week
    for week in sorted(usage_df['week'].unique()):
        week_data = usage_df[usage_df['week'] == week]
        
        # Get action thresholds for this week
        action_thresholds = get_action_thresholds(week_data)
        
        # Calculate segments for this week
        segments = analyze_user_segments(week_data, action_thresholds)
        
        # Add week information
        segments['week'] = week.start_time
        weekly_stickiness.append(segments)
    
    return pd.concat(weekly_stickiness, ignore_index=True)

def get_weekly_new_users(daily_usage):
    """Calculate new users per week based on first usage date"""
    # Get first usage date for each customer-product combination
    first_usage = (
        daily_usage
        .groupby(['customerid', 'product_name'])['event_date']
        .min()
        .reset_index()
    )
    
    # Convert to weekly and count new users
    first_usage['week'] = first_usage['event_date'].dt.to_period('W')
    weekly_new_users = (
        first_usage
        .groupby(['week', 'product_name'])
        .size()
        .reset_index(name='new_users')
    )
    weekly_new_users['week'] = weekly_new_users['week'].dt.start_time
    
    return weekly_new_users

def get_stickiness_insights(segments_df):
    """Generate insights based on user segments"""
    insights = []
    
    for product in segments_df['product_name'].unique():
        product_data = segments_df[segments_df['product_name'] == product]
        
        # Get top action by power users
        top_action = product_data.nlargest(1, 'power_users_pct').iloc[0]
        
        insights.append({
            'product': product,
            'top_action': top_action['action_type_id'],
            'power_users_pct': top_action['power_users_pct'],
            'frequent_light_pct': top_action['frequent_light_pct'],
            'intensive_irregular_pct': top_action['intensive_irregular_pct'],
            'day_threshold': top_action['day_threshold'],
            'action_threshold': top_action['action_threshold'],
            'median_days': top_action['median_days'],
            'median_actions': top_action['median_actions']
        })
        
        # Add specific insights based on segments
        if top_action['frequent_light_pct'] > 0.3:
            insights[-1]['opportunity'] = 'High frequency, low intensity users - Focus on feature adoption'
        elif top_action['intensive_irregular_pct'] > 0.3:
            insights[-1]['opportunity'] = 'High intensity, low frequency users - Focus on regular engagement'
        else:
            insights[-1]['opportunity'] = 'Balanced user base - Focus on converting to power users'
    
    return pd.DataFrame(insights)