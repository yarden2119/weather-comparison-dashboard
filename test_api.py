import requests
import json
import pandas as pd

url = "https://archive-api.open-meteo.com/v1/archive"

params = {
    "latitude": 32.0853,
    "longitude": 34.7818,
    "start_date": "2025-01-01",
    "end_date": "2025-01-07",
    "daily": (
        "temperature_2m_max,"
        "temperature_2m_min,"
        "precipitation_sum"
    ),
    "timezone": "auto"
}


response = requests.get(
    url,
    params=params,
    timeout=30
)

print("Status code:", response.status_code)

response.raise_for_status()

data = response.json()

daily_data = data["daily"]

df = pd.DataFrame(daily_data)

print("\nWeather table:")
print(df)
#print(df.to_string(index=False))