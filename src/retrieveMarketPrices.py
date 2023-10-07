import json
import urllib3
from dataclasses import dataclass, asdict
from datetime import datetime
import csv
import concurrent.futures

@dataclass
class marketItem:
    id: int
    name : str
    averagePrice: int
    generated_at: str

def process_json_result(json_result):
    id = json_result['type_id']
    averagePrice = json_result['average_price'] if 'average_price' in json_result else 0

    resp = urllib3.request(
        "GET",
        "https://esi.evetech.net/dev/universe/types/" + str(id) + "/"
    )
    try:
        item_data = json.loads(resp.data)
        generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S") 

        data_instance = marketItem(id, item_data['name'],
                                    averagePrice, generated_at)
        
        return data_instance
    except Exception as e:
        print(f"An error occurred: {e}")

def write_to_csv():
    current_datetime = datetime.now()
    current_datetime_str = current_datetime.strftime("%Y-%m-%d")

    csv_name = 'data/eve_market_prices_' + current_datetime_str +'.csv'    
    # Write the dictionary to the CSV file
    with open(csv_name, 'w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=asdict(processed_data).keys())
        # Write the header row
        writer.writeheader()
        
        # Write the data rows
        for key, data in result_dict.items():
            writer.writerow(asdict(data))

# Define the URL of the REST endpoint
url = "https://esi.evetech.net/dev/markets/prices/"
http = urllib3.PoolManager()
response = http.request("GET", url)
result_dict = {}

# Check if the request was successful (status code 200)
if response.status == 200:
    try:
    # Parse the JSON response
        data = response.data
        values = json.loads(data)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
            tasks = [executor.submit(process_json_result, json_result) for json_result in values]

            # Keep track of completed tasks
            completed_count = 0
            # Your code to handle the processed_data, e.g., storing it in a dictionary

            # Process completed tasks as they finish
            for future in concurrent.futures.as_completed(tasks):
                # Get the result of the completed task
                processed_data = future.result()
                completed_count += 1
                result_dict[processed_data.id] = processed_data
                if completed_count % 1000 == 0:
                    print(f"Processed {completed_count} out of {len(values)}")
        
        write_to_csv()

    except Exception as e:
            print((f"An error occurred: {e}"))
else:
    print(f"There was an error code {response.status} from the API.")



