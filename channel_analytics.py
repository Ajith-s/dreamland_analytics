import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def get_channel_overview_metrics(customer_summary):
    """Calculate overview metrics for each channel"""
    # Get unique customers per channel (first signup channel)
    channel_metrics = (
        customer_summary
        .groupby('first_signedup_channel')
        .agg({
            'customerid': 'nunique',  # Count unique customers
            'activated': 'sum'  # Sum of activated flag
        })
        .reset_index()
        .rename(columns={
            'customerid': 'total_signups',
            'activated': 'total_activated'
        })
    )
    
    # Calculate activation rate
    channel_metrics['activation_rate'] = (
        channel_metrics['total_activated'] / channel_metrics['total_signups']
    )
    
    return channel_metrics

def calculate_channel_trends(customer_summary):
    """Calculate weekly signup and activation trends by channel"""
    # Add week for trending
    customer_summary['signup_week'] = customer_summary['signup_date'].dt.to_period('W')
    customer_summary['activation_week'] = customer_summary['first_activation_date'].dt.to_period('W')
    
    # Calculate weekly signups by channel and product
    weekly_signups = (
        customer_summary
        .groupby([
            'signup_week', 
            'first_signedup_channel',
            'first_signedup_product'
        ])['customerid']
        .nunique()  # Count unique customers
        .reset_index(name='signup_count')
    )
    weekly_signups['signup_week'] = weekly_signups['signup_week'].dt.start_time
    
    # Calculate weekly activations by channel and product
    weekly_activations = (
        customer_summary[customer_summary['activated']]
        .groupby([
            'activation_week',
            'first_signedup_channel',
            'first_signedup_product'
        ])['customerid']
        .nunique()  # Count unique customers
        .reset_index(name='activation_count')
    )
    weekly_activations['activation_week'] = weekly_activations['activation_week'].dt.start_time
    
    return weekly_signups, weekly_activations

def analyze_multi_channel_distribution(customer_summary):
    """Analyze distribution of customers across multiple channels"""
    # Calculate overall multi-channel metrics
    total_customers = customer_summary['customerid'].nunique()
    multi_channel_customers = (
        customer_summary[customer_summary['is_multi_channel']]
        ['customerid'].nunique()
    )
    multi_channel_pct = multi_channel_customers / total_customers
    
    # Get distribution of number of channels
    channel_count_dist = (
        customer_summary.groupby('customerid')['num_channels']
        .first()  # Take first occurrence for each customer
        .value_counts()
        .sort_index()
        .reset_index()
    )
    channel_count_dist.columns = ['num_channels', 'count']
    channel_count_dist['percentage'] = channel_count_dist['count'] / total_customers
    
    # Get common channel combinations
    def get_channel_combo(channels):
        return ' + '.join(sorted(channels))
    
    channel_combos = (
        customer_summary.groupby('customerid')['channel']
        .first()  # Take first occurrence for each customer
        .apply(get_channel_combo)
        .value_counts()
        .head(10)  # Top 10 combinations
        .reset_index()
    )
    channel_combos.columns = ['combination', 'count']
    channel_combos['percentage'] = channel_combos['count'] / total_customers
    
    return {
        'multi_channel_customers': multi_channel_customers,
        'multi_channel_pct': multi_channel_pct,
        'channel_count_dist': channel_count_dist,
        'channel_combinations': channel_combos
    }

def show_channel_analytics(customer_summary):
    """Display channel analytics dashboard"""
    st.header("📊 Channel Analytics")
    
    # Overview Metrics
    st.subheader("Channel Overview")
    channel_metrics = get_channel_overview_metrics(customer_summary)
    
    # Create metrics display with more detail
    cols = st.columns(len(channel_metrics))
    for idx, (col, metrics) in enumerate(zip(cols, channel_metrics.itertuples())):
        with col:
            st.markdown(f"### {metrics.first_signedup_channel}")
            st.metric("Total Signups", f"{metrics.total_signups:,}")
            st.metric("Total Activations", f"{metrics.total_activated:,}")
            st.metric("Activation Rate", f"{metrics.activation_rate:.1%}")
    
    # Channel Trends
    st.subheader("Channel Trends")
    weekly_signups, weekly_activations = calculate_channel_trends(customer_summary)
    
    # Create separate charts for each channel
    for channel in sorted(weekly_signups['first_signedup_channel'].unique()):
        st.markdown(f"### {channel} Channel")
        col1, col2 = st.columns(2)
        
        with col1:
            # Weekly Signups
            channel_signups = weekly_signups[
                weekly_signups['first_signedup_channel'] == channel
            ].copy()
            
            fig_signups = px.bar(
                channel_signups,
                x='signup_week',
                y='signup_count',
                color='first_signedup_product',
                title=f'Weekly Signups - {channel}',
                labels={
                    'signup_week': 'Week',
                    'signup_count': 'Number of Signups',
                    'first_signedup_product': 'Product'
                }
            )
            fig_signups.update_layout(
                barmode='stack',
                height=400,
                hovermode='x unified'
            )
            st.plotly_chart(fig_signups, use_container_width=True)
        
        with col2:
            # Weekly Activations
            channel_activations = weekly_activations[
                weekly_activations['first_signedup_channel'] == channel
            ].copy()
            
            fig_activations = px.bar(
                channel_activations,
                x='activation_week',
                y='activation_count',
                color='first_signedup_product',
                title=f'Weekly Activations - {channel}',
                labels={
                    'activation_week': 'Week',
                    'activation_count': 'Number of Activations',
                    'first_signedup_product': 'Product'
                }
            )
            fig_activations.update_layout(
                barmode='stack',
                height=400,
                hovermode='x unified'
            )
            st.plotly_chart(fig_activations, use_container_width=True)
        
        # Show summary metrics for this channel
        channel_summary = channel_metrics[
            channel_metrics['first_signedup_channel'] == channel
        ].iloc[0]
        
        # Calculate product distribution
        product_dist = (
            weekly_signups[weekly_signups['first_signedup_channel'] == channel]
            .groupby('first_signedup_product')['signup_count']
            .sum()
            .sort_values(ascending=False)
        )
        
        total_signups = product_dist.sum()
        product_breakdown = ", ".join([
            f"{product}: {count:,} ({count/total_signups:.1%})"
            for product, count in product_dist.items()
        ])
        
        st.info(f"""
        **Channel Summary:**
        - Total Signups: {channel_summary.total_signups:,}
        - Total Activations: {channel_summary.total_activated:,}
        - Overall Activation Rate: {channel_summary.activation_rate:.1%}
        
        **Product Distribution:**
        {product_breakdown}
        """)
        
        st.markdown("---")
    
    # Multi-channel Analysis
    st.subheader("Multi-channel Distribution")
    multi_channel_analysis = analyze_multi_channel_distribution(customer_summary)
    
    # Show multi-channel metrics
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric(
            "Multi-channel Customers",
            f"{multi_channel_analysis['multi_channel_customers']:,}",
            f"{multi_channel_analysis['multi_channel_pct']:.1%} of total"
        )
        
        # Channel count distribution
        fig = px.bar(
            multi_channel_analysis['channel_count_dist'],
            x='num_channels',
            y='percentage',
            text=[f'{p:.1%}' for p in multi_channel_analysis['channel_count_dist']['percentage']],
            title='Distribution of Channels per Customer'
        )
        fig.update_layout(
            xaxis_title="Number of Channels",
            yaxis_title="Percentage of Customers",
            yaxis_tickformat='.1%'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Top channel combinations
        st.write("Top Channel Combinations")
        fig = px.bar(
            multi_channel_analysis['channel_combinations'],
            x='percentage',
            y='combination',
            orientation='h',
            text=[f'{p:.1%}' for p in multi_channel_analysis['channel_combinations']['percentage']],
            title='Most Common Channel Combinations'
        )
        fig.update_layout(
            xaxis_title="Percentage of Customers",
            yaxis_title="Channel Combination",
            xaxis_tickformat='.1%',
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Additional Insights
    st.subheader("Additional Channel Insights")
    
    # Calculate time to activation by channel
    activation_data = customer_summary[
        customer_summary['activated']
    ].copy()
    
    # Calculate days to activation
    activation_data['days_to_activation'] = (
        activation_data['first_activation_date'] - activation_data['signup_date']
    ).dt.total_seconds() / (24 * 60 * 60)  # Convert to days
    
    # Filter for valid activation times (only non-negative values)
    activation_data = activation_data[activation_data['days_to_activation'] >= 0]
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Average time to activation by channel
        avg_activation_time = (
            activation_data
            .groupby('first_signedup_channel')
            .agg({
                'days_to_activation': ['mean', 'median']
            })
            .round(1)
        )
        avg_activation_time.columns = ['mean_days', 'median_days']
        avg_activation_time = avg_activation_time.reset_index()
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            name='Mean',
            x=avg_activation_time['first_signedup_channel'],
            y=avg_activation_time['mean_days'],
            text=avg_activation_time['mean_days'].round(1),
            textposition='auto'
        ))
        fig.add_trace(go.Bar(
            name='Median',
            x=avg_activation_time['first_signedup_channel'],
            y=avg_activation_time['median_days'],
            text=avg_activation_time['median_days'].round(1),
            textposition='auto'
        ))
        
        fig.update_layout(
            title='Time to Activation by Channel (Days)',
            barmode='group',
            yaxis_title='Days',
            height=400,
            showlegend=True
        )
        
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Note: Analysis includes only valid activation times (where activation date is after signup date)")
    
    with col2:
        # Product distribution by channel
        product_channel_dist = (
            customer_summary
            .groupby(['first_signedup_channel', 'first_signedup_product'])
            ['customerid']
            .nunique()
            .reset_index(name='count')
        )
        
        # Calculate percentages within each channel
        product_channel_dist['total_channel'] = product_channel_dist.groupby(
            'first_signedup_channel'
        )['count'].transform('sum')
        product_channel_dist['percentage'] = (
            product_channel_dist['count'] / product_channel_dist['total_channel']
        )
        
        fig = px.bar(
            product_channel_dist,
            x='first_signedup_channel',
            y='percentage',
            color='first_signedup_product',
            text=[f'{p:.1%}' for p in product_channel_dist['percentage']],
            title='Product Distribution by Channel'
        )
        fig.update_layout(
            yaxis_title='Percentage of Customers',
            yaxis_tickformat='.1%',
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)