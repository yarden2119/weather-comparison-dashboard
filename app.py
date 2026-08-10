from pathlib import Path

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

from weather_etl import fetch_dynamic_city_history

DATA_FILE = Path("data/processed/weather_2021_2025.csv")
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"

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

TRAVEL_MIN_TEMP_C = 18
TRAVEL_MAX_TEMP_C = 28
TRAVEL_MAX_PRECIPITATION_MM = 1
TRAVEL_MAX_WIND_KMH = 25

st.set_page_config(
    page_title="Travel Weather Planner",
    page_icon="✈️",
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

    return df

def search_city(city_name):

    params = {
        "name": city_name,
        "count": 5,
        "language": "en",
        "format": "json"
    }

    response = requests.get(
        GEOCODING_URL,
        params=params,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    return data.get("results", [])


weather_df = load_weather_data()

# אם המשתמש כבר הוסיף עיר חדשה במהלך השימוש באפליקציה,
# הנתונים שלה נשמרו ב-session_state תחת המפתח dynamic_city_data
if "dynamic_city_data" in st.session_state:

    # חיבור הנתונים של העיר החדשה לנתונים הקבועים
    # שכבר נטענו מה-CSV
    weather_df = pd.concat(
        [
            weather_df,
            st.session_state["dynamic_city_data"]
        ],
        ignore_index=True
    )

# חישוב המדדים הבוליאניים אחרי חיבור כל מקורות הנתונים,
# כדי שאותה לוגיקה תחול גם על הערים הקבועות וגם על ערים דינמיות

weather_df["is_rainy_day"] = (
    weather_df["precipitation_mm"] > 0
)

weather_df["is_travel_friendly_day"] = (
    weather_df["average_temperature_c"].between(
        TRAVEL_MIN_TEMP_C,
        TRAVEL_MAX_TEMP_C
    )
    & (
        weather_df["precipitation_mm"]
        < TRAVEL_MAX_PRECIPITATION_MM
    )
    & (
        weather_df["max_wind_speed_kmh"]
        < TRAVEL_MAX_WIND_KMH
    )
)

st.title("✈️ Travel Weather Planner🌤️")

st.markdown(
    """
    <div dir="rtl" style="text-align: right;">
        מתכננים טיול? השוו בין יעדים, בדקו את דפוסי מזג האוויר
        לאורך השנה וגלו מתי הכי נעים לבקר.
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown(
    f"""
    <div dir="rtl" style="
        text-align: right;
        background-color: rgba(28, 131, 225, 0.12);
        padding: 16px;
        border-radius: 8px;
        margin-top: 10px;
        margin-bottom: 20px;
    ">
        💡 <strong>איך מוגדר יום נוח לטיול?</strong><br>
        יום שבו הטמפרטורה הממוצעת היא בין
        {TRAVEL_MIN_TEMP_C}°C ל־{TRAVEL_MAX_TEMP_C}°C,
        כמות המשקעים נמוכה מ־{TRAVEL_MAX_PRECIPITATION_MM} מ״מ
        ומהירות הרוח נמוכה מ־{TRAVEL_MAX_WIND_KMH} קמ״ש.
    </div>
    """,
    unsafe_allow_html=True
)

# --------------------------------------------------
# פונקציות RTL
# --------------------------------------------------

def rtl_text( container, text, tag="div", align="right", style=""):
    container.markdown(
        f"""
        <{tag} dir="rtl"
        style="text-align: {align}; {style}">
            {text}
        </{tag}>
        """,
        unsafe_allow_html=True
    )


def rtl_subheader(text):
    rtl_text(
        st,
        text,
        tag="h2",
        align="right"
    )


def rtl_caption(container, text):
    rtl_text(
        container,
        text,
        align="left",
        style="color: gray; font-size: 14px;"
    )

# --------------------------------------------------
# סרגל סינון
# --------------------------------------------------

st.sidebar.markdown(
    """
    <h3 dir="rtl" style="text-align: right;">
       תכנון הנסיעה
    </h3>
    """,
    unsafe_allow_html=True
)

available_cities = sorted(
    weather_df["city"].unique()
)

selected_cities = st.sidebar.multiselect(
    "אילו יעדים מעניינים אתכם?",
    options=available_cities,
    default=available_cities
)

with st.sidebar.expander("➕ הוספת יעד אחר"):

    city_query = st.text_input(
        "הקלידו שם עיר",
        placeholder="לדוגמה: Paris"
    )

    if st.button("חיפוש עיר"):

        if len(city_query.strip()) < 3:
            st.warning("יש להקליד לפחות 3 תווים.")

        else:
            try:
                search_results = search_city(
                    city_query.strip()
                )

                st.session_state["city_search_results"] = (
                    search_results
                )

            except requests.RequestException:
                st.error(
                    "לא ניתן היה לבצע את החיפוש."
                )
    if "city_search_results" in st.session_state:

        search_results = st.session_state[
            "city_search_results"
        ]

        if not search_results:
            st.info("לא נמצאו ערים מתאימות.")

        else:

            city_options = {}
                
            for result in search_results:

                city_label = (
                    f"{result.get('name', '')}, "
                    f"{result.get('admin1', '')}, "
                    f"{result.get('country', '')}"
                )

                city_options[city_label] = result

            selected_city_label = st.selectbox(
                "בחרו את העיר המתאימה",
                list(city_options.keys())
            )

            selected_city_result = city_options[
                selected_city_label
            ] 

            # שם קצר יותר להצגה בדשבורד
            dynamic_city_name = selected_city_result["name"]

            # כאשר המשתמש לוחץ על הכפתור,
            # נמשוך את נתוני מזג האוויר ההיסטוריים של העיר שבחר
            if st.button("הוספה להשוואה"):

                try:
                    dynamic_city_df = fetch_dynamic_city_history(
                        city_name=dynamic_city_name,
                        latitude=selected_city_result["latitude"],
                        longitude=selected_city_result["longitude"]
                    )

                    # אם כבר נוספה בעבר עיר דינמית,
                    # נחבר את העיר החדשה לנתונים שכבר שמורים ב-session_state
                    if "dynamic_city_data" in st.session_state:

                        combined_dynamic_data = pd.concat(
                            [
                                st.session_state["dynamic_city_data"],
                                dynamic_city_df
                            ],
                            ignore_index=True
                        )

                        # מניעת כפילות אם המשתמש מוסיף שוב את אותה עיר
                        combined_dynamic_data = combined_dynamic_data.drop_duplicates(
                            subset=["city", "date"]
                        ).reset_index(drop=True)

                        st.session_state["dynamic_city_data"] = (
                            combined_dynamic_data
                        )

                    # אם זו העיר הדינמית הראשונה שנוספה,
                    # ניצור את המפתח dynamic_city_data ונשמור בו את הדאטה
                    else:
                        st.session_state["dynamic_city_data"] = (
                            dynamic_city_df
                        )

                    # הרצה מחדש של האפליקציה כדי שהעיר החדשה
                    # תיכנס ל-weather_df ותופיע ברשימת היעדים
                    st.rerun()

                except requests.RequestException:
                    st.error(
                        "לא ניתן היה להוריד את נתוני מזג האוויר עבור העיר."
                    )

selected_months = st.sidebar.multiselect(
    "באילו חודשים אתם שוקלים לטייל?",
    options=list(MONTH_NAMES.keys()),
    default=list(MONTH_NAMES.keys()),
    format_func=lambda month: MONTH_NAMES[month]
)


if not selected_cities:
    st.warning("יש לבחור לפחות עיר אחת.")
    st.stop()

if not selected_months:
    st.warning("יש לבחור לפחות חודש אחד.")
    st.stop()



filtered_df = weather_df[
    weather_df["city"].isin(selected_cities)
    & weather_df["month"].isin(selected_months)
].copy()


if filtered_df.empty:
    st.warning("לא נמצאו נתונים עבור הסינון שנבחר.")
    st.stop()

yearly_selected_df = weather_df[
    weather_df["city"].isin(selected_cities)
].copy()

yearly_selected_df["month"] = (
    yearly_selected_df["date"].dt.month
)

yearly_monthly_df = (
    yearly_selected_df
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
        travel_friendly_days=(
            "is_travel_friendly_day",
            "sum"
        ),
        total_days=(
            "date",
            "count"
        )
    )
)

yearly_monthly_df["travel_friendly_percent"] = (
    yearly_monthly_df["travel_friendly_days"]
    / yearly_monthly_df["total_days"]
    * 100
).round(1)

precipitation_by_year_month = (
    yearly_selected_df
    .groupby(
        ["city", "year", "month"],
        as_index=False
    )
    .agg(
        total_precipitation_mm=(
            "precipitation_mm",
            "sum"
        )
    )
)

average_monthly_precipitation = (
    precipitation_by_year_month
    .groupby(
        ["city", "month"],
        as_index=False
    )
    .agg(
        average_monthly_precipitation_mm=(
            "total_precipitation_mm",
            "mean"
        )
    )
)

average_monthly_precipitation[
    "average_monthly_precipitation_mm"
] = (
    average_monthly_precipitation[
        "average_monthly_precipitation_mm"
    ].round(1)
)

city_comparison = (
    filtered_df
    .groupby(
        "city",
        as_index=False
    )
    .agg(
        travel_friendly_days=(
            "is_travel_friendly_day",
            "sum"
        ),
        total_days=(
            "date",
            "count"
        ),
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


city_comparison["travel_friendly_percent"] = (
    city_comparison["travel_friendly_days"]
    / city_comparison["total_days"]
    * 100
).round(1)

city_comparison["rainy_day_percent"] = (
    city_comparison["rainy_days"]
    / city_comparison["total_days"]
    * 100
).round(1)

valid_stability_data = city_comparison.dropna(
    subset=["temperature_std_c"]
)

if not valid_stability_data.empty:
    most_stable_city = valid_stability_data.loc[
        valid_stability_data[
            "temperature_std_c"
        ].idxmin()
    ]
else:
    most_stable_city = None

# --------------------------------------------------
# יצירת סיכום חודשי לפי הסינון
# --------------------------------------------------


monthly_df = (
    filtered_df
    .groupby(
        ["city", "month"],
        as_index=False
    )
    .agg(
        rainy_days=(
            "is_rainy_day",
            "sum"
        ),
        travel_friendly_days=(
            "is_travel_friendly_day",
            "sum"
        ),
        total_days=(
            "date",
            "count"
        ),
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

monthly_df["travel_friendly_percent"] = (
    monthly_df["travel_friendly_days"]
    / monthly_df["total_days"]
    * 100
).round(1)

monthly_df["rainy_day_percent"] = (
    monthly_df["rainy_days"]
    / monthly_df["total_days"]
    * 100
).round(1)


# --------------------------------------------------
# סקירה מהירה
# --------------------------------------------------

rtl_subheader("סקירה מהירה")

metric_1, metric_2, metric_3, metric_4 = st.columns(4)


if len(selected_cities) == 1:

    # --------------------------------------------------
    # יעד אחד + חודש אחד
    # --------------------------------------------------

    if len(selected_months) == 1:

        selected_month = selected_months[0]

        selected_month_data = monthly_df.loc[
            monthly_df["month"] == selected_month
        ].iloc[0]

        precipitation_per_year = (
            filtered_df
            .groupby(
                "year",
                as_index=False
            )
            .agg(
                total_precipitation_mm=(
                    "precipitation_mm",
                    "sum"
                )
            )
        )

        average_precipitation_mm = (
            precipitation_per_year[
                "total_precipitation_mm"
            ].mean()
        )

        metric_1.metric(
            "טמפרטורה ממוצעת",
            f"{selected_month_data['average_temperature_c']:.1f} °C"
        )

        metric_2.metric(
            "ימים נוחים לטיול",
            f"{selected_month_data['travel_friendly_percent']:.0f}%"
        )

        metric_3.metric(
            "ימים גשומים",
            f"{selected_month_data['rainy_day_percent']:.0f}%"
        )

        metric_4.metric(
            "משקעים חודשיים ממוצעים",
            f"{average_precipitation_mm:.1f} מ״מ"
        )


    # --------------------------------------------------
    # יעד אחד + כמה חודשים
    # --------------------------------------------------

    else:

        best_month = monthly_df.loc[
            monthly_df[
                "travel_friendly_percent"
            ].idxmax()
        ]

        driest_month = monthly_df.loc[
            monthly_df[
                "rainy_day_percent"
            ].idxmin()
        ]

        warmest_month = monthly_df.loc[
            monthly_df[
                "average_temperature_c"
            ].idxmax()
        ]

        rainiest_month = monthly_df.loc[
            monthly_df[
                "rainy_day_percent"
            ].idxmax()
        ]

        metric_1.metric(
            "החודש המומלץ",
            best_month["month_name"]
        )

        rtl_caption(
            metric_1,
            f"{best_month['travel_friendly_percent']:.0f}% ימים נוחים"
        )

        metric_2.metric(
            "החודש היבש ביותר",
            driest_month["month_name"]
        )

        rtl_caption(
            metric_2,
            f"{driest_month['rainy_day_percent']:.0f}% ימים גשומים"
        )

        metric_3.metric(
            "החודש החם ביותר",
            warmest_month["month_name"]
        )

        rtl_caption(
            metric_3,
            f"{warmest_month['average_temperature_c']:.1f}°C בממוצע"
        )

        metric_4.metric(
            "החודש הגשום ביותר",
            rainiest_month["month_name"]
        )

        rtl_caption(
            metric_4,
            f"{rainiest_month['rainy_day_percent']:.0f}% ימים גשומים"
        )

else:

    most_travel_friendly_city = city_comparison.loc[
        city_comparison[
            "travel_friendly_percent"
        ].idxmax()
    ]

    driest_city = city_comparison.loc[
        city_comparison[
            "rainy_day_percent"
        ].idxmin()
    ]

    warmest_city = city_comparison.loc[
        city_comparison[
            "average_temperature_c"
        ].idxmax()
    ]

    metric_1.metric(
    "הכי הרבה ימים נוחים",
    most_travel_friendly_city["city"]
    )

    rtl_caption(
    metric_1,
    f"{most_travel_friendly_city['travel_friendly_percent']:.0f}% מהימים"
    )

    metric_2.metric(
    "היעד היבש ביותר",
    driest_city["city"]
    )

    rtl_caption(
    metric_2,
    f"{driest_city['rainy_day_percent']:.0f}% ימי גשם"
    )


    if most_stable_city is not None:

        metric_3.metric(
            "מזג האוויר היציב ביותר",
            most_stable_city["city"]
        )

        rtl_caption(
            metric_3,
            f"סטיית תקן {most_stable_city['temperature_std_c']:.1f}°C"
        )

    else:

        metric_3.metric(
            "מזג האוויר היציב ביותר",
            "לא ניתן לחשב"
        )

        rtl_caption(
            metric_3,
            "נדרשים לפחות יומיים"
        )


    metric_4.metric(
    "היעד החם ביותר",
    warmest_city["city"]
    )

    rtl_caption(
    metric_4,
    f"טמפרטורה ממוצעת {warmest_city['average_temperature_c']:.1f}°C"
    ) 

# --------------------------------------------------
# המלצות למטייל
# --------------------------------------------------

rtl_subheader("מה כדאי לדעת לפני שמזמינים?")


if len(selected_cities) == 1:

    city_name = selected_cities[0]

    # --------------------------------------------------
    # יעד אחד + חודש אחד
    # --------------------------------------------------

    if len(selected_months) == 1:

        selected_month = selected_months[0]

        selected_month_data = monthly_df.loc[
            monthly_df["month"] == selected_month
        ].iloc[0]

        precipitation_per_year = (
            filtered_df
            .groupby(
                "year",
                as_index=False
            )
            .agg(
                total_precipitation_mm=(
                    "precipitation_mm",
                    "sum"
                )
            )
        )

        average_precipitation_mm = (
            precipitation_per_year[
                "total_precipitation_mm"
            ].mean()
        )

        st.html(
            f"""
            <div dir="rtl" style="text-align: right;">
                <ul>
                    <li>
                        ב־
                        <strong>{MONTH_NAMES[selected_month]}</strong>,
                        הטמפרטורה הממוצעת ב־
                        <bdi dir="ltr"><strong>{city_name}</strong></bdi>
                        הייתה
                        <bdi dir="ltr">
                            <strong>{selected_month_data['average_temperature_c']:.1f}°C</strong>
                        </bdi>.
                    </li>

                    <li>
                        <strong>{selected_month_data['travel_friendly_percent']:.0f}%</strong>
                        מהימים בחודש זה עמדו בתנאים שהוגדרו כנוחים לטיול.
                    </li>

                    <li>
                        ב־
                        <strong>{selected_month_data['rainy_day_percent']:.0f}%</strong>
                        מהימים נמדדו משקעים.
                    </li>

                    <li>
                        כמות המשקעים החודשית הממוצעת הייתה
                        <strong>{average_precipitation_mm:.1f} מ"מ</strong>,
                        על בסיס השנים 2021–2025.
                    </li>
                </ul>
            </div>
            """
        )


    # --------------------------------------------------
    # יעד אחד + כמה חודשים
    # --------------------------------------------------

    else:

        best_month = monthly_df.loc[
            monthly_df[
                "travel_friendly_percent"
            ].idxmax()
        ]

        driest_month = monthly_df.loc[
            monthly_df[
                "rainy_day_percent"
            ].idxmin()
        ]

        warmest_month = monthly_df.loc[
            monthly_df[
                "average_temperature_c"
            ].idxmax()
        ]

        rainiest_month = monthly_df.loc[
            monthly_df[
                "rainy_day_percent"
            ].idxmax()
        ]

        st.html(
            f"""
            <div dir="rtl" style="text-align: right;">
                <ul>
                    <li>
                        מבין החודשים שנבחרו,
                        <strong>{best_month['month_name']}</strong>
                        הוא החודש המומלץ ביותר,
                        עם
                        <strong>{best_month['travel_friendly_percent']:.0f}%</strong>
                        ימים נוחים לטיול.
                    </li>

                    <li>
                        <strong>{driest_month['month_name']}</strong>
                        הוא החודש היבש ביותר,
                        עם
                        <strong>{driest_month['rainy_day_percent']:.0f}%</strong>
                        ימים גשומים.
                    </li>

                    <li>
                        <strong>{warmest_month['month_name']}</strong>
                        הוא החודש החם ביותר מבין הבחירות,
                        עם טמפרטורה ממוצעת של
                        <bdi dir="ltr">
                            <strong>{warmest_month['average_temperature_c']:.1f}°C</strong>
                        </bdi>.
                    </li>

                    <li>
                        <strong>{rainiest_month['month_name']}</strong>
                        הוא החודש הגשום ביותר,
                        עם
                        <strong>{rainiest_month['rainy_day_percent']:.0f}%</strong>
                        ימים גשומים.
                    </li>
                </ul>
            </div>
            """
        )


else:

    most_travel_friendly_city = city_comparison.loc[
        city_comparison[
            "travel_friendly_percent"
        ].idxmax()
    ]

    driest_city = city_comparison.loc[
        city_comparison[
            "rainy_day_percent"
        ].idxmin()
    ]

    if most_stable_city is not None:

        stability_insight = f"""
        <li>
            <bdi dir="ltr">
                <strong>{most_stable_city['city']}</strong>
            </bdi>
            הציגה את מזג האוויר היציב ביותר מבחינת טמפרטורה,
            עם סטיית תקן של
            <bdi dir="ltr">
                <strong>{most_stable_city['temperature_std_c']:.1f}°C</strong>
            </bdi>.
        </li>
        """

    else:

        stability_insight = """
        <li>
            לא ניתן להשוות יציבות בטמפרטורה עבור יום בודד.
        </li>
        """

    st.html(
        f"""<div dir="rtl" style="text-align: right;">
    <ul>
        <li>
             מבין היעדים שנבחרו,
            <bdi dir="ltr"><strong>{most_travel_friendly_city['city']}</strong></bdi>
             מציעה את שיעור הימים הנוחים הגבוה ביותר:
            <strong>{most_travel_friendly_city['travel_friendly_percent']:.0f}%</strong>.
        </li>

        <li>
            <bdi dir="ltr"><strong>{driest_city['city']}</strong></bdi>
            היא היעד היבש ביותר בתקופה שנבחרה,
            עם
            <strong>{driest_city['rainy_day_percent']:.0f}%</strong>
            ימים גשומים.
        </li>

        {stability_insight}

        <li>
            להשוואת התקופות המומלצות בכל יעד,
            ניתן להיעזר בגרף
            <strong>"באילו חודשים הכי נעים לטייל?"</strong>.
        </li>
    </ul>
    </div>"""
    )

    
# --------------------------------------------------
# גרף 1: טמפרטורה חודשית ממוצעת
# --------------------------------------------------

rtl_subheader("איך הטמפרטורה משתנה לאורך השנה?")

temperature_chart = px.line(
    yearly_monthly_df,
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

rtl_subheader("באילו חודשים צפוי להיות גשום יותר?")

precipitation_chart = px.bar(
    average_monthly_precipitation,
    x="month",
    y="average_monthly_precipitation_mm",
    color="city",
    barmode="group",
    labels={
        "month": "חודש",
        "average_monthly_precipitation_mm": "משקעים חודשיים ממוצעים (מ״מ)",
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
# גרף 3: אחוז ימים נוחים לטיול לפי חודש
# --------------------------------------------------

rtl_subheader("באילו חודשים הכי נעים לטייל?")

travel_chart = px.line(
    yearly_monthly_df,
    x="month",
    y="travel_friendly_percent",
    color="city",
    markers=True,
    labels={
        "month": "חודש",
        "travel_friendly_percent": "ימים נוחים לטיול (%)",
        "city": "יעד"
    }
)

travel_chart.update_xaxes(
    tickmode="array",
    tickvals=list(MONTH_NAMES.keys()),
    ticktext=list(MONTH_NAMES.values())
)

travel_chart.update_yaxes(
    range=[0, 100]
)

st.plotly_chart(
    travel_chart,
    use_container_width=True
)

# --------------------------------------------------
# טבלת הנתונים
# --------------------------------------------------

rtl_subheader("הנתונים מאחורי ההמלצה")

display_df = filtered_df[
    [
        "date",
        "city",
        "max_temperature_c",
        "min_temperature_c",
        "average_temperature_c",
        "precipitation_mm",
        "max_wind_speed_kmh"
    ]
].copy()

display_df["date"] = (
    display_df["date"].dt.strftime("%d/%m/%Y")
)

display_df = display_df.rename(
    columns={
        "date": "תאריך",
        "city": "יעד",
        "max_temperature_c": "טמפ׳ מקסימלית (°C)",
        "min_temperature_c": "טמפ׳ מינימלית (°C)",
        "average_temperature_c": "טמפ׳ ממוצעת (°C)",
        "precipitation_mm": "משקעים (מ״מ)",
        "max_wind_speed_kmh": "רוח מקסימלית (קמ״ש)"
    }
)

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True
)


st.caption(
    "Weather data source: Open-Meteo Historical Weather API"
)