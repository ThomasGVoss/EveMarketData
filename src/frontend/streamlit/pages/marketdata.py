import streamlit as st
import pandas as pd
import plotly.express as px
from plotly import graph_objects as go  # Import graph_objects for advanced Plotly features
import boto3
import io

# Page config
st.set_page_config(
    page_title="Market Data Analysis",
    page_icon="📊",
    layout="wide"
)

# Title and description
st.title("Market Data Analysis")
st.markdown("""
This page visualizes market data from S3 storage for analysis and predictions.
""")

# AWS S3 configuration
AWS_REGION = "us-east-1"  # Change to your AWS region

# Function to load data from S3
@st.cache_data
def load_data_from_s3(bucket, key):
    """Load data from S3 bucket"""
    try:
        s3_client = boto3.client('s3', region_name=AWS_REGION)
        response = s3_client.get_object(Bucket=bucket, Key=key)
        content = response['Body'].read()
        
        # Determine file type and read accordingly
        if key.endswith('.csv'):
            return pd.read_csv(io.BytesIO(content))
        elif key.endswith('.parquet'):
            return pd.read_parquet(io.BytesIO(content))
        elif key.endswith('.json'):
            return pd.read_json(io.BytesIO(content))
        else:
            st.error(f"Unsupported file format: {key}")
            return None
    except Exception as e:
        st.error(f"Error loading data from S3: {str(e)}")
        return None

# Function to load all Parquet files from an S3 folder
@st.cache_data
def load_parquet_files_from_s3(bucket, folder):
    """Load all Parquet files from a folder in an S3 bucket"""
    try:
        s3_client = boto3.client('s3', region_name=AWS_REGION)
        response = s3_client.list_objects_v2(Bucket=bucket, Prefix=folder)
        
        if 'Contents' not in response:
            st.error(f"No files found in folder: {folder}")
            return None
        
        # Filter for Parquet files
        parquet_files = [obj['Key'] for obj in response['Contents'] if obj['Key'].endswith('.parquet')]
        
        if not parquet_files:
            st.error(f"No Parquet files found in folder: {folder}")
            return None
        
        # Load and concatenate all Parquet files
        data_frames = []
        for key in parquet_files:
            obj = s3_client.get_object(Bucket=bucket, Key=key)
            content = obj['Body'].read()
            data_frames.append(pd.read_parquet(io.BytesIO(content)))
        
        # Combine all data frames
        return pd.concat(data_frames, ignore_index=True)
    except Exception as e:
        st.error(f"Error loading data from S3: {str(e)}")
        return None


# S3 bucket and folder inputs
bucket_name = st.text_input(
    "S3 Bucket Name", 
    value="market-data-dev-142571790518"
)

# Sidebar for S3 data configuration and filters
with st.sidebar:
    common_type_ids = set()

    st.header("Filters")
        
    selected_type_ids = st.multiselect(
        "Filter by Type ID",
        options=list([ 1333, 2994, 34126, 32995, 34132, 34133]),  # Example type IDs
        default=list([32995])  # Default to all type IDs
    )

if 'data_loaded' not in st.session_state or not st.session_state.data_loaded:
    with st.spinner("Loading datasets from S3..."):
        price_data = load_parquet_files_from_s3(bucket_name, "aggregated/market_prices/")
        volumen_data = load_parquet_files_from_s3(bucket_name, "processed/order_volumes/")

        if price_data is not None and volumen_data is not None:
            st.session_state.price_data = price_data
            st.session_state.volumen_data = volumen_data
            st.session_state.data_loaded = True
        else:
            st.error("Failed to load one or both datasets. Please check the S3 paths and bucket name.")

# Display data and visualizations if data is loaded
if st.session_state.get('data_loaded', False):
    price_data = st.session_state.price_data
    volumen_data = st.session_state.volumen_data

    # Apply Type ID filter
    if selected_type_ids:
        if 'type_id' in price_data.columns:
            price_data = price_data[price_data['type_id'].isin(selected_type_ids)]
        if 'type_id' in volumen_data.columns:
            volumen_data = volumen_data[volumen_data['type_id'].isin(selected_type_ids)]
    
    
    # Data overview for Dataset 1
    st.subheader("Dataset 1: Market Prices")
    st.write(f"Number of rows: {len(price_data)}")
    st.write(f"Number of columns: {len(price_data.columns)}")
    with st.expander("Data Sample (Dataset 1)"):
        st.dataframe(price_data.head(10))
    
    # Visualization for Dataset 1
    st.subheader("Visualizations for Dataset 1")
    price_data['processed_timestamp'] = pd.to_datetime(price_data['processed_timestamp'], errors='coerce')
    price_data = price_data.sort_values(by='processed_timestamp')
    if 'processed_timestamp' in price_data.columns and 'average_price' in price_data.columns:
        fig_1 = px.line(
            price_data, 
            x='processed_timestamp', 
            y='average_price', 
            title="Average Price Over Time (Dataset 1)"
        )
        st.plotly_chart(fig_1, use_container_width=True)
    else:
        st.error("Broken....")
    
        
    # Data overview for Dataset 2
    st.subheader("Dataset 2: Market Volumes")
    st.write(f"Number of rows: {len(volumen_data)}")
    st.write(f"Number of columns: {len(volumen_data.columns)}")
    with st.expander("Data Sample (Dataset 2)"):
        st.dataframe(volumen_data.head(10))

    # Visualization for Dataset 2
    st.subheader("Visualizations for Dataset 2")
    if 'system_id' in volumen_data.columns and 'type_id' in volumen_data.columns:
        fig_2 = px.histogram(
            volumen_data, 
            x='price', 
            color='is_buy_order',
            nbins=20,
            title="Average Volume Over Time (Dataset 2)"
        )
        st.plotly_chart(fig_2, use_container_width=True)
    else:
        st.error("Broken....")

# Footer
st.markdown("---")
st.markdown("Data source: S3 bucket from AWS SageMaker")