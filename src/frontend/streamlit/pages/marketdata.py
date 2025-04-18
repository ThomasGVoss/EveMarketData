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

# Sidebar for S3 data configuration
with st.sidebar:
    st.header("Data Source Settings")
    
    bucket_name = st.text_input(
        "S3 Bucket Name", 
        value="market-data-dev-142571790518"
    )
         
    # Default folder path
    default_folder = "aggregated/market_prices/"
    
    # Allow users to specify a folder
    folder_path = st.text_input("S3 Folder Path", value=default_folder)
    
    load_button = st.button("Load Data")

# Main content area
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False

# Load data when button is clicked
if load_button:
    with st.spinner("Loading data from S3..."):
        data = load_parquet_files_from_s3(bucket_name, folder_path)

        if data is not None:
            st.session_state.data = data
            st.session_state.data_loaded = True
        else:
            st.error("Failed to load data. Please check the S3 path and bucket name.")

# Display data and visualizations if data is loaded
if st.session_state.get('data_loaded', False):
    data = st.session_state.data
    
    # Data overview
    st.subheader("Data Overview")
    st.write(f"Number of rows: {len(data)}")
    st.write(f"Number of columns: {len(data.columns)}")
    
    # Show data sample
    with st.expander("Data Sample"):
        st.dataframe(data.head(10))
    
    # Show column information
    with st.expander("Column Information"):
        st.dataframe(pd.DataFrame({
            'Column': data.columns,
            'Type': data.dtypes,
            'Non-Null Count': data.count(),
            'Null Count': data.isna().sum()
        }))
    
    # Add a filter for type_id
    if 'type_id' in data.columns:
        st.subheader("Filter by Type ID")
        unique_type_ids = data['type_id'].unique().tolist()
        selected_type_ids = st.multiselect(
            "Select Type ID(s) to filter",
            options=unique_type_ids,
            default=[81901]  # Default to None
        )
        
        # Apply the filter
        if selected_type_ids:
            data = data[data['type_id'].isin(selected_type_ids)]
    
    # Visualization options
    st.subheader("Visualizations")
    
# Allow user to select columns for visualization
    numeric_cols = data.select_dtypes(include=['number']).columns.tolist()
    categorical_cols = data.select_dtypes(exclude=['number']).columns.tolist()
    
    # Ensure 'type_id' is included in categorical columns
    if 'type_id' in data.columns and 'type_id' not in categorical_cols:
        categorical_cols.append('type_id')
    
    # Only show visualization options if we have data to visualize
    if numeric_cols:

        data['processed_timestamp'] = pd.to_datetime(data['processed_timestamp'], errors='coerce')
        
        # Sort data by processed_timestamp
        data = data.sort_values(by='processed_timestamp')

    # Fix col_x to processed_timestamp and col_y to average_price
    col_x = 'processed_timestamp'
    col_y = 'average_price'

    if col_x in data.columns and col_y in data.columns:
        group_by = st.selectbox("Group by (optional)", ["None"] + categorical_cols)
        
        if 'min_daily_price' in data.columns and 'max_daily_price' in data.columns:
            # Create a line plot with a corridor for min and max daily prices
            fig = px.line(data, x=col_x, y=col_y, color=group_by if group_by != "None" else None, title=f"{col_y} over {col_x}")
            
            # Add the min-max corridor
            fig.add_traces([
                go.Scatter(
                    x=data[col_x],
                    y=data['max_daily_price'],
                    mode='lines',
                    line=dict(width=0),
                    showlegend=False,
                    name='Max Price',
                    hoverinfo='skip'
                ),
                go.Scatter(
                    x=data[col_x],
                    y=data['min_daily_price'],
                    mode='lines',
                    line=dict(width=0),
                    fill='tonexty',
                    fillcolor='rgba(0,100,200,0.2)',
                    showlegend=True,
                    name='Price Corridor'
                )
            ])
        else:
            # Create a standard line plot if min and max prices are not available
            fig = px.line(data, x=col_x, y=col_y, color=group_by if group_by != "None" else None, title=f"{col_y} over {col_x}")
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error(f"Columns '{col_x}' and/or '{col_y}' are not available in the data.")

# Footer
st.markdown("---")
st.markdown("Data source: S3 bucket from AWS SageMaker")