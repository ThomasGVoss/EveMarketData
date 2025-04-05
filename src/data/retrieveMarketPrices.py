import json
import urllib3
import duckdb
import polars as pl
import sys
import logging

logger = logging.getLogger(__name__)

duck_db_uri = "/workspaces/EveMarketData/data/market_data.db"


def create_db():

    with duckdb.connect(duck_db_uri) as connection:
        # Create a table to store market data
        create_table_query = """
        CREATE TABLE IF NOT EXISTS market_data (
            id TEXT NOT NULL,
            averagePrice REAL NOT NULL,
            adjustedPrice REAL NOT NULL,
            generated TIMESTAMP NOT NULL,
            PRIMARY KEY (id, generated)
        )
        """

        connection.sql(create_table_query)


def retrieve(): 

    # Define the URL of the REST endpoint
    url = "https://esi.evetech.net/latest/markets/prices/"
    http = urllib3.PoolManager()
    response = http.request("GET", url)
    result_array = []
    result_df = pl.DataFrame()

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


def process(df):

    result_df = df.drop_nulls()
    return result_df


def write(df):

    try:
        with duckdb.connect(duck_db_uri) as connection:
            connection.sql(f"""
                INSERT INTO market_data 
                    SELECT type_id, average_price, adjusted_price, current_timestamp FROM df;
                """)       
 
    except Exception as e:
        logger.error(e)
           


def main():

    create_db()  

    response_df = retrieve()

    result_df = process(response_df)

    write(result_df)
    

if __name__ == "__main__":
    main()
