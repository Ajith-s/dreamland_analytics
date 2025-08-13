import streamlit as st
import pandas as pd

# Constants
CUSTOMERS_FILE = 'customers.csv'
USAGE_FILE = 'usage.csv'

@st.cache_data
def load_data():
    """Load and preprocess data with proper handling of multiple rows per customer"""
    try:
        # Load data with explicit datetime parsing
        usage_df = pd.read_csv(USAGE_FILE)
        customers_df = pd.read_csv(CUSTOMERS_FILE)
        
        # Convert date columns to datetime with error handling
        usage_df['event_date'] = pd.to_datetime(usage_df['event_date'], errors='coerce')
        customers_df['signup_date'] = pd.to_datetime(customers_df['signup_date'], errors='coerce')
        customers_df['first_activation_date'] = pd.to_datetime(customers_df['first_activation_date'], errors='coerce')
        customers_df['first_purchase_date'] = pd.to_datetime(customers_df['first_purchase_date'], errors='coerce')
        customers_df['cancel_date'] = pd.to_datetime(customers_df['cancel_date'], errors='coerce')
        
        # Clean data - remove rows with invalid dates
        usage_df = usage_df.dropna(subset=['event_date'])
        customers_df = customers_df.dropna(subset=['signup_date'])
        
        return usage_df, customers_df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None, None

@st.cache_data
def get_customer_summary(customers_df):
    """Create a clean customer summary handling multiple rows per customer"""
    
    # First, let's get the earliest signup record for each customer to determine first product/channel
    earliest_signup = customers_df.loc[customers_df.groupby('customerid')['signup_date'].idxmin()]
    first_signup_info = earliest_signup[['customerid', 'product_name', 'channel']].rename(columns={
        'product_name': 'first_signedup_product',
        'channel': 'first_signedup_channel'
    })
    
    # Build customer summary with earliest events
    customer_summary = customers_df.groupby('customerid').agg({
        'signup_date': 'min',
        'first_activation_date': 'min',
        'first_purchase_date': 'min',
        'cancel_date': 'min',
        'product_name': lambda x: list(x.dropna().unique()),
        'channel': lambda x: list(x.dropna().unique())
    }).reset_index()

    # Merge in the first signed up product and channel (chronologically first)
    customer_summary = customer_summary.merge(first_signup_info, on='customerid', how='left')
    
    # Fill null first_signedup_product with any available product for that customer
    def fill_first_product(row):
        if pd.isna(row['first_signedup_product']) and len(row['product_name']) > 0:
            return row['product_name'][0]  # Take first available product
        return row['first_signedup_product']
    
    def fill_first_channel(row):
        if pd.isna(row['first_signedup_channel']) and len(row['channel']) > 0:
            return row['channel'][0]  # Take first available channel
        return row['first_signedup_channel']
    
    customer_summary['first_signedup_product'] = customer_summary.apply(fill_first_product, axis=1)
    customer_summary['first_signedup_channel'] = customer_summary.apply(fill_first_channel, axis=1)
    
    # Flags and counts
    customer_summary['signedup'] = customer_summary['signup_date'].notnull()
    customer_summary['activated'] = customer_summary['first_activation_date'].notnull()
    customer_summary['purchased'] = customer_summary['first_purchase_date'].notnull()
    customer_summary['cancelled'] = customer_summary['cancel_date'].notnull()
    customer_summary['num_products'] = customer_summary['product_name'].apply(len)
    customer_summary['num_channels'] = customer_summary['channel'].apply(len)
    customer_summary['is_cross_product'] = customer_summary['num_products'] > 1
    customer_summary['is_multi_channel'] = customer_summary['num_channels'] > 1

    return customer_summary

@st.cache_data
def get_daily_usage_summary(usage_df):
    """Aggregate usage data by customer-date-product level"""
    daily_usage = usage_df.groupby(['customerid', 'event_date', 'product_name']).agg({
        'usage_count': 'sum',  # Total usage across all actions that day
        'action_type_id': 'nunique'  # Number of different actions taken
    }).reset_index()
    daily_usage.columns = ['customerid', 'event_date', 'product_name', 'total_usage', 'actions_taken']
    
    return daily_usage