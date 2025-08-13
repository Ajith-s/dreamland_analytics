import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

def get_products_per_customer(usage_df):
    """Calculate how many products each customer uses"""
    # Get unique products per customer
    products_per_customer = (
        usage_df
        .groupby('customerid')['product_name']
        .nunique()
        .reset_index(name='num_products')
    )
    
    # Create distribution
    distribution = (
        products_per_customer['num_products']
        .value_counts()
        .reset_index()
    )
    # Rename columns after reset_index
    distribution.columns = ['num_products', 'num_customers']
    # Sort after renaming
    distribution = distribution.sort_values('num_products')
    
    # Calculate percentages
    total_customers = len(products_per_customer)
    distribution['percentage'] = distribution['num_customers'] / total_customers * 100
    
    return distribution, total_customers

def analyze_product_transitions(usage_df):
    """
    Analyze how users transition between products over time
    Returns:
    - transition_matrix: How many users move from one product to another
    - journey_patterns: Most common product usage sequences
    - time_to_transition: Average time between product adoptions
    """
    # Remove rows with null product names
    usage_df = usage_df.dropna(subset=['product_name'])
    
    # Sort usage data by customer and date
    usage_sorted = usage_df.sort_values(['customerid', 'event_date'])
    
    # Get first usage date for each product by customer
    first_product_usage = (
        usage_sorted
        .groupby(['customerid', 'product_name'])['event_date']
        .min()
        .reset_index()
    )
    
    # Create customer journeys
    customer_journeys = []
    transition_counts = {}
    transition_times = []
    
    for customer in first_product_usage['customerid'].unique():
        customer_products = (
            first_product_usage[first_product_usage['customerid'] == customer]
            .sort_values('event_date')
        )
        
        # Record the journey
        journey = customer_products['product_name'].tolist()
        journey_str = ' → '.join(journey)
        customer_journeys.append(journey_str)
        
        # Record transitions
        if len(journey) > 1:
            for i in range(len(journey)-1):
                from_product = journey[i]
                to_product = journey[i+1]
                transition_key = (from_product, to_product)
                
                transition_counts[transition_key] = transition_counts.get(transition_key, 0) + 1
                
                # Calculate time to transition
                from_date = customer_products.iloc[i]['event_date']
                to_date = customer_products.iloc[i+1]['event_date']
                days_to_transition = (to_date - from_date).days
                transition_times.append({
                    'from_product': from_product,
                    'to_product': to_product,
                    'days': days_to_transition
                })
    
    # Create transition matrix
    products = sorted([p for p in usage_df['product_name'].unique() if pd.notna(p)])
    transition_matrix = pd.DataFrame(0, index=products, columns=products)
    
    for (from_product, to_product), count in transition_counts.items():
        if pd.notna(from_product) and pd.notna(to_product):
            transition_matrix.loc[from_product, to_product] = count
    
    # Calculate journey patterns
    journey_patterns = (
        pd.Series(customer_journeys)
        .value_counts()
        .reset_index()
        .rename(columns={'index': 'journey', 0: 'count'})
    )
    
    # Calculate average transition times
    transition_times_df = pd.DataFrame(transition_times)
    if not transition_times_df.empty:
        avg_transition_times = (
            transition_times_df
            .groupby(['from_product', 'to_product'])['days']
            .agg(['mean', 'median', 'count'])
            .reset_index()
        )
    else:
        avg_transition_times = pd.DataFrame(columns=['from_product', 'to_product', 'mean', 'median', 'count'])
    
    # Calculate multi-product usage summary
    products_per_customer_dist, total_customers = get_products_per_customer(usage_df)
    
    return {
        'transition_matrix': transition_matrix,
        'journey_patterns': journey_patterns,
        'avg_transition_times': avg_transition_times,
        'products_per_customer': products_per_customer_dist,
        'total_customers': total_customers
    }

def show_product_transitions(transition_data):
    """Display product transition analysis"""
    st.header("🔄 Product Transition Analysis")
    
    # Multi-product usage summary
    st.subheader("Multi-Product Usage Overview")
    products_per_customer = transition_data['products_per_customer']
    total_customers = transition_data['total_customers']
    
    # Create summary metrics
    multi_product_users = products_per_customer[products_per_customer['num_products'] > 1]['num_customers'].sum()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            "Total Customers",
            f"{total_customers:,}"
        )
    with col2:
        st.metric(
            "Multi-Product Users",
            f"{multi_product_users:,}",
            f"{multi_product_users/total_customers:.1%} of total"
        )
    with col3:
        avg_products = (
            products_per_customer['num_products'] * products_per_customer['num_customers']
        ).sum() / total_customers
        st.metric(
            "Avg Products per Customer",
            f"{avg_products:.2f}"
        )
    
    # Products per customer distribution
    fig = px.bar(
        products_per_customer,
        x='num_products',
        y='percentage',
        text=products_per_customer['num_customers'].apply(lambda x: f'{x:,}'),
        title='Distribution of Products per Customer'
    )
    fig.update_traces(textposition='outside')
    fig.update_layout(
        xaxis_title='Number of Products',
        yaxis_title='Percentage of Customers'
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Transition Matrix Heatmap
    st.subheader("Product Transition Matrix")
    transition_matrix = transition_data['transition_matrix']
    
    if not transition_matrix.empty:
        fig = px.imshow(
            transition_matrix,
            labels=dict(x="To Product", y="From Product", color="Number of Transitions"),
            aspect="auto"
        )
        fig.update_traces(text=transition_matrix.values, texttemplate="%{z}")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No product transitions found in the selected date range.")
    
    # Common Journey Patterns
    st.subheader("Most Common Product Journeys")
    journey_patterns = transition_data['journey_patterns'].head(10)
    
    if not journey_patterns.empty:
        fig = px.bar(
            journey_patterns,
            x='count',
            y='journey',
            orientation='h',
            title='Top 10 Product Journey Patterns'
        )
        fig.update_layout(
            yaxis_title="Journey Pattern",
            xaxis_title="Number of Customers",
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No multi-product journeys found in the selected date range.")
    
    # Transition Times
    st.subheader("Time Between Product Adoptions")
    transition_times = transition_data['avg_transition_times']
    
    # Filter for significant transitions (more than 5 customers)
    significant_transitions = transition_times[transition_times['count'] >= 5]
    
    if not significant_transitions.empty:
        fig = px.scatter(
            significant_transitions,
            x='from_product',
            y='to_product',
            size='count',
            color='mean',
            hover_data=['median', 'count'],
            title='Average Days Between Product Adoptions',
            color_continuous_scale='Viridis'
        )
        fig.update_traces(
            hovertemplate="From: %{x}<br>To: %{y}<br>Mean Days: %{marker.color:.1f}<br>Median Days: %{customdata[0]:.1f}<br>Customers: %{customdata[1]}"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Not enough transition data to show meaningful patterns.")
    
    # Key Insights
    st.subheader("💡 Key Insights")
    
    if not transition_matrix.empty:
        # Calculate insights
        most_common_start = transition_matrix.index[transition_matrix.sum(axis=1).argmax()]
        most_common_second = transition_matrix.columns[transition_matrix.sum(axis=0).argmax()]
        
        if not transition_times.empty and len(transition_times[transition_times['count'] >= 5]) > 0:
            fastest_transition = transition_times.loc[transition_times['count'] >= 5, 'mean'].min()
            transition_insight = f"- Fastest product transition takes {fastest_transition:.1f} days on average"
        else:
            transition_insight = "- Not enough data to determine transition times"
        
        st.write(f"""
        - Most common starting product: **{most_common_start}**
        - Most common second product: **{most_common_second}**
        - {multi_product_users:,} customers ({multi_product_users/total_customers:.1%}) use multiple products
        {transition_insight}
        """)
    
        # Growth Opportunities
        st.subheader("🎯 Growth Opportunities")
        
        # Calculate potential for cross-product adoption
        single_product_users = products_per_customer[products_per_customer['num_products'] == 1]['num_customers'].iloc[0]
        current_conversion = multi_product_users / total_customers
        
        st.write(f"""
        **Cross-Product Adoption Potential:**
        - {single_product_users:,} customers currently use only one product
        - If conversion rate improved by 10%, that would mean {int(single_product_users * 0.1):,} new multi-product users
        - Current cross-product conversion rate: {current_conversion:.1%}
        """)
        
        # Product-specific opportunities
        for product in transition_matrix.index:
            outbound = transition_matrix.loc[product].sum()
            inbound = transition_matrix[product].sum()
            if outbound > 0 or inbound > 0:
                st.write(f"""
                **{product}**:
                - Sends {outbound:.0f} customers to other products
                - Receives {inbound:.0f} customers from other products
                - Net flow: {inbound - outbound:+.0f} customers
                """)
    else:
        st.info("Not enough data to generate insights. Try expanding the date range or checking data quality.")