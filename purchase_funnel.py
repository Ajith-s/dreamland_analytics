import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

def calculate_purchase_metrics():
    # Read the data
    df = pd.read_csv('Customers.csv')
    usage_df = pd.read_csv('Usage.csv')
    
    # Function to safely convert dates
    def safe_parse_date(date_str):
        if pd.isna(date_str) or date_str == '#REF!':
            return pd.NaT
        try:
            return pd.to_datetime(date_str)
        except:
            return pd.NaT
    
    # Convert dates to datetime safely
    date_columns = ['first_activation_date', 'first_purchase_date']
    for col in date_columns:
        df[col] = pd.to_datetime(df[col], format='%m/%d/%y', errors='coerce')
    
    # Safely convert event_date
    usage_df['event_date'] = usage_df['event_date'].apply(safe_parse_date)
    
    # Calculate time to purchase
    df['time_to_purchase'] = (df['first_purchase_date'] - df['first_activation_date']).dt.days
    
    # Count negative time cases
    negative_time_cases = df[df['time_to_purchase'] < 0]['customerid'].nunique()
    
    # Overall metrics
    total_activated = df[df['first_activation_date'].notna()]['customerid'].nunique()
    
    # Get customers who purchased
    purchased_customers = df[df['first_purchase_date'].notna()]['customerid'].unique()
    total_purchased = len(purchased_customers)
    
    # Count purchased customers who have usage data
    total_used = usage_df[
        (usage_df['event_date'].notna()) & 
        (usage_df['customerid'].isin(purchased_customers))
    ]['customerid'].nunique()
    
    overall_purchase_rate = total_purchased / total_activated if total_activated > 0 else 0
    overall_usage_rate = total_used / total_purchased if total_purchased > 0 else 0
    avg_time_to_purchase = df[df['time_to_purchase'] >= 0]['time_to_purchase'].mean()
    
    # Product-level metrics
    product_metrics = []
    
    for product in df['product_name'].dropna().unique():
        product_data = df[df['product_name'] == product]
        
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

if __name__ == "__main__":
    metrics = calculate_purchase_metrics()
    overall_fig, product_fig = create_funnel_figures()
    
    # Print metrics
    print("\nOverall Metrics:")
    print(f"Activated: {metrics['overall']['activated']}")
    print(f"Purchased: {metrics['overall']['purchased']}")
    print(f"Used: {metrics['overall']['used']}")
    print(f"Purchase Rate: {metrics['overall']['purchase_rate']:.2%}")
    print(f"Usage Rate: {metrics['overall']['usage_rate']:.2%}")
    print(f"Average Time to Purchase: {metrics['overall']['avg_time_to_purchase']:.1f} days")
    print(f"Customers with negative time to purchase: {metrics['overall']['negative_time_cases']}")
    
    print("\nProduct Metrics:")
    for product in metrics['by_product']:
        print(f"\n{product['product']}:")
        print(f"Activated: {product['activated']}")
        print(f"Purchased: {product['purchased']}")
        print(f"Used: {product['used']}")
        print(f"Purchase Rate: {product['purchase_rate']:.2%}")
        print(f"Usage Rate: {product['usage_rate']:.2%}")
        print(f"Average Time to Purchase: {product['avg_time_to_purchase']:.1f} days")