import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from data_manager import load_data

def calculate_purchase_metrics():
    # Get data from centralized loader
    usage_df, customers_df = load_data()
    if usage_df is None or customers_df is None:
        return None
    
    # Calculate time to purchase
    customers_df['time_to_purchase'] = (customers_df['first_purchase_date'] - customers_df['first_activation_date']).dt.days
    
    # Count negative time cases
    negative_time_cases = customers_df[customers_df['time_to_purchase'] < 0]['customerid'].nunique()
    
    # Overall metrics
    total_activated = customers_df[customers_df['first_activation_date'].notna()]['customerid'].nunique()
    
    # Get customers who purchased
    purchased_customers = customers_df[customers_df['first_purchase_date'].notna()]['customerid'].unique()
    total_purchased = len(purchased_customers)
    
    # Count purchased customers who have usage data
    total_used = usage_df[
        (usage_df['event_date'].notna()) & 
        (usage_df['customerid'].isin(purchased_customers))
    ]['customerid'].nunique()
    
    overall_purchase_rate = total_purchased / total_activated if total_activated > 0 else 0
    overall_usage_rate = total_used / total_purchased if total_purchased > 0 else 0
    avg_time_to_purchase = customers_df[customers_df['time_to_purchase'] >= 0]['time_to_purchase'].mean()
    
    # Product-level metrics
    product_metrics = []
    
    for product in customers_df['product_name'].dropna().unique():
        product_data = customers_df[customers_df['product_name'] == product]
        
        # Get activated and purchased counts
        activated = product_data[product_data['first_activation_date'].notna()]['customerid'].nunique()
        
        # Get customers who purchased this product
        product_purchased_customers = product_data[
            product_data['first_purchase_date'].notna()
        ]['customerid'].unique()
        purchased = len(product_purchased_customers)
        
        # Count purchased customers who have usage data for this product
        used = usage_df[
            (usage_df['product_name'] == product) & 
            (usage_df['event_date'].notna()) &
            (usage_df['customerid'].isin(product_purchased_customers))
        ]['customerid'].nunique()
        
        purchase_rate = purchased / activated if activated > 0 else 0
        usage_rate = used / purchased if purchased > 0 else 0
        avg_time = product_data[product_data['time_to_purchase'] >= 0]['time_to_purchase'].mean()
        
        product_metrics.append({
            'product': product,
            'activated': activated,
            'purchased': purchased,
            'used': used,
            'purchase_rate': purchase_rate,
            'usage_rate': usage_rate,
            'avg_time_to_purchase': avg_time
        })
    
    return {
        'overall': {
            'activated': total_activated,
            'purchased': total_purchased,
            'used': total_used,
            'purchase_rate': overall_purchase_rate,
            'usage_rate': overall_usage_rate,
            'avg_time_to_purchase': avg_time_to_purchase,
            'negative_time_cases': negative_time_cases
        },
        'by_product': product_metrics
    }

def create_funnel_figures():
    metrics = calculate_purchase_metrics()
    if metrics is None:
        return None, None
        
    # Create overall funnel
    overall_fig = go.Figure()
    
    overall_fig.add_trace(go.Funnel(
        name='Overall',
        y=['Activated', 'Purchased', 'Used'],
        x=[
            metrics['overall']['activated'],
            metrics['overall']['purchased'],
            metrics['overall']['used']
        ],
        textinfo="value+percent initial",
        opacity=0.65
    ))
    
    overall_fig.update_layout(
        title=f"Overall Customer Funnel<br><sub>Avg Time to Purchase: {metrics['overall']['avg_time_to_purchase']:.1f} days<br>Purchase Rate: {metrics['overall']['purchase_rate']:.1%}, Usage Rate: {metrics['overall']['usage_rate']:.1%}</sub>",
        showlegend=False
    )
    
    # Create product-level funnel
    product_fig = go.Figure()
    
    for product in metrics['by_product']:
        product_fig.add_trace(go.Funnel(
            name=product['product'],
            y=['Activated', 'Purchased', 'Used'],
            x=[
                product['activated'],
                product['purchased'],
                product['used']
            ],
            textinfo="value+percent initial"
        ))
    
    product_fig.update_layout(
        title="Customer Funnel by Product",
        showlegend=True
    )
    
    return overall_fig, product_fig