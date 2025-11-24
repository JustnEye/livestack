import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import httpx
import streamlit as st

BACKEND_BASE_URL = "http://localhost:8000"  # adjust if needed


# ---------- HTTP helpers ----------

def get_client() -> httpx.Client:
    """Return a short-lived HTTP client with a sane timeout."""
    return httpx.Client(timeout=5.0)


def fetch_recommendation(server_hint: Optional[str] = None) -> Tuple[Optional[Dict[str, Any]], Optional[float]]:
    """
    Call the backend /recommend endpoint.
    Returns (response_json, latency_ms) or (None, None) on failure.
    """
    params: Dict[str, Any] = {}
    if server_hint:
        params["server_hint"] = server_hint

    try:
        with get_client() as client:
            start = time.perf_counter()
            resp = client.get(f"{BACKEND_BASE_URL}/recommend", params=params)
            elapsed_ms = (time.perf_counter() - start) * 1000.0
    except Exception as e:
        st.error(f"Failed to contact backend: {e}")
        return None, None

    if resp.status_code != 200:
        st.error(f"Backend returned status {resp.status_code}: {resp.text}")
        return None, None

    try:
        data = resp.json()
    except Exception as e:
        st.error(f"Failed to decode backend JSON: {e}")
        return None, None

    return data, elapsed_ms


def send_rating(content_id: str, rating: int) -> bool:
    """
    Send a rating to /rate.
    Returns True on success, False otherwise.
    """
    payload = {"content_id": content_id, "rating": rating}
    try:
        with get_client() as client:
            resp = client.post(f"{BACKEND_BASE_URL}/rate", json=payload)
    except Exception as e:
        st.error(f"Failed to send rating: {e}")
        return False

    if resp.status_code != 200:
        st.error(f"Backend rating error ({resp.status_code}): {resp.text}")
        return False

    return True


# ---------- State helpers ----------

def init_state() -> None:
    """Initialize Streamlit session_state keys."""
    if "current_rec" not in st.session_state:
        st.session_state.current_rec: Optional[Dict[str, Any]] = None
    if "last_latency_ms" not in st.session_state:
        st.session_state.last_latency_ms: Optional[float] = None
    if "logs" not in st.session_state:
        st.session_state.logs: List[Dict[str, Any]] = []


def log_event(event: Dict[str, Any]) -> None:
    """Append an event dictionary to the log."""
    st.session_state.logs.append(event)


# ---------- Main app ----------

def main() -> None:
    st.set_page_config(page_title="LiveStack Frontend", layout="wide")
    init_state()

    st.title("LiveStack Lab – Recommendation Playground")

    # Sidebar: simulated CDN/server selection
    st.sidebar.header("Simulated CDN / Server")
    server_hint = st.sidebar.selectbox(
        "Choose server / region",
        ["auto", "edge-us-1", "edge-eu-1", "edge-apac-1"],
        index=0,
    )
    st.sidebar.markdown(
        "The selected value is sent to the backend as `server_hint`. "
        "Use this to simulate different CDN edges."
    )

    col_main, col_metrics = st.columns([2, 1])

    # ---------- Left column: content + rating ----------
    with col_main:
        st.subheader("Recommended Content")

        if st.button("Next recommendation"):
            hint = None if server_hint == "auto" else server_hint
            rec, latency_ms = fetch_recommendation(hint)

            if rec is None:
                st.error("Failed to fetch recommendation.")
            else:
                st.session_state.current_rec = rec
                st.session_state.last_latency_ms = latency_ms

                log_event(
                    {
                        "time": datetime.utcnow().isoformat(),
                        "event": "recommend",
                        "content_id": rec.get("content_id"),
                        "title": rec.get("title"),
                        "server_id": rec.get("server_id"),
                        "server_region": rec.get("server_region"),
                        "latency_ms": latency_ms,
                        "rating": None,
                        "success": True,
                    }
                )

        current = st.session_state.current_rec

        if current is None:
            st.info("Click **Next recommendation** to load content.")
        else:
            # Content card
            st.markdown(f"### {current.get('title', 'Untitled')}")
            body = current.get("body", "")
            if body:
                st.write(body)
            else:
                st.write("_No body provided by backend._")

            st.markdown("---")
            st.markdown("### Rate this content")

            # Rating buttons 1–5
            rate_cols = st.columns(5)
            for idx, rating in enumerate(range(1, 6)):
                if rate_cols[idx].button(str(rating), key=f"rate_{rating}"):
                    content_id = current.get("content_id")
                    if not content_id:
                        st.error("Current content has no content_id; cannot send rating.")
                        ok = False
                    else:
                        ok = send_rating(content_id, rating)

                    log_event(
                        {
                            "time": datetime.utcnow().isoformat(),
                            "event": "rate",
                            "content_id": content_id,
                            "title": current.get("title"),
                            "server_id": current.get("server_id"),
                            "server_region": current.get("server_region"),
                            "latency_ms": st.session_state.last_latency_ms,
                            "rating": rating,
                            "success": ok,
                        }
                    )

                    if ok:
                        st.success(f"Recorded rating: {rating}")
                    else:
                        st.error("Failed to submit rating.")

    # ---------- Right column: metrics ----------
    with col_metrics:
        st.subheader("Request Metrics")

        latency_ms = st.session_state.last_latency_ms
        current = st.session_state.current_rec

        st.metric(
            label="Last request latency (ms)",
            value=f"{latency_ms:.1f}" if latency_ms is not None else "—",
        )

        if current is not None:
            st.text(f"Server ID: {current.get('server_id', 'unknown')}")
            st.text(f"Region:   {current.get('server_region', 'unknown')}")

        # Simple aggregate stats
        rec_events = [
            e for e in st.session_state.logs
            if e.get("event") == "recommend" and e.get("latency_ms") is not None
        ]

        if rec_events:
            avg_latency = sum(e["latency_ms"] for e in rec_events) / len(rec_events)
            st.text(f"Total recommendations: {len(rec_events)}")
            st.text(f"Avg latency (ms): {avg_latency:.1f}")
        else:
            st.text("Total recommendations: 0")
            st.text("Avg latency (ms): —")

    # ---------- Bottom: event log ----------
    st.markdown("---")
    st.subheader("Event Log")

    if st.session_state.logs:
        st.dataframe(st.session_state.logs)
    else:
        st.write("No events logged yet.")


if __name__ == "__main__":
    main()

