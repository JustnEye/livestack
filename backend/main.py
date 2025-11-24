from fastapi import FastAPI
import random
import uuid
from datetime import datetime

app = FastAPI()

REGIONS = ["edge-us-1", "edge-eu-1", "edge-apac-1"]

VIDEOS = [
    {
        "title": "How TikTok Recommends Videos",
        "body": "A deep dive into real-time recommendation engines.",
    },
    {
        "title": "Distributed Systems 101",
        "body": "What every engineer should know about distributed computing.",
    },
    {
        "title": "Murdoch vs Redstone",
        "body": "The history of media empires and power.",
    },
    {
        "title": "Building a CDN Simulator",
        "body": "Simulating multi-edge routing and latency.",
    },
    {
        "title": "Ellison's AI Cluster",
        "body": "Inside Oracle's 1.2 billion-watt GPU brain.",
    },
]


@app.get("/recommend")
def recommend(server_hint: str | None = None):
    """Return a content object following the full frontend contract."""
    
    # Resolve server
    if server_hint is None:
        server = random.choice(REGIONS)
    else:
        server = server_hint

    video = random.choice(VIDEOS)

    response = {
        "content_id": str(uuid.uuid4()),
        "title": video["title"],
        "body": video["body"],
        "server_id": server,
        "server_region": server,       # identical for now; can differ later
        "timestamp": datetime.utcnow().isoformat(),
    }

    return response


@app.post("/rate")
def rate(payload: dict):
    """Accept rating submissions."""
    
    content_id = payload.get("content_id")
    rating = payload.get("rating")

    if not content_id or rating is None:
        return {"status": "error", "message": "Invalid payload"}

    print(f"[RATE] content_id={content_id} rating={rating}")

    return {"status": "ok"}

