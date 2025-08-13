def get_unique_products(weekly_customer_metrics, weekly_active_users):
    """Get unique products from metrics, handling NaN values"""
    products = set()
    
    # Add products from customer metrics
    if 'first_signedup_product' in weekly_customer_metrics.columns:
        products.update(weekly_customer_metrics['first_signedup_product'].dropna().unique())
    
    # Add products from active users
    if not weekly_active_users.empty and 'product_name' in weekly_active_users.columns:
        products.update(weekly_active_users['product_name'].dropna().unique())
    
    # Sort and return as list
    return sorted(products)