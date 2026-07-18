import json
import urllib.request


def get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def get_browser_name(user_agent):
    if not user_agent:
        return "Unknown"

    user_agent = user_agent.lower()

    if "edg/" in user_agent:
        return "Edge"
    if "chrome" in user_agent:
        return "Chrome"
    if "firefox" in user_agent:
        return "Firefox"
    if "safari" in user_agent:
        return "Safari"
    if "opera" in user_agent:
        return "Opera"
    if "curl" in user_agent or "wget" in user_agent:
        return "CLI"

    return "Unknown"


def resolve_location(ip_address):
    if not ip_address or ip_address in {"127.0.0.1", "localhost", "::1"}:
        return "Local environment"

    try:
        with urllib.request.urlopen(
            f"https://ipapi.co/{ip_address}/json/",
            timeout=3,
        ) as response:
            payload = json.load(response)

        city = payload.get("city") or ""
        region = payload.get("region") or ""
        country = payload.get("country_name") or payload.get("country") or ""

        parts = [part for part in [city, region, country] if part]
        return ", ".join(parts) if parts else "Unknown"

    except Exception:
        return "Unknown"