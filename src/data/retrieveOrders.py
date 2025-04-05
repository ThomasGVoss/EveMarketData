import json
import urllib3
import duckdb
import polars as pl
from datetime import datetime
import sys
import logging


logger = logging.getLogger(__name__)

duck_db_uri = "/workspaces/EveMarketData/data/market_data.db"


def create_db():

    with duckdb.connect(duck_db_uri) as connection:
                
        # Create a table to store market data
        create_table_query = """
        CREATE TABLE IF NOT EXISTS orders (
            typeId TEXT NOT NULL,
            regionId REAL NOT NULL,
            isBuyOrder BOOLEAN NOT NULL,
            minPrice REAL NOT NULL,
            meanPrice REAL NOT NULL,
            maxPrice REAL NOT NULL,
            generated TIMESTAMP NOT NULL,
            PRIMARY KEY (typeId, generated, regionId, isBuyOrder)
        )
        """
        # Foreign Keys to the type ids? 

        connection.sql(create_table_query)


def retrieve_values(region_ids, type_ids):
    
    response_df = pl.DataFrame()
    for id in region_ids:
        region_df = pl.DataFrame()
        for type in type_ids:
            tmp_df = retrieve_by_region_and_id(region=id, type_id=type)
            
            tmp_df = tmp_df.with_columns(
                pl.lit(id).alias("region_id")
            )

            price_df = (tmp_df
                        .group_by("is_buy_order","region_id","type_id")
                        .agg(
                           pl.col("price").min().alias("min_price"),
                           pl.col("price").mean().alias("mean_price"),
                           pl.col("price").max().alias("max_price"))
            )

            # TODO: next we will add a frame to check the vol. remain
            # can we get the sum of the volumen remian at the specific values? 

            region_df = pl.concat([region_df,price_df], how="vertical")
        
        response_df = pl.concat([response_df, region_df], how="vertical")

    response_df = response_df.with_columns(
                generated = datetime.now()
            )

    return response_df
    

def retrieve_by_region_and_id(region,type_id): 

    # Example: https://esi.evetech.net/latest/markets/10000002/orders/?datasource=tranquility&order_type=all&page=1&type_id=17357
    params = '?datasource=tranquility&order_type=all&page=1&type_id={}'.format(type_id)
    url = "https://esi.evetech.net/latest/markets/{}/orders/{}".format(region,params)
    http = urllib3.PoolManager()
    response = http.request("GET", url)

    try: 
        if response.status == 200:
            data = response.data
            values = json.loads(data)

            response_df = pl.DataFrame(values)
            return response_df
            
        else:
            logger.warning(f"There was an code {response.status} from the API - not the 200 we would expect")
            sys.exit(-1)

    except Exception as e: 
        logger.error("Error retrieving data from the API - {e}")

def get_type_ids() -> list :

    duck_db_uri = "/workspaces/EveMarketData/data/market_data.db"

    with duckdb.connect(duck_db_uri) as connection:
        results = (connection.sql(f"""
                SELECT * FROM market_data.market_data 
                                  
                """)
                .fetchall())
        
        type_ids = [i[0] for i in results]

    return type_ids

def write(df):

    try:
        with duckdb.connect(duck_db_uri) as connection:
            connection.sql(f"""
                INSERT OR REPLACE INTO orders 
                    SELECT type_id, region_id, is_buy_order, min_price, mean_price, max_price, generated FROM df;
                """)     
 
    except Exception as e:
        logger.error(e)

def main():

    create_db()  

    region_ids = [10000002,10000032,10000043,10000030]
    type_ids = [17357,230,222,9957]

    # How to get the type IDs of the items we care about? 
    #type_ids = get_type_ids()    

    response_df = retrieve_values(region_ids,type_ids)

    write(response_df)


if __name__ == "__main__":
    main()
