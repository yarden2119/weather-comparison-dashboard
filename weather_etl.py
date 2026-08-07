from pathlib import Path
import json

import pandas as pd
import requests


# כתובת ה-API לנתוני מזג אוויר היסטוריים
URL = "https://archive-api.open-meteo.com/v1/archive"

# טווח התאריכים של הפרויקט
START_DATE = "2025-01-01"
END_DATE = "2025-12-31"


# המדדים היומיים שאנחנו מבקשים מה-API
DAILY_VARIABLES = [
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "wind_speed_10m_max"
]


# הערים והקואורדינטות שלהן
CITIES = {
    "Tel Aviv": {
        "latitude": 32.0853,
        "longitude": 34.7818
    },
    "New York": {
        "latitude": 40.7128,
        "longitude": -74.0060
    },
    "London": {
        "latitude": 51.5074,
        "longitude": -0.1278
    },
    "Bangkok": {
        "latitude": 13.7563,
        "longitude": 100.5018
    }
}


# תיקיות שבהן נשמור את הנתונים
RAW_DATA_FOLDER = Path("data/raw")
PROCESSED_DATA_FOLDER = Path("data/processed")

# יצירת התיקיות אם הן עדיין לא קיימות
RAW_DATA_FOLDER.mkdir(parents=True, exist_ok=True)
PROCESSED_DATA_FOLDER.mkdir(parents=True, exist_ok=True)


def fetch_city_weather(city_name, coordinates):
    """
    שולחת בקשת API עבור עיר אחת,
    שומרת את תשובת ה-JSON ומחזירה DataFrame.
    """

    params = {
        "latitude": coordinates["latitude"],
        "longitude": coordinates["longitude"],
        "start_date": START_DATE,
        "end_date": END_DATE,
        "daily": ",".join(DAILY_VARIABLES),
        "timezone": "auto",
        "temperature_unit": "celsius",
        "wind_speed_unit": "kmh",
        "precipitation_unit": "mm"
    }

    print(f"Fetching weather data for {city_name}...")

    response = requests.get(
        URL,
        params=params,
        timeout=30
    )

    print(
        f"Status code for {city_name}:",
        response.status_code
    )

    response.raise_for_status()

    data = response.json()

    # יצירת שם קובץ ללא רווחים
    city_file_name = city_name.lower().replace(" ", "_")

    raw_file_path = (
        RAW_DATA_FOLDER
        / f"{city_file_name}_2025.json"
    )

    # שמירת התשובה המקורית שקיבלנו מה-API
    with raw_file_path.open(
        mode="w",
        encoding="utf-8"
    ) as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=4
        )

    # המרת החלק היומי לטבלת פנדס
    city_df = pd.DataFrame(data["daily"])

    # הוספת שם העיר לכל השורות
    city_df["city"] = city_name

    return city_df


# כאן נאסוף את טבלאות כל הערים
city_dataframes = []


# מעבר על כל הערים שבמילון
for city_name, coordinates in CITIES.items():

    city_df = fetch_city_weather(
        city_name,
        coordinates
    )

    city_dataframes.append(city_df)


# חיבור ארבעת הדאטה פריימים לטבלה אחת
weather_df = pd.concat(
    city_dataframes,
    ignore_index=True
)


# שינוי שמות העמודות לשמות ברורים יותר
weather_df = weather_df.rename(
    columns={
        "time": "date",
        "temperature_2m_max": "max_temperature_c",
        "temperature_2m_min": "min_temperature_c",
        "precipitation_sum": "precipitation_mm",
        "wind_speed_10m_max": "max_wind_speed_kmh"
    }
)


def validate_and_clean_data(df):

    print("\nStarting data validation and cleaning...")

    # הסרת כפילויות
    duplicates_before = df.duplicated(
        subset=["city", "date"]
    ).sum()

    df = df.drop_duplicates(
        subset=["city", "date"]
    )

    print("Duplicate rows removed:", duplicates_before)


    # המרת תאריך
    df["date"] = pd.to_datetime(
        df["date"],
        errors="coerce"
    )


    # עמודות שאמורות להיות מספריות
    numeric_columns = [
        "max_temperature_c",
        "min_temperature_c",
        "precipitation_mm",
        "max_wind_speed_kmh"
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )


    # בדיקת ערכים חסרים
    print("\nMissing values after type conversion:")
    print(df.isna().sum())

    # הסרת שורות שחסר בהן מידע הכרחי לניתוח
    required_columns = [
        "city",
        "date",
        "max_temperature_c",
        "min_temperature_c",
        "precipitation_mm",
        "max_wind_speed_kmh"
    ]

    df = df.dropna(
        subset=required_columns
    )

    # בדיקות לערכים לא הגיוניים
    invalid_temperature_rows = (
        df["min_temperature_c"]
        > df["max_temperature_c"]
    ).sum()

    negative_precipitation_rows = (
        df["precipitation_mm"] < 0
    ).sum()

    negative_wind_rows = (
        df["max_wind_speed_kmh"] < 0
    ).sum()


    print(
        "\nRows where minimum temperature "
        "is higher than maximum:",
        invalid_temperature_rows
    )

    print(
        "Rows with negative precipitation:",
        negative_precipitation_rows
    )

    print(
        "Rows with negative wind speed:",
        negative_wind_rows
    )


    # הסרת רשומות בלתי אפשריות
    df = df[
        (df["min_temperature_c"] <= df["max_temperature_c"])
        & (df["precipitation_mm"] >= 0)
        & (df["max_wind_speed_kmh"] >= 0)
    ].copy()


    print("\nRows per city after cleaning:")
    print(df.groupby("city").size())


    print("\nRows after cleaning:", len(df))

    return df


weather_df = validate_and_clean_data(weather_df)

# יצירת עמודת טמפרטורה יומית ממוצעת
weather_df["average_temperature_c"] = (
    (
        weather_df["max_temperature_c"]
        + weather_df["min_temperature_c"]
    )
    / 2
).round(1)


# יצירת טווח הטמפרטורות היומי
weather_df["temperature_range_c"] = (
    weather_df["max_temperature_c"]
    - weather_df["min_temperature_c"]
).round(1)


# חילוץ פרטי זמן מתוך עמודת התאריך
weather_df["year"] = weather_df["date"].dt.year
weather_df["month"] = weather_df["date"].dt.month
weather_df["month_name"] = (
    weather_df["date"].dt.month_name()
)


# עמודה בוליאנית: האם ירדו משקעים באותו יום
weather_df["is_rainy_day"] = (
    weather_df["precipitation_mm"] > 0
)


# מיון לפי עיר ותאריך
weather_df = weather_df.sort_values(
    by=["city", "date"]
).reset_index(drop=True)


# הנתיב שבו יישמר הקובץ הנקי
processed_file_path = (
    PROCESSED_DATA_FOLDER
    / "weather_2025.csv"
)




# בדיקות בסיסיות של התוצאה


print("\nDataFrame shape:")
print(weather_df.shape)

print("\nFirst rows:")
print(weather_df.head())

print("\nFinal validation - missing values:")
print(weather_df.isna().sum())

print("\nFinal validation - duplicate city-date rows:")
print(
    weather_df.duplicated(
        subset=["city", "date"]
    ).sum()
)

# שמירת הדאטה פריים לקובץ CSV
weather_df.to_csv(
    processed_file_path,
    index=False,
    encoding="utf-8-sig"
)

print("\nProcessed file saved to:")
print(processed_file_path)

print("\nETL completed successfully.")