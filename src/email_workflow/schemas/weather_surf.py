"""Schemas for deterministic weather + surf workflows."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SurfSlotForecast(BaseModel):
    hour: int
    rating: float | None = None


class ForecastPeriodStats(BaseModel):
    wind_avg_kmh: float
    wind_max_kmh: float
    rain_probability_max: float
    rain_mm: float


class WeekendDayForecast(BaseModel):
    iso_date: str
    label: str
    weather_desc: str
    tmin_c: float
    tmax_c: float
    rain_probability_day: float
    wind_max_day_kmh: float
    wave_height_m: float
    swell_height_m: float
    swell_period_s: float
    surf_rating_avg: float | None = None
    surf_rating_label: str = "n/a"
    morning: ForecastPeriodStats | None = None
    afternoon: ForecastPeriodStats | None = None
    surf_slots: list[SurfSlotForecast] = Field(default_factory=list)
    practical_note: str = ""


class WeekendForecast(BaseModel):
    workflow_name: str
    beach_slug: str
    beach_name: str
    timezone: str
    generated_at: str
    summary: list[str] = Field(default_factory=list)
    headline: str
    best_day: str
    best_window: str
    practical_note: str
    schedule_note: str
    source_notes: list[str] = Field(default_factory=list)
    days: list[WeekendDayForecast] = Field(default_factory=list)
