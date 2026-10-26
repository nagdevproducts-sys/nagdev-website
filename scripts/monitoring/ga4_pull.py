import os
import sys
import json
from datetime import datetime, timezone
from pathlib import Path
from google.oauth2 import service_account
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest,
    DateRange,
    Dimension,
    Metric,
    OrderBy,
    FilterExpression,
    Filter
)

DEFAULT_PROPERTY_ID = "560496046"
OUTPUT_DIR = Path("monitoring_output")
OUTPUT_FILE = OUTPUT_DIR / "ga4_data.json"

AI_REFERRAL_SOURCES = [
    "chatgpt.com",
    "chat.openai.com",
    "perplexity.ai",
    "gemini.google.com",
    "copilot.microsoft.com",
    "claude.ai"
]

KEY_EVENT_NAMES = [
    "generate_lead",
    "sample_request",
    "whatsapp_click"
]

def get_client():
    sa_json = os.environ.get("GOOGLE_SA_JSON")
    if not sa_json:
        raise ValueError("Environment variable GOOGLE_SA_JSON is not set.")
    try:
        sa_info = json.loads(sa_json)
    except Exception as e:
        raise ValueError(f"Failed to parse GOOGLE_SA_JSON: {e}")

    credentials = service_account.Credentials.from_service_account_info(sa_info)
    return BetaAnalyticsDataClient(credentials=credentials)

def run_pull():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    property_id = os.environ.get("GA4_PROPERTY_ID", DEFAULT_PROPERTY_ID).strip()
    property_name = f"properties/{property_id}"
    
    out_data = {
        "status": "SUCCESS",
        "pulled_at": datetime.now(timezone.utc).isoformat(),
        "property_id": property_id,
        "channel_groups": {"current": {}, "previous": {}},
        "organic_sessions": {"current": 0, "previous": 0},
        "ai_referral_sessions": {"total": 0, "by_source": {}},
        "key_events": {
            "totals": {k: 0 for k in KEY_EVENT_NAMES},
            "by_landing_page": [],
            "tds_downloads": {"total": 0, "by_landing_page": []}
        },
        "top_countries": []
    }
    
    try:
        client = get_client()
    except Exception as e:
        out_data["status"] = "ERROR"
        out_data["error"] = str(e)
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(out_data, f, indent=2)
        print(f"GA4 pull client initialization failed: {e}")
        return out_data

    # 1. Channels for Current (28daysAgo to yesterday) and Previous (56daysAgo to 29daysAgo)
    try:
        print(f"Querying GA4 Channels for {property_name}...")
        req_channels = RunReportRequest(
            property=property_name,
            dimensions=[Dimension(name="sessionDefaultChannelGroup")],
            metrics=[Metric(name="sessions")],
            date_ranges=[
                DateRange(start_date="28daysAgo", end_date="yesterday", name="current_28d"),
                DateRange(start_date="56daysAgo", end_date="29daysAgo", name="previous_28d")
            ]
        )
        resp_channels = client.run_report(req_channels)
        for row in resp_channels.rows:
            channel = row.dimension_values[0].value
            # When multiple date ranges are queried, metric_values has an entry per date range
            curr_val = int(row.metric_values[0].value) if len(row.metric_values) > 0 else 0
            prev_val = int(row.metric_values[1].value) if len(row.metric_values) > 1 else 0
            out_data["channel_groups"]["current"][channel] = curr_val
            out_data["channel_groups"]["previous"][channel] = prev_val
            if channel == "Organic Search":
                out_data["organic_sessions"]["current"] = curr_val
                out_data["organic_sessions"]["previous"] = prev_val
    except Exception as e:
        print(f"Error querying channels: {e}", file=sys.stderr)
        out_data["channel_groups"]["error"] = str(e)

    # 2. AI Referrals
    try:
        print("Querying GA4 Sources for AI referrals...")
        req_sources = RunReportRequest(
            property=property_name,
            dimensions=[Dimension(name="sessionSource")],
            metrics=[Metric(name="sessions")],
            date_ranges=[DateRange(start_date="28daysAgo", end_date="yesterday")]
        )
        resp_sources = client.run_report(req_sources)
        total_ai = 0
        ai_sources = {}
        for row in resp_sources.rows:
            source = row.dimension_values[0].value.lower()
            sessions = int(row.metric_values[0].value)
            for ai_domain in AI_REFERRAL_SOURCES:
                if ai_domain in source:
                    ai_sources[source] = sessions
                    total_ai += sessions
                    break
        out_data["ai_referral_sessions"]["total"] = total_ai
        out_data["ai_referral_sessions"]["by_source"] = ai_sources
    except Exception as e:
        print(f"Error querying sources: {e}", file=sys.stderr)
        out_data["ai_referral_sessions"]["error"] = str(e)

    # 3. Key events totals
    try:
        print("Querying GA4 Key Events totals...")
        req_events = RunReportRequest(
            property=property_name,
            dimensions=[Dimension(name="eventName")],
            metrics=[Metric(name="eventCount")],
            date_ranges=[DateRange(start_date="28daysAgo", end_date="yesterday")]
        )
        resp_events = client.run_report(req_events)
        for row in resp_events.rows:
            ev_name = row.dimension_values[0].value
            count = int(row.metric_values[0].value)
            if ev_name in KEY_EVENT_NAMES:
                out_data["key_events"]["totals"][ev_name] = count
            elif ev_name == "tds_download":
                out_data["key_events"]["tds_downloads"]["total"] = count
    except Exception as e:
        print(f"Error querying event totals: {e}", file=sys.stderr)
        out_data["key_events"]["error"] = str(e)

    # 4. Key events breakdown by landing page
    try:
        print("Querying GA4 Key Events by landing page...")
        req_breakdown = RunReportRequest(
            property=property_name,
            dimensions=[Dimension(name="eventName"), Dimension(name="landingPagePlusQueryString")],
            metrics=[Metric(name="eventCount")],
            date_ranges=[DateRange(start_date="28daysAgo", end_date="yesterday")]
        )
        resp_breakdown = client.run_report(req_breakdown)
        for row in resp_breakdown.rows:
            ev_name = row.dimension_values[0].value
            landing = row.dimension_values[1].value
            count = int(row.metric_values[0].value)
            if ev_name in KEY_EVENT_NAMES:
                out_data["key_events"]["by_landing_page"].append({
                    "event_name": ev_name,
                    "landing_page": landing,
                    "count": count
                })
            elif ev_name == "tds_download":
                out_data["key_events"]["tds_downloads"]["by_landing_page"].append({
                    "landing_page": landing,
                    "count": count
                })
    except Exception as e:
        print(f"Error querying event breakdown: {e}", file=sys.stderr)

    # 5. Top 10 Countries
    try:
        print("Querying GA4 Top Countries...")
        req_geo = RunReportRequest(
            property=property_name,
            dimensions=[Dimension(name="country")],
            metrics=[Metric(name="sessions")],
            date_ranges=[DateRange(start_date="28daysAgo", end_date="yesterday")],
            order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
            limit=10
        )
        resp_geo = client.run_report(req_geo)
        for row in resp_geo.rows:
            out_data["top_countries"].append({
                "country": row.dimension_values[0].value,
                "sessions": int(row.metric_values[0].value)
            })
    except Exception as e:
        print(f"Error querying top countries: {e}", file=sys.stderr)
        out_data["top_countries_error"] = str(e)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(out_data, f, indent=2)

    print(f"GA4 data successfully saved to {OUTPUT_FILE}")
    return out_data

if __name__ == "__main__":
    run_pull()
