from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


DATA_FILE = Path("data/processed/weather_2025.csv")

MONTH_NAMES = {
    1: "ינואר",
    2: "פברואר",
    3: "מרץ",
    4: "אפריל",
    5: "מאי",
    6: "יוני",
    7: "יולי",
    8: "אוגוסט",
    9: "ספטמבר",
    10: "אוקטובר",
    11: "נובמבר",
    12: "דצמבר"
}


st.set_page_config(
    page_title="Weather Comparison Dashboard",
    page_icon="🌤️",
    layout="wide"
)


@st.cache_data
def load_weather_data():
    """
    טוענת את קובץ הנתונים המעובד.
    הפונקציה נשמרת בזיכרון המטמון של Streamlit,
    כדי שלא לקרוא מחדש את הקובץ בכל אינטראקציה.
    """

    if not DATA_FILE.exists():
        raise FileNotFoundError(
            "Processed data file was not found. "
            "Run weather_etl.py first."
        )

    df = pd.read_csv(
        DATA_FILE,
        parse_dates=["date"]
    )

    # יצירה מחדש של העמודה כדי לוודא שהיא בוליאנית
    df["is_rainy_day"] = (
        df["precipitation_mm"] > 0
    )

    return df


weather_df = load_weather_data()


st.title("🌤️ Weather Comparison Dashboard")

st.write(
    """
    השוואת נתוני מזג אוויר היסטוריים בין תל אביב,
    ניו יורק, לונדון ובנגקוק במהלך שנת 2025.
    """
)

def rtl_subheader(text):
    st.markdown(
        f"""
        <h2 dir="rtl" style="text-align: right;">
            {text}
        </h2>
        """,
        unsafe_allow_html=True
    )
# --------------------------------------------------
# סרגל סינון
# --------------------------------------------------

st.sidebar.markdown(
    """
    <h3 dir="rtl" style="text-align: right;">
        סינון הנתונים
    </h3>
    """,
    unsafe_allow_html=True
)

available_cities = sorted(
    weather_df["city"].unique()
)

selected_cities = st.sidebar.multiselect(
    "בחרי ערים:",
    options=available_cities,
    default=available_cities
)

minimum_date = weather_df["date"].min().date()
maximum_date = weather_df["date"].max().date()

selected_dates = st.sidebar.date_input(
    "בחרי טווח תאריכים:",
    value=(minimum_date, maximum_date),
    min_value=minimum_date,
    max_value=maximum_date
)


if not selected_cities:
    st.warning("יש לבחור לפחות עיר אחת.")
    st.stop()


if len(selected_dates) == 2:
    start_date = pd.Timestamp(selected_dates[0])
    end_date = pd.Timestamp(selected_dates[1])
else:
    start_date = pd.Timestamp(selected_dates[0])
    end_date = pd.Timestamp(selected_dates[0])


filtered_df = weather_df[
    weather_df["city"].isin(selected_cities)
    & weather_df["date"].between(
        start_date,
        end_date
    )
].copy()


if filtered_df.empty:
    st.warning("לא נמצאו נתונים עבור הסינון שנבחר.")
    st.stop()

city_comparison = (
    filtered_df
    .groupby(
        "city",
        as_index=False
    )
    .agg(
        lowest_temperature_c=(
            "min_temperature_c",
            "min"
        ),
        temperature_std_c=(
            "average_temperature_c",
            "std"
        ),
        average_temperature_c=(
            "average_temperature_c",
            "mean"
        ),
        highest_temperature_c=(
            "max_temperature_c",
            "max"
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
)
# --------------------------------------------------
# מדדים מרכזיים
# --------------------------------------------------

rtl_subheader("מדדים מרכזיים")

metric_1, metric_2, metric_3, metric_4 = st.columns(4)


if len(selected_cities) == 1:

    city_data = city_comparison.iloc[0]

    metric_1.metric(
        "טמפרטורה ממוצעת",
        f"{city_data['average_temperature_c']:.1f} °C"
    )

    metric_2.metric(
        "הטמפרטורה הגבוהה ביותר",
        f"{city_data['highest_temperature_c']:.1f} °C"
    )

    metric_3.metric(
        "סך המשקעים",
        f"{city_data['total_precipitation_mm']:.1f} מ״מ"
    )

    metric_4.metric(
        "ימים גשומים",
        f"{int(city_data['rainy_days'])}"
    )


else:

    warmest_city = city_comparison.loc[
        city_comparison["average_temperature_c"].idxmax()
    ]

    highest_temperature_city = city_comparison.loc[
        city_comparison["highest_temperature_c"].idxmax()
    ]

    wettest_city = city_comparison.loc[
        city_comparison["total_precipitation_mm"].idxmax()
    ]

    rainiest_city = city_comparison.loc[
        city_comparison["rainy_days"].idxmax()
    ]


    metric_1.metric(
        "העיר החמה בממוצע",
        warmest_city["city"],
        f"{warmest_city['average_temperature_c']:.1f} °C"
    )

    metric_2.metric(
        "הטמפרטורה הגבוהה ביותר",
        highest_temperature_city["city"],
        f"{highest_temperature_city['highest_temperature_c']:.1f} °C"
    )

    metric_3.metric(
        "העיר עם הכי הרבה משקעים",
        wettest_city["city"],
        f"{wettest_city['total_precipitation_mm']:.1f} מ״מ"
    )

    metric_4.metric(
        "העיר עם הכי הרבה ימי גשם",
        rainiest_city["city"],
        f"{int(rainiest_city['rainy_days'])} ימים"
    )


# --------------------------------------------------
# יצירת סיכום חודשי לפי הסינון
# --------------------------------------------------

filtered_df["month"] = (
    filtered_df["date"].dt.month
)

monthly_df = (
    filtered_df
    .groupby(
        ["city", "month"],
        as_index=False
    )
    .agg(
        average_temperature_c=(
            "average_temperature_c",
            "mean"
        ),
        total_precipitation_mm=(
            "precipitation_mm",
            "sum"
        ),
        strongest_wind_kmh=(
            "max_wind_speed_kmh",
            "max"
        )
    )
)

monthly_df["month_name"] = (
    monthly_df["month"].map(MONTH_NAMES)
)

# --------------------------------------------------
# סיכום מילולי דינמי
# --------------------------------------------------

rtl_subheader("מסקנות מרכזיות")


if len(selected_cities) == 1:

    city_name = selected_cities[0]

    city_data = city_comparison.iloc[0]

    warmest_month = monthly_df.loc[
        monthly_df[
            "average_temperature_c"
        ].idxmax()
    ]

    wettest_month = monthly_df.loc[
        monthly_df[
            "total_precipitation_mm"
        ].idxmax()
    ]

    st.markdown(
        f"""
        <div dir="rtl" style="text-align: right;">
            <ul>
                <li>
                    הטמפרטורה הממוצעת ב־
                    <bdi dir="ltr"><strong>{city_name}</strong></bdi>
                    בתקופה שנבחרה הייתה
                    <bdi dir="ltr"><strong>{city_data['average_temperature_c']:.1f}°C</strong></bdi>.
                </li>
                <li>
                    הטמפרטורה הגבוהה ביותר הייתה
                    <bdi dir="ltr"><strong>{city_data['highest_temperature_c']:.1f}°C</strong></bdi>,
                    והנמוכה ביותר הייתה
                    <bdi dir="ltr"><strong>{city_data['lowest_temperature_c']:.1f}°C</strong></bdi>.
                </li>
                <li>
                    החודש החם ביותר היה
                    <strong>{warmest_month['month_name']}</strong>,
                    עם טמפרטורה ממוצעת של
                    <bdi dir="ltr"><strong>{warmest_month['average_temperature_c']:.1f}°C</strong></bdi>.
                </li>
                <li>
                    החודש הגשום ביותר היה
                    <strong>{wettest_month['month_name']}</strong>,
                    עם
                    <bdi dir="ltr"><strong>{wettest_month['total_precipitation_mm']:.1f} מ"מ</strong></bdi>
                    משקעים.
                </li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True
    )


else:

    warmest_city = city_comparison.loc[
        city_comparison[
            "average_temperature_c"
        ].idxmax()
    ]

    coldest_city = city_comparison.loc[
        city_comparison[
            "average_temperature_c"
        ].idxmin()
    ]

    wettest_city = city_comparison.loc[
        city_comparison[
            "total_precipitation_mm"
        ].idxmax()
    ]

    most_variable_city = city_comparison.loc[
        city_comparison[
            "temperature_std_c"
        ].idxmax()
    ]
    st.markdown(
        f"""
        <div dir="rtl" style="text-align: right;">
            <ul>
                <li>
                    <bdi dir="ltr"><strong>{warmest_city['city']}</strong></bdi>
                    הייתה העיר החמה ביותר בממוצע, עם
                    <bdi dir="ltr"><strong>{warmest_city['average_temperature_c']:.1f}°C</strong></bdi>.
                </li>
                <li>
                    <bdi dir="ltr"><strong>{coldest_city['city']}</strong></bdi>
                    הייתה העיר הקרה ביותר בממוצע, עם
                    <bdi dir="ltr"><strong>{coldest_city['average_temperature_c']:.1f}°C</strong></bdi>.
                </li>
                <li>
                    <bdi dir="ltr"><strong>{wettest_city['city']}</strong></bdi>
                    קיבלה את כמות המשקעים הגבוהה ביותר:
                    <bdi dir="ltr"><strong>{wettest_city['total_precipitation_mm']:.1f} מ"מ</strong></bdi>.
                </li>
                <li>
                    <bdi dir="ltr"><strong>{most_variable_city['city']}</strong></bdi>
                    הציגה את התנודתיות הגדולה ביותר בטמפרטורה,
                    עם סטיית תקן של
                    <bdi dir="ltr"><strong>{most_variable_city['temperature_std_c']:.1f}°C</strong></bdi>.
                </li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True
    )
    
# --------------------------------------------------
# גרף 1: טמפרטורה חודשית ממוצעת
# --------------------------------------------------

rtl_subheader("טמפרטורה חודשית ממוצעת")

temperature_chart = px.line(
    monthly_df,
    x="month",
    y="average_temperature_c",
    color="city",
    markers=True,
    labels={
        "month": "חודש",
        "average_temperature_c":
            "טמפרטורה ממוצעת (°C)",
        "city": "עיר"
    }
)

temperature_chart.update_xaxes(
    tickmode="array",
    tickvals=list(MONTH_NAMES.keys()),
    ticktext=list(MONTH_NAMES.values())
)

st.plotly_chart(
    temperature_chart,
    use_container_width=True
)


# --------------------------------------------------
# גרף 2: משקעים חודשיים
# --------------------------------------------------

rtl_subheader("כמות משקעים חודשית")

precipitation_chart = px.bar(
    monthly_df,
    x="month",
    y="total_precipitation_mm",
    color="city",
    barmode="group",
    labels={
        "month": "חודש",
        "total_precipitation_mm":
            "סך משקעים (מ״מ)",
        "city": "עיר"
    }
)

precipitation_chart.update_xaxes(
    tickmode="array",
    tickvals=list(MONTH_NAMES.keys()),
    ticktext=list(MONTH_NAMES.values())
)

st.plotly_chart(
    precipitation_chart,
    use_container_width=True
)


# --------------------------------------------------
# גרף 3: התפלגות הטמפרטורות
# --------------------------------------------------

rtl_subheader("התפלגות הטמפרטורות היומיות")

temperature_distribution_chart = px.box(
    filtered_df,
    x="city",
    y="average_temperature_c",
    points=False,
    labels={
        "city": "עיר",
        "average_temperature_c":
            "טמפרטורה יומית ממוצעת (°C)"
    }
)

st.plotly_chart(
    temperature_distribution_chart,
    use_container_width=True
)


# --------------------------------------------------
# טבלת הנתונים
# --------------------------------------------------

rtl_subheader("הנתונים המסוננים")

display_columns = [
    "date",
    "city",
    "max_temperature_c",
    "min_temperature_c",
    "average_temperature_c",
    "precipitation_mm",
    "max_wind_speed_kmh"
]

st.dataframe(
    filtered_df[display_columns],
    use_container_width=True,
    hide_index=True
)


st.caption(
    "Weather data source: Open-Meteo Historical Weather API"
)