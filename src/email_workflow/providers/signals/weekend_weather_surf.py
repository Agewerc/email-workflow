"""Weekend weather + surf forecast provider."""

from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

import httpx

from email_workflow.schemas import (
    BeachConfig,
    ForecastPeriodStats,
    SurfSlotForecast,
    WeekendDayForecast,
    WeekendForecast,
    WeekendWeatherSurfWorkflowConfig,
)

WMO = {
    0: "Clear",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Rime fog",
    51: "Light drizzle",
    53: "Drizzle",
    55: "Dense drizzle",
    61: "Light rain",
    63: "Rain",
    65: "Heavy rain",
    71: "Light snow",
    80: "Rain showers",
    81: "Showers",
    82: "Heavy showers",
    95: "Thunderstorm",
}


class WeekendWeatherSurfProvider:
    """Fetch weather, marine, and optional surf rating data for a beach."""

    def __init__(self, timeout_seconds: int = 20) -> None:
        self.timeout_seconds = timeout_seconds

    def _fetch_json(self, client: httpx.Client, url: str, params: dict) -> dict:
        response = client.get(url, params=params, headers={"User-Agent": "email-workflow/weekend-weather-surf"})
        response.raise_for_status()
        return response.json()

    def _next_weekend_dates(self, today: dt.date) -> tuple[dt.date, dt.date]:
        days_ahead = (5 - today.weekday()) % 7
        saturday = today + dt.timedelta(days=days_ahead)
        sunday = saturday + dt.timedelta(days=1)
        return saturday, sunday

    def _rating_label(self, avg: float | None) -> str:
        if avg is None:
            return "n/a"
        if avg >= 4:
            return "Good"
        if avg >= 3:
            return "Fair"
        if avg >= 2:
            return "Poor to Fair"
        return "Poor"

    def _surfline_day_values(self, ratings: list[dict], target_day: dt.date, tz: ZoneInfo) -> list[float]:
        values: list[float] = []
        for rating in ratings:
            ts = dt.datetime.fromtimestamp(rating["timestamp"], tz)
            if ts.date() == target_day:
                values.append(float(rating["rating"]["value"]))
        return values

    def _surfline_timeslots(self, ratings: list[dict], target_day: dt.date, tz: ZoneInfo, hours: tuple[int, ...] = (6, 9, 12, 15, 18)) -> list[SurfSlotForecast]:
        by_hour: dict[int, float] = {}
        for rating in ratings:
            ts = dt.datetime.fromtimestamp(rating["timestamp"], tz)
            if ts.date() == target_day:
                by_hour[ts.hour] = float(rating["rating"]["value"])
        return [SurfSlotForecast(hour=hour, rating=by_hour.get(hour)) for hour in hours]

    def _period_stats_for_day(
        self,
        hour_times: list[dt.datetime],
        weather_hourly: dict,
        target_day: dt.date,
        start_h: int,
        end_h: int,
    ) -> ForecastPeriodStats | None:
        values: list[tuple[float, float, float]] = []
        for index, timestamp in enumerate(hour_times):
            if timestamp.date() == target_day and start_h <= timestamp.hour <= end_h:
                values.append(
                    (
                        float(weather_hourly["windspeed_10m"][index]),
                        float(weather_hourly["precipitation_probability"][index]),
                        float(weather_hourly["precipitation"][index]),
                    )
                )
        if not values:
            return None
        return ForecastPeriodStats(
            wind_avg_kmh=sum(value[0] for value in values) / len(values),
            wind_max_kmh=max(value[0] for value in values),
            rain_probability_max=max(value[1] for value in values),
            rain_mm=sum(value[2] for value in values),
        )

    def _practical_note(self, day: WeekendDayForecast) -> str:
        if day.morning is None:
            return "Forecast is incomplete for the key morning window."
        if day.surf_rating_avg is not None and day.surf_rating_avg >= 3 and day.morning.wind_avg_kmh <= 20:
            return "Worth a surf if you can get out early before the wind builds."
        if day.morning.wind_avg_kmh <= 15 and day.rain_probability_day <= 20:
            return "Best for a clean early beach session, even if surf quality is only moderate."
        if day.morning.wind_avg_kmh >= 25 or day.rain_probability_day >= 60:
            return "Probably not worth forcing a surf unless conditions improve late."
        return "Check the morning window; conditions look mixed rather than clearly good or bad."

    def fetch_forecast(self, config: WeekendWeatherSurfWorkflowConfig) -> WeekendForecast:
        beach: BeachConfig = config.beach
        tz = ZoneInfo(config.timezone)
        with httpx.Client(timeout=self.timeout_seconds, follow_redirects=True) as client:
            weather = self._fetch_json(
                client,
                "https://api.open-meteo.com/v1/forecast",
                {
                    "latitude": beach.latitude,
                    "longitude": beach.longitude,
                    "daily": "weathercode,temperature_2m_max,temperature_2m_min,precipitation_probability_max,windspeed_10m_max",
                    "hourly": "windspeed_10m,precipitation_probability,precipitation",
                    "timezone": config.timezone,
                    "forecast_days": config.forecast_days,
                },
            )
            marine = self._fetch_json(
                client,
                "https://marine-api.open-meteo.com/v1/marine",
                {
                    "latitude": beach.latitude,
                    "longitude": beach.longitude,
                    "daily": "wave_height_max,swell_wave_height_max,swell_wave_period_max",
                    "timezone": config.timezone,
                    "forecast_days": config.forecast_days,
                },
            )
            surfline_ratings: list[dict] = []
            if beach.surfline_spot_id:
                try:
                    surfline = self._fetch_json(
                        client,
                        "https://services.surfline.com/kbyg/spots/forecasts/rating",
                        {"spotId": beach.surfline_spot_id, "days": 4, "intervalHours": 1},
                    )
                    surfline_ratings = surfline.get("data", {}).get("rating", [])
                except httpx.HTTPError:
                    surfline_ratings = []

        today = dt.datetime.now(tz).date()
        saturday, sunday = self._next_weekend_dates(today)
        daily_dates = [dt.date.fromisoformat(day) for day in weather["daily"]["time"]]
        date_index = {day: index for index, day in enumerate(daily_dates)}
        if saturday not in date_index or sunday not in date_index:
            raise RuntimeError("Weekend forecast window is not available in the upstream source yet.")

        hour_times = [dt.datetime.fromisoformat(timestamp).replace(tzinfo=tz) for timestamp in weather["hourly"]["time"]]

        day_forecasts: list[WeekendDayForecast] = []
        for target_day in [saturday, sunday]:
            index = date_index[target_day]
            day_ratings = self._surfline_day_values(surfline_ratings, target_day, tz)
            rating_avg = sum(day_ratings) / len(day_ratings) if day_ratings else None
            morning = self._period_stats_for_day(hour_times, weather["hourly"], target_day, 6, 11)
            afternoon = self._period_stats_for_day(hour_times, weather["hourly"], target_day, 12, 18)
            day = WeekendDayForecast(
                iso_date=target_day.isoformat(),
                label=target_day.strftime("%A %d %b"),
                weather_desc=WMO.get(weather["daily"]["weathercode"][index], "Unknown"),
                tmin_c=float(weather["daily"]["temperature_2m_min"][index]),
                tmax_c=float(weather["daily"]["temperature_2m_max"][index]),
                rain_probability_day=float(weather["daily"]["precipitation_probability_max"][index]),
                wind_max_day_kmh=float(weather["daily"]["windspeed_10m_max"][index]),
                wave_height_m=float(marine["daily"]["wave_height_max"][index]),
                swell_height_m=float(marine["daily"]["swell_wave_height_max"][index]),
                swell_period_s=float(marine["daily"]["swell_wave_period_max"][index]),
                surf_rating_avg=rating_avg,
                surf_rating_label=self._rating_label(rating_avg),
                morning=morning,
                afternoon=afternoon,
                surf_slots=self._surfline_timeslots(surfline_ratings, target_day, tz),
            )
            day.practical_note = self._practical_note(day)
            day_forecasts.append(day)

        saturday_forecast, sunday_forecast = day_forecasts
        morning_winner = saturday_forecast if (
            sunday_forecast.morning is None
            or (saturday_forecast.morning and saturday_forecast.morning.wind_avg_kmh <= sunday_forecast.morning.wind_avg_kmh)
        ) else sunday_forecast
        surf_winner = saturday_forecast if (
            (saturday_forecast.surf_rating_avg or 0.0) >= (sunday_forecast.surf_rating_avg or 0.0)
        ) else sunday_forecast
        best_day = surf_winner.label if (surf_winner.surf_rating_avg or 0.0) >= 2.5 else morning_winner.label
        best_window = f"{best_day} early morning (06:00-09:00)"
        headline = f"{best_day} looks like the strongest {beach.name} window for the weekend."

        summary = [
            f"Best surf shot: {best_window}.",
            f"Calmer morning winds favor {morning_winner.label}.",
            f"Best-rated surf outlook favors {surf_winner.label} ({surf_winner.surf_rating_label}).",
        ]
        if saturday_forecast.afternoon and sunday_forecast.afternoon:
            windier = saturday_forecast if saturday_forecast.afternoon.wind_avg_kmh >= sunday_forecast.afternoon.wind_avg_kmh else sunday_forecast
            summary.append(f"Expect the windiest afternoon on {windier.label}.")

        practical_note = (
            f"If you only pick one session, target {best_window}; "
            f"backup day is {morning_winner.label if best_day != morning_winner.label else sunday_forecast.label}."
        )
        source_notes = [
            f"Weather + marine forecast: {config.weather_source_label}",
            f"Surf quality rating: {config.surf_source_label if beach.surfline_spot_id else 'Surfline unavailable for this beach'}",
        ]
        return WeekendForecast(
            workflow_name="Weekend Weather + Surf",
            beach_slug=beach.slug,
            beach_name=beach.name,
            timezone=config.timezone,
            generated_at=dt.datetime.now(tz).strftime("%a %d %b %Y %H:%M (%Z)"),
            summary=summary,
            headline=headline,
            best_day=best_day,
            best_window=best_window,
            practical_note=practical_note,
            schedule_note=f"{config.schedule_day} {config.schedule_time} ({config.schedule_timezone})",
            source_notes=source_notes,
            days=day_forecasts,
        )
