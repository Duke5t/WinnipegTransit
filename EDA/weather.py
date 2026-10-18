import openmeteo_requests
import requests_cache
import pandas as pd

from retry_requests import retry

# Open-Meteo API link
url = "https://archive-api.open-meteo.com/v1/archive"

# Coords Winnipeg
LATITUDE = 49.8951
LONGITUDE = -97.1384

# Set up with caching and retries
cache_session = requests_cache.CachedSession(
    ".cache",
    expire_after=-1
)
retry_session = retry(
    cache_session,
    retries=5,
    backoff_factor=1
)
openmeteo = openmeteo_requests.Client(
    session=retry_session
)


def get_weather_db(start_year=2021, end_year=2026):
    weather_df = []

    for year in range(int(start_year), int(end_year) + 1):
        print(f"API call for {year}")

        # Avoid requesting dates beyond today
        start_date = f"{year}-01-01"
        end_date = min(
            pd.Timestamp(f"{year}-12-31"),
            pd.Timestamp.today().normalize() - pd.Timedelta(days=1)
        ).strftime("%Y-%m-%d")

        if pd.Timestamp(start_date) > pd.Timestamp(end_date):
            continue

        params = {
            "latitude": LATITUDE,
            "longitude": LONGITUDE,
            "start_date": start_date,
            "end_date": end_date,
            "daily": [
                "temperature_2m_mean",
                "precipitation_sum",
                "rain_sum",
                "snowfall_sum"
            ],
            "timezone": "America/Winnipeg"
        }

        # Make API request
        responses = openmeteo.weather_api(url, params=params)
        response = responses[0]

        # Extract daily data
        daily = response.Daily()

        daily_data = {
            "date": pd.date_range(
                start=pd.to_datetime(daily.Time(), unit="s", utc=True),
                periods=daily.Variables(0).ValuesAsNumpy().size,
                freq="D"
            )
        }

        # Variable order matches the "daily" request above

        daily_data["temp_mean_C"] = (
            daily.Variables(0).ValuesAsNumpy().round(2)
        )
        daily_data["precip_sum_mm"] = (
            daily.Variables(1).ValuesAsNumpy().round(2)
        )
        daily_data["rain_sum_mm"] = (
            daily.Variables(2).ValuesAsNumpy().round(2)
        )
        daily_data["snowfall_sum_cm"] = (
            daily.Variables(3).ValuesAsNumpy().round(2)
        )

        df = pd.DataFrame(daily_data)

        df["date"] = pd.to_datetime(df["date"])
        df["year"] = df["date"].dt.year
        df["month"] = df["date"].dt.month
        df["day"] = df["date"].dt.day
        df.drop(columns=["date"], inplace=True)

        weather_df.append(df)

    if not weather_df:
        return pd.DataFrame()

    return pd.concat(weather_df, ignore_index=True)

from pathlib import Path
print(Path.cwd())

# winnipeg_weather = get_weather_db()

# save to CSV
# winnipeg_weather.to_csv(
#     "wpg_transit_weather.csv",
#     index=False
# )

# print(winnipeg_weather.head())
# print(f"Total daily records: {len(winnipeg_weather)}")
