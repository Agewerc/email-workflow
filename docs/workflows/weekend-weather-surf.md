# Weekend Weather + Surf

This workflow recreates the old Thursday evening Trigg forecast email inside the platform.

## First configured instance

- Workflow id: `weekend-weather-surf-trigg`
- Beach: Trigg Beach
- Intended schedule: Thursday 6:00 PM
- Timezone: Australia/Perth

## Data sources

- Open-Meteo forecast API for weather
- Open-Meteo marine API for wave and swell data
- Surfline rating API when a beach has a Surfline spot id configured

## Design notes

- The workflow type is generic: `weekend_weather_surf`
- Beach-specific values live in workflow config
- The current Trigg setup is the first instance and can be duplicated for beaches such as Mettams with only config changes
