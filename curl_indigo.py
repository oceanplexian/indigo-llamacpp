# This is a pure python example - no additional libraries needed
from urllib.request import Request, urlopen
import json

REFLECTORNAME = os.environ.get("REFLECTOR_NAME", "dummy")
APIKEY = os.environ.get("INDIGO_API_KEY", "dummy")  # Fallback to hardcoded key if not set
 
req = Request(f"https://{REFLECTORNAME}.indigodomo.net/v2/api/indigo.devices")
req.add_header('Authorization', f"Bearer {APIKEY}")
with urlopen(req) as request:

    # Parse the JSON string into a Python object
    devices = json.load(request)

    # Initialize an empty list to hold the filtered data
    filtered_data = []

    # Loop through the devices and filter only the name and states
    for device in devices:
        filtered_data.append({
            'name': device['name'],
            'id': device['id'],
            'states': device['states']
        })

    # Convert the filtered data back to JSON format (optional)
    filtered_json_str = json.dumps(filtered_data)

    # Print the filtered data
    print(filtered_json_str)

