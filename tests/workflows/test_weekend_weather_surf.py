from pathlib import Path

from email_workflow.engine.context import WorkflowContext
from email_workflow.schemas import AppSettings, WeekendForecast, WeekendDayForecast, ForecastPeriodStats, SurfSlotForecast, WorkflowCatalog, WorkflowDefinition
from email_workflow.workflows.weekend_weather_surf import WeekendWeatherSurfWorkflow


class DummyEmailProvider:
    def send_email(self, **kwargs):
        return True


class DummyGmailProvider:
    pass


class DummyLLMProvider:
    pass


class DummyWeekendForecastProvider:
    def fetch_forecast(self, config):
        return WeekendForecast(
            workflow_name="Weekend Weather + Surf",
            beach_slug="trigg",
            beach_name="Trigg Beach",
            timezone="Australia/Perth",
            generated_at="Thu 24 Apr 2026 18:00 (AWST)",
            summary=["Best surf shot is Saturday dawn.", "Sunday is cleaner on wind."],
            headline="Saturday looks like the strongest Trigg window.",
            best_day="Saturday 25 Apr",
            best_window="Saturday 25 Apr early morning (06:00-09:00)",
            practical_note="If you only surf once, go Saturday at dawn.",
            schedule_note="Thursday 18:00 (Australia/Perth)",
            source_notes=["Weather + marine forecast: Open-Meteo", "Surf quality rating: Surfline"],
            days=[
                WeekendDayForecast(
                    iso_date="2026-04-25",
                    label="Saturday 25 Apr",
                    weather_desc="Partly cloudy",
                    tmin_c=18,
                    tmax_c=27,
                    rain_probability_day=10,
                    wind_max_day_kmh=22,
                    wave_height_m=1.4,
                    swell_height_m=1.2,
                    swell_period_s=14,
                    surf_rating_avg=3.6,
                    surf_rating_label="Fair",
                    morning=ForecastPeriodStats(wind_avg_kmh=12, wind_max_kmh=18, rain_probability_max=10, rain_mm=0),
                    afternoon=ForecastPeriodStats(wind_avg_kmh=21, wind_max_kmh=25, rain_probability_max=20, rain_mm=0),
                    surf_slots=[SurfSlotForecast(hour=6, rating=4), SurfSlotForecast(hour=9, rating=3)],
                    practical_note="Worth a dawn surf.",
                ),
                WeekendDayForecast(
                    iso_date="2026-04-26",
                    label="Sunday 26 Apr",
                    weather_desc="Clear",
                    tmin_c=17,
                    tmax_c=26,
                    rain_probability_day=5,
                    wind_max_day_kmh=18,
                    wave_height_m=1.0,
                    swell_height_m=1.1,
                    swell_period_s=13,
                    surf_rating_avg=3.2,
                    surf_rating_label="Fair",
                    morning=ForecastPeriodStats(wind_avg_kmh=10, wind_max_kmh=14, rain_probability_max=5, rain_mm=0),
                    afternoon=ForecastPeriodStats(wind_avg_kmh=16, wind_max_kmh=18, rain_probability_max=10, rain_mm=0),
                    surf_slots=[SurfSlotForecast(hour=6, rating=3), SurfSlotForecast(hour=9, rating=3)],
                    practical_note="Cleaner weather but slightly softer surf.",
                ),
            ],
        )


def test_weekend_weather_surf_render_creates_artifacts(tmp_path: Path) -> None:
    definition = WorkflowDefinition(
        id="weekend-weather-surf-trigg",
        workflow_type="weekend_weather_surf",
        name="Weekend Weather + Surf (Trigg)",
        description="desc",
        config={
            "email_account": "test@example.com",
            "email_to": "test@example.com",
            "email_subject": "Weekend Weather + Surf Forecast — Trigg",
            "beach": {
                "slug": "trigg",
                "name": "Trigg Beach",
                "latitude": -31.87,
                "longitude": 115.756,
                "surfline_spot_id": "spot",
            },
            "timezone": "Australia/Perth",
            "template_html": "src/email_workflow/templates/weekend_weather_surf.html.j2",
            "template_text": "src/email_workflow/templates/weekend_weather_surf.txt.j2",
        },
    )
    ctx = WorkflowContext(
        settings=AppSettings(),
        catalog=WorkflowCatalog(workflows=[definition]),
        definition=definition,
        project_root=Path.cwd(),
        run_dir=tmp_path,
        prompt_dir=Path("config/prompts"),
        llm_provider=DummyLLMProvider(),
        email_provider=DummyEmailProvider(),
        gmail_provider=DummyGmailProvider(),
        weekend_forecast_provider=DummyWeekendForecastProvider(),
    )
    workflow = WeekendWeatherSurfWorkflow()
    result = workflow.run(ctx, dry_run=True)
    assert result.status.value == "success"
    assert (tmp_path / "forecast.json").exists()
    html = (tmp_path / "email.html").read_text(encoding="utf-8")
    text = (tmp_path / "email.txt").read_text(encoding="utf-8")
    assert "Trigg Beach" in html
    assert "Best window" in html
    assert "Saturday 25 Apr" in text
