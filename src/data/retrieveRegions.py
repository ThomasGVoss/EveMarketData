import json
import urllib3
import duckdb
import pandas as pd
import polars as pl
import pytz
from datetime import datetime
import sys
import logging

logger = logging.getLogger(__name__)

duck_db_uri = "/workspaces/EveMarketData/data/market_data.db"


def create_db():

    with duckdb.connect(duck_db_uri) as connection:
        # Create a table to store market data
        create_table_query = """
        CREATE TABLE IF NOT EXISTS regions (
            id INTEGER PRIMARY KEY
        )
        """

        connection.sql(create_table_query)


def retrieve_region_id(): 

    # Define the URL of the REST endpoint
    url = "https://esi.evetech.net/latest/universe/regions/"
    http = urllib3.PoolManager()
    response = http.request("GET", url)

    try: 
        # Check if the request was successful (status code 200)
        if response.status == 200:
            # Parse the JSON response
            data = response.data
            values = json.loads(data)

            response_df = pl.DataFrame(values)
            return response_df
            
        else:
            logger.warning(f"There was an code {response.status} from the API - not the 200 we would expect")
            sys.exit(-1)

    except Exception as e: 
        logger.error("Error retrieving data from the API - {e}")


def write(df):

    try:
        with duckdb.connect(duck_db_uri) as connection:
            connection.sql(f"""
                INSERT OR REPLACE INTO regions 
                    SELECT column_0 FROM df;
                """)       
 
    except Exception as e:
        logger.error(e)
           


def main():

    create_db()  

    response_df = retrieve_region_id()
    
    write(response_df)
    

if __name__ == "__main__":
    main()
