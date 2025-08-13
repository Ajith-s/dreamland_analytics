import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from stickiness import calculate_time_based_stickiness, STICKINESS_THRESHOLDS

def plot_overview_trends(weekly_customer_metrics, weekly_new_users, weekly_active_users, weekly_cancellations, cross_product_usage, weekly_purchases):
    """Plot overall trends for all products combined with simplified legend"""
    
    fig = make_subplots(
        rows=4, cols=2,  # Changed from 3 rows to 4
        subplot_titles=(
            'Weekly Signups by Product',
            'Weekly New Users by Product', 
            'Weekly Cross-Product Signups by Product',
            'Weekly Cross-Product Usage by Product',
            'Weekly Cancellations by Product',
            'Weekly Purchases by Product',  
            None,
            None
        ),
        specs=[[{"secondary_y": False}, {"secondary_y": False}],
               [{"secondary_y": False}, {"secondary_y": False}],
               [{"secondary_y": False}, {"secondary_y": False}],
               [{"secondary_y": False}, None]],
        vertical_spacing=0.12
    )

    
    # Use distinct colors for each product
    colors = px.colors.qualitative.Set2  # Using Set2 for more distinct colors
    
    # Get unique products across all metrics
    all_products = sorted(set(
        list(weekly_customer_metrics['first_signedup_product'].unique()) +
        list(weekly_new_users['product_name'].unique()) +
        list(weekly_active_users['product_name'].unique() if not weekly_active_users.empty else [])
    ))
    all_products = [p for p in all_products if pd.notna(p)]
    
    # Create color mapping for consistency
    color_map = dict(zip(all_products, colors[:len(all_products)]))
    
    # Weekly signups by product
    for product in all_products:
        data = weekly_customer_metrics[
            weekly_customer_metrics['first_signedup_product'] == product
        ]
        if not data.empty:
            fig.add_trace(
                go.Scatter(
                    x=data['signup_week'], 
                    y=data['customerid'],
                    name=product,  # Simplified legend name
                    line=dict(color=color_map[product]),
                    showlegend=True
                ),
                row=1, col=1
            )
    
    # Weekly new users by product
    for product in all_products:
        data = weekly_new_users[weekly_new_users['product_name'] == product]
        if not data.empty:
            fig.add_trace(
                go.Scatter(
                    x=data['week'], 
                    y=data['new_users'],
                    name=product,
                    line=dict(color=color_map[product]),
                    showlegend=False  # Don't show in legend again
                ),
                row=1, col=2
            )
            
    
    # Cross-product signups by product
    for product in all_products:
        data = weekly_customer_metrics[
            weekly_customer_metrics['first_signedup_product'] == product
        ]
        if not data.empty:
            fig.add_trace(
                go.Scatter(
                    x=data['signup_week'], 
                    y=data['cross_product_rate'],
                    name=product,
                    line=dict(color=color_map[product]),
                    showlegend=False
                ),
                row=2, col=1
            )
            
    
    # Cross-product usage by product
    for product in all_products:
        data = cross_product_usage[cross_product_usage['product_name'] == product]
        if not data.empty:
            fig.add_trace(
                go.Scatter(
                    x=data['week'],
                    y=data['cross_product_rate'],
                    name=product,
                    line=dict(color=color_map[product]),
                    showlegend=False
                ),
                row=2, col=2
            )
            
    
    # Weekly cancellations by product
    for product in all_products:
        data = weekly_cancellations[weekly_cancellations['product_name'] == product]
        if not data.empty:
            fig.add_trace(
                go.Scatter(
                    x=data['week'],
                    y=data['cancelled_users'],
                    name=product,
                    line=dict(color=color_map[product]),
                    showlegend=False
                ),
                row=3, col=1
            )
            

     # Add Weekly purchases by product
    for product in all_products:
        data = weekly_purchases[weekly_purchases['product_name'] == product]
        if not data.empty:
            fig.add_trace(
                go.Scatter(
                    x=data['week'],
                    y=data['purchased_users'],
                    name=product,
                    line=dict(color=color_map[product]),
                    showlegend=False
                ),
                row=3, col=2
            )
            
    
    # Update layout with better spacing and single legend
    fig.update_layout(
        height=1200,  # Increased height for 6 charts
        title_text="Growth Metrics Trends by Product",
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    # Add y-axis titles with clear descriptions
    fig.update_yaxes(title_text="Number of Signups", row=1, col=1)
    fig.update_yaxes(title_text="Number of New Users", row=1, col=2)
    fig.update_yaxes(title_text="% of Users with Multiple Products", row=2, col=1)
    fig.update_yaxes(title_text="% of Users Using Multiple Products", row=2, col=2)
    fig.update_yaxes(title_text="Number of Cancellations", row=3, col=1)
    fig.update_yaxes(title_text="Number of Purchases", row=3, col=1)
    
    # Add x-axis titles with specific time dimensions
    fig.update_xaxes(title_text="Signup Week", row=1, col=1)
    fig.update_xaxes(title_text="First Event Week", row=1, col=2)
    fig.update_xaxes(title_text="Signup Week", row=2, col=1)
    fig.update_xaxes(title_text="Event Week", row=2, col=2)
    fig.update_xaxes(title_text="Cancellation Week", row=3, col=1)
    fig.update_xaxes(title_text="Purchase Week", row=3, col=2)
    
    return fig

def calculate_monthly_retention(usage_df, product):
    """Calculate monthly retention rate for a specific product"""
    # Filter for the product
    product_df = usage_df[usage_df['product_name'] == product].copy()
    
    # Add month number
    product_df['month'] = product_df['event_date'].dt.to_period('M')
    
    # Get active users by month
    monthly_active = (
        product_df
        .groupby('month')['customerid']
        .nunique()
        .reset_index()
    )
    
    # Calculate retention rate
    monthly_active['retention_rate'] = monthly_active['customerid'].shift(-1) / monthly_active['customerid']
    
    # Convert month period to datetime for plotting
    monthly_active['month'] = monthly_active['month'].dt.end_time
    
    return monthly_active

def show_product_metrics(product, weekly_customer_metrics, weekly_new_users, weekly_active_users, weekly_cancellations, daily_usage, user_engagement, weekly_purchases):
    """Display detailed metrics for a specific product"""
    
    st.subheader(f"📊 Detailed Metrics for {product}")
    
    # Filter data for this product
    product_signups = weekly_customer_metrics[
        weekly_customer_metrics['first_signedup_product'] == product
    ]
    product_new_users = weekly_new_users[
        weekly_new_users['product_name'] == product
    ]
    product_active = weekly_active_users[
        weekly_active_users['product_name'] == product
    ] if not weekly_active_users.empty else pd.DataFrame()
    product_cancellations = weekly_cancellations[
        weekly_cancellations['product_name'] == product
    ]
    
    # # Create subplots for weekly trends
    # fig = make_subplots(
    #     rows=2, cols=2,
    #     subplot_titles=('Weekly Signups', 'Weekly New Users', 
    #                    'Weekly Cross-Product Adoption', 'Weekly Cancellations'),
    #     specs=[[{"secondary_y": False}, {"secondary_y": False}],
    #            [{"secondary_y": False}, {"secondary_y": False}]]
    # )
    
    # # Weekly signups
    # fig.add_trace(
    #     go.Scatter(x=product_signups['signup_week'], 
    #               y=product_signups['customerid'],
    #               name='Signups', line=dict(color='blue', width=3)),
    #     row=1, col=1
    # )
    
    # # Weekly new users
    # fig.add_trace(
    #     go.Scatter(x=product_new_users['week'], 
    #               y=product_new_users['new_users'],
    #               name='New Users', line=dict(color='red', width=3)),
    #     row=1, col=2
    # )
    
    # # Cross-product rate
    # fig.add_trace(
    #     go.Scatter(x=product_signups['signup_week'], 
    #               y=product_signups['cross_product_rate'],
    #               name='Cross-Product Rate', line=dict(color='green', width=3)),
    #     row=2, col=1
    # )
    
    # # Weekly cancellations
    # if not product_cancellations.empty:
    #     fig.add_trace(
    #         go.Bar(
    #             x=product_cancellations['week'],
    #             y=product_cancellations['cancelled_users'],
    #             name='Cancelled Users',
    #             marker_color='red'
    #         ),
    #         row=2, col=2
    #     )
    
    # fig.update_layout(
    #     height=800,
    #     title_text=f"Weekly Growth Metrics Trends - {product}",
    #     showlegend=True
    # )
    #     # Add Weekly Active Users and Purchase trends
    # st.subheader("Weekly User Activity and Purchases")
    # col1, col2 = st.columns(2)
    
    # with col1:
    #     # Weekly Active Users
    #     active_data = weekly_active_users[
    #         weekly_active_users['product_name'] == product
    #     ]
        
    #     fig_active = go.Figure()
    #     fig_active.add_trace(
    #         go.Scatter(
    #             x=active_data['week'],
    #             y=active_data['active_users'],
    #             mode='lines+markers',
    #             name='Active Users',
    #             line=dict(color='blue', width=2)
    #         )
    #     )
    #     fig_active.update_layout(
    #         title='Weekly Active Users',
    #         xaxis_title='Week',
    #         yaxis_title='Number of Active Users',
    #         height=400
    #     )
    #     st.plotly_chart(fig_active, use_container_width=True)
    
    # with col2:
    #     # Weekly Purchases
    #     purchase_data = weekly_purchases[
    #         weekly_purchases['product_name'] == product
    #     ]
        
    #     fig_purchase = go.Figure()
    #     fig_purchase.add_trace(
    #         go.Scatter(
    #             x=purchase_data['week'],
    #             y=purchase_data['purchased_users'],
    #             mode='lines+markers',
    #             name='Purchases',
    #             line=dict(color='green', width=2)
    #         )
    #     )
    #     fig_purchase.update_layout(
    #         title='Weekly Purchases',
    #         xaxis_title='Week',
    #         yaxis_title='Number of Purchases',
    #         height=400
    #     )
    #     st.plotly_chart(fig_purchase, use_container_width=True)
    


    # # Update y-axes
    # fig.update_yaxes(title_text="Number of Users", row=1, col=1)
    # fig.update_yaxes(title_text="Number of Users", row=1, col=2)
    # fig.update_yaxes(title_text="Cross-Product Rate", row=2, col=1)
    # fig.update_yaxes(title_text="Number of Cancellations", row=2, col=2)
    
    # # Update x-axes
    # fig.update_xaxes(title_text="Signup Week", row=1, col=1)
    # fig.update_xaxes(title_text="First Event Week", row=1, col=2)
    # fig.update_xaxes(title_text="Signup Week", row=2, col=1)
    # fig.update_xaxes(title_text="Cancellation Week", row=2, col=2)
    
    # st.plotly_chart(fig, use_container_width=True)
    
    # # Show summary metrics
    # col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    # with col1:
    #     total_signups = product_signups['customerid'].sum()
    #     st.metric(f"Total Signups", f"{total_signups:,}")
    
    # with col2:
    #     total_new_users = product_new_users['new_users'].sum()
    #     st.metric(f"Total New Users", f"{total_new_users:,}")
    
    # with col3:
    #     if not product_active.empty:
    #         avg_weekly_active = active_data['active_users'].mean()
    #         st.metric(f"Avg Weekly Active Users", f"{avg_weekly_active:.0f}")
    
    # with col4:
    #     if not weekly_cancellations.empty:
    #         total_cancelled = weekly_cancellations[
    #             weekly_cancellations['product_name'] == product
    #         ]['cancelled_users'].sum()
    #         cancellation_rate = total_cancelled / total_signups if total_signups > 0 else 0
    #         st.metric(f"Overall Cancellation Rate", f"{cancellation_rate:.1%}")
    
    # with col5:
    #     total_purchased = purchase_data['purchased_users'].sum()
    #     st.metric(f"Total Purchased Users", f"{total_purchased:,}")
    
    # with col6:
    #     # Calculate active purchasers (purchased but not cancelled)
    #     active_purchasers = total_purchased - total_cancelled
    #     st.metric(f"Active Purchased Users", f"{active_purchasers:,}")
    
    # Churn Analysis
    st.subheader("Cohort Analysis with Churn Metrics")
    st.caption("""
    **Definitions:**
    - Cohort: Group of users based on their first usage week
    - Churn: User is considered churned if inactive for 21+ days
    - Churn Rate: Number of churned users / Total users in cohort
    """)
    
    # Import and calculate churn metrics
    from churn_analysis import calculate_churn_metrics, plot_churn_analysis
    
    cohort_metrics = calculate_churn_metrics(daily_usage, product)
    fig_churn = plot_churn_analysis(cohort_metrics)
    st.plotly_chart(fig_churn, use_container_width=True)
    
    # Add summary metrics for churn
    col1, col2, col3 = st.columns(3)
    
    with col1:
        total_cohort_size = cohort_metrics['cohort_size'].sum()
        st.metric("Total Users in Cohorts", f"{total_cohort_size:,}")
    
    with col2:
        total_churned = cohort_metrics['churned_users'].sum()
        st.metric("Total Churned Users", f"{total_churned:,}")
    
    with col3:
        overall_churn_rate = total_churned / total_cohort_size if total_cohort_size > 0 else 0
        st.metric("Overall Churn Rate", f"{overall_churn_rate:.1%}")
    
    # Engagement Analysis
    st.subheader("User Engagement Analysis")
    
    product_engagement = user_engagement[user_engagement['product_name'] == product]
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig = px.histogram(product_engagement, x='active_days', nbins=30,
                          title=f'Distribution of Active Days per User')
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        fig = px.scatter(product_engagement, x='active_days', y='total_usage',
                        title=f'Active Days vs Total Usage',
                        hover_data=['actions_taken'])
        st.plotly_chart(fig, use_container_width=True)
    
    # Engagement summary metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        avg_active_days = product_engagement['active_days'].mean()
        st.metric(f"Avg Active Days", f"{avg_active_days:.1f}")
    
    with col2:
        avg_usage = product_engagement['total_usage'].mean()
        st.metric(f"Avg Total Usage", f"{avg_usage:.1f}")
    
    with col3:
        avg_actions = product_engagement['actions_taken'].mean()
        st.metric(f"Avg Daily Actions", f"{avg_actions:.1f}")

def show_action_stickiness_section(stickiness_metrics, top_sticky_actions, segments_df, usage_df, section_key="main"):
    """Display action stickiness analysis section"""
    
    st.header("🎯 Enhanced Action Stickiness Analysis")
    st.write("""
    **Enhanced Stickiness Definition:**
    - Frequency: Minimum unique days of usage (varies by product)
    - Intensity: Actions above 70th percentile for each product-action combination
    - Power Users: Meet both frequency and intensity thresholds
    """)
    
    # Group products into columns
    products = sorted(stickiness_metrics['product_name'].unique())
    cols = st.columns(min(3, len(products)))
    
    for idx, product in enumerate(products):
        col = cols[idx % len(cols)]
        with col:
            st.subheader(f"{product}")
            
            # Get product metrics
            product_metrics = stickiness_metrics[stickiness_metrics['product_name'] == product]
            top_5 = product_metrics.nlargest(5, 'stickiness_ratio')
            
            # Show thresholds for top action
            top_action = top_5.iloc[0]
            st.metric(
                "Day Threshold",
                f"{STICKINESS_THRESHOLDS.get(product, STICKINESS_THRESHOLDS['default'])} days"
            )
            st.metric(
                "Action Threshold",
                f"{top_action['action_threshold']:.0f} actions"
            )
            
            # Show user segments for top action
            segments = segments_df[
                (segments_df['product_name'] == product) &
                (segments_df['action_type_id'] == top_action['action_type_id'])
            ].iloc[0]
            
            # Create a treemap of user segments
            segment_data = pd.DataFrame([
                {'segment': 'Power Users', 'value': segments['power_users_pct']},
                {'segment': 'Frequent Light', 'value': segments['frequent_light_pct']},
                {'segment': 'Intensive Irregular', 'value': segments['intensive_irregular_pct']},
                {'segment': 'Other Users', 'value': 1 - segments['power_users_pct'] - 
                 segments['frequent_light_pct'] - segments['intensive_irregular_pct']}
            ])
            
            fig = px.treemap(
                segment_data,
                path=['segment'],
                values='value',
                title=f'User Segments - Action {top_action["action_type_id"]}',
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            fig.update_traces(textinfo="label+percent parent")
            st.plotly_chart(fig, use_container_width=True, key=f"{section_key}_treemap_{product}_{idx}")
            
            # Show action distribution
            fig = px.bar(
                top_5,
                x='action_type_id',
                y=['power_users_pct', 'frequent_light_pct', 'intensive_irregular_pct'],
                title=f'Top 5 Actions - User Segments',
                labels={
                    'action_type_id': 'Action ID',
                    'value': 'Percentage of Users',
                    'variable': 'Segment'
                },
                barmode='stack'
            )
            st.plotly_chart(fig, use_container_width=True, key=f"{section_key}_action_dist_{product}_{idx}")
    
    # Time-based Analysis
    st.header("📈 Stickiness Trends")
    
    weekly_stickiness = calculate_time_based_stickiness(usage_df)
    
    # Plot stickiness trends for top actions with segment breakdown
    fig = go.Figure()
    
    for product in products:
        top_action = top_sticky_actions[top_sticky_actions['product_name'] == product].iloc[0]
        action_trend = weekly_stickiness[
            (weekly_stickiness['product_name'] == product) &
            (weekly_stickiness['action_type_id'] == top_action['action_type_id'])
        ]
        
        # Add traces for each segment
        fig.add_trace(
            go.Scatter(
                x=action_trend['week'],
                y=action_trend['power_users_pct'],
                name=f"{product} - Power Users",
                mode='lines',
                stackgroup='one'
            )
        )
        fig.add_trace(
            go.Scatter(
                x=action_trend['week'],
                y=action_trend['frequent_light_pct'],
                name=f"{product} - Frequent Light",
                mode='lines',
                stackgroup='one'
            )
        )
        fig.add_trace(
            go.Scatter(
                x=action_trend['week'],
                y=action_trend['intensive_irregular_pct'],
                name=f"{product} - Intensive Irregular",
                mode='lines',
                stackgroup='one'
            )
        )
    
    fig.update_layout(
        title='Weekly User Segments Trends - Top Actions by Product',
        xaxis_title='Week',
        yaxis_title='Percentage of Users',
        height=500,
        hovermode='x unified'
    )
    
    st.plotly_chart(fig, use_container_width=True, key=f"{section_key}_stickiness_trends")