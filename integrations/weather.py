import requests


def get_weather(city: str = "Zurich") -> dict:
    """Get weather via wttr.in — completely free, no API key needed."""
    try:
        url = f"https://wttr.in/{city}?format=j1&lang=de"
        r = requests.get(url, timeout=8)
        data = r.json()
        current = data["current_condition"][0]
        today = data["weather"][0]

        return {
            "city": city,
            "temp_c": current["temp_C"],
            "feels_like": current["FeelsLikeC"],
            "description": current["lang_de"][0]["value"],
            "humidity": current["humidity"],
            "wind_kmh": current["windspeedKmph"],
            "max_temp": today["maxtempC"],
            "min_temp": today["mintempC"],
            "sunrise": today["astronomy"][0]["sunrise"],
            "sunset": today["astronomy"][0]["sunset"],
        }
    except Exception as e:
        return {"error": str(e)}
