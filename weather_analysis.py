from pathlib import Path

import pandas as pd


# קובץ הנתונים שיצר תהליך ה-ETL
DATA_FILE = Path("data/processed/weather_2025.csv")

# תיקייה שבה נשמור את תוצאות הניתוח
OUTPUT_FOLDER = Path("outputs")
OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)


# בדיקה שהקובץ אכן קיים
if not DATA_FILE.exists():
    raise FileNotFoundError(
        "The processed weather file was not found. "
        "Run weather_etl.py first."
    )


# טעינת הנתונים והמרת עמודת התאריך
weather_df = pd.read_csv(
    DATA_FILE,
    parse_dates=["date"]
)


print("Weather data loaded successfully.")

print("\nDataFrame shape:")
print(weather_df.shape)


# --------------------------------------------------
# 1. סיכום שנתי לפי עיר
# --------------------------------------------------

city_summary = (
    weather_df
    .groupby(
        "city",
        as_index=False
    )
    .agg(
        average_temperature_c=(
            "average_temperature_c",
            "mean"
        ),
        highest_temperature_c=(
            "max_temperature_c",
            "max"
        ),
        lowest_temperature_c=(
            "min_temperature_c",
            "min"
        ),
        total_precipitation_mm=(
            "precipitation_mm",
            "sum"
        ),
        rainy_days=(
            "is_rainy_day",
            "sum"
        ),
        average_temperature_range_c=(
            "temperature_range_c",
            "mean"
        ),
        strongest_wind_kmh=(
            "max_wind_speed_kmh",
            "max"
        ),
        temperature_standard_deviation_c=(
            "average_temperature_c",
            "std"
        )
    )
)


# עיגול העמודות המספריות לספרה אחת
numeric_columns = city_summary.select_dtypes(
    include="number"
).columns

city_summary[numeric_columns] = (
    city_summary[numeric_columns].round(1)
)


# --------------------------------------------------
# 2. סיכום חודשי לפי עיר
# --------------------------------------------------

monthly_summary = (
    weather_df
    .groupby(
        [
            "city",
            "month",
            "month_name"
        ],
        as_index=False
    )
    .agg(
        monthly_average_temperature_c=(
            "average_temperature_c",
            "mean"
        ),
        monthly_max_temperature_c=(
            "max_temperature_c",
            "max"
        ),
        monthly_min_temperature_c=(
            "min_temperature_c",
            "min"
        ),
        total_precipitation_mm=(
            "precipitation_mm",
            "sum"
        ),
        rainy_days=(
            "is_rainy_day",
            "sum"
        ),
        strongest_wind_kmh=(
            "max_wind_speed_kmh",
            "max"
        )
    )
    .sort_values(
        by=["city", "month"]
    )
)


monthly_numeric_columns = (
    monthly_summary
    .select_dtypes(include="number")
    .columns
)

monthly_summary[monthly_numeric_columns] = (
    monthly_summary[
        monthly_numeric_columns
    ].round(1)
)


# --------------------------------------------------
# 3. היום החם ביותר בכל עיר
# --------------------------------------------------

hottest_days = weather_df.loc[
    weather_df
    .groupby("city")["max_temperature_c"]
    .idxmax(),
    [
        "city",
        "date",
        "max_temperature_c"
    ]
].copy()

hottest_days = hottest_days.rename(
    columns={
        "date": "hottest_date",
        "max_temperature_c":
            "highest_temperature_c"
    }
)


# --------------------------------------------------
# 4. היום הקר ביותר בכל עיר
# --------------------------------------------------

coldest_days = weather_df.loc[
    weather_df
    .groupby("city")["min_temperature_c"]
    .idxmin(),
    [
        "city",
        "date",
        "min_temperature_c"
    ]
].copy()

coldest_days = coldest_days.rename(
    columns={
        "date": "coldest_date",
        "min_temperature_c":
            "lowest_temperature_c"
    }
)


# חיבור ימי הקיצון לטבלה אחת
extreme_days = hottest_days.merge(
    coldest_days,
    on="city"
)


# --------------------------------------------------
# 5. מסקנות מרכזיות
# --------------------------------------------------

warmest_city = city_summary.loc[
    city_summary[
        "average_temperature_c"
    ].idxmax()
]

wettest_city = city_summary.loc[
    city_summary[
        "total_precipitation_mm"
    ].idxmax()
]

most_stable_city = city_summary.loc[
    city_summary[
        "temperature_standard_deviation_c"
    ].idxmin()
]


# --------------------------------------------------
# שמירת תוצאות הניתוח
# --------------------------------------------------

city_summary.to_csv(
    OUTPUT_FOLDER / "city_summary.csv",
    index=False,
    encoding="utf-8-sig"
)

monthly_summary.to_csv(
    OUTPUT_FOLDER / "monthly_summary.csv",
    index=False,
    encoding="utf-8-sig"
)

extreme_days.to_csv(
    OUTPUT_FOLDER / "extreme_days.csv",
    index=False,
    encoding="utf-8-sig"
)


# --------------------------------------------------
# הצגת התוצאות בטרמינל
# --------------------------------------------------

print("\nAnnual city summary:")
print(city_summary)

print("\nExtreme weather days:")
print(extreme_days)

print("\nMain findings:")

print(
    "Warmest city:",
    warmest_city["city"],
    "-",
    warmest_city["average_temperature_c"],
    "°C"
)

print(
    "Wettest city:",
    wettest_city["city"],
    "-",
    wettest_city["total_precipitation_mm"],
    "mm"
)

print(
    "Most stable temperature:",
    most_stable_city["city"],
    "- standard deviation:",
    most_stable_city[
        "temperature_standard_deviation_c"
    ],
    "°C"
)

print("\nAnalysis files saved in:")
print(OUTPUT_FOLDER)