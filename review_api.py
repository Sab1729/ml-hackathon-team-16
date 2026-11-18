"""FastAPI development service for the PathSnap Review 1 fixtures."""

import csv
import logging
import os
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from route_decoder import decode, load_fixture


ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get("PATHSNAP_DATA", ROOT / "Student folder/Student folder"))
OUTPUT = Path(os.environ.get("PATHSNAP_REVIEW_OUTPUT", ROOT / "output/review-1"))
FIXTURES = {
    "synthetic": OUTPUT / "synthetic_decoder_fixture.json",
    "00000001": OUTPUT / "00000001/decoder_fixture.json",
}
logger = logging.getLogger("uvicorn.error")
app = FastAPI(title="PathSnap Review 1")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get(
        "PATHSNAP_UI_ORIGINS", "http://localhost:8080,http://127.0.0.1:8080"
    ).split(","),
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class PredictionRequest(BaseModel):
    trip_id: str


@app.middleware("http")
async def log_request(request: Request, call_next):
    request_id = uuid4().hex[:12]
    request.state.request_id = request_id
    start = perf_counter()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request=%s client=%s method=%s path=%s trip=%s status=%s duration_ms=%.1f",
        request_id, request.client.host if request.client else "unknown",
        request.method, request.url.path, getattr(request.state, "trip_id", "-"),
        response.status_code, (perf_counter() - start) * 1000,
    )
    return response


@app.get("/health")
def health():
    ready = all(path.is_file() for path in FIXTURES.values())
    if not ready:
        raise HTTPException(503, "Generate the development fixtures with review_one.py")
    return {"status": "ready"}


@app.get("/trips")
def trips():
    health()
    return {"trip_ids": list(FIXTURES)}


@app.post("/predict")
def predict(payload: PredictionRequest, request: Request):
    trip_id = payload.trip_id
    request.state.trip_id = trip_id
    if trip_id not in FIXTURES:
        raise HTTPException(404, "Unknown development trip")
    try:
        fixture, nodes, arcs = load_fixture(FIXTURES[trip_id], DATA)
        observations = fixture["observations"]
        assignments, sections, warnings = decode(observations, nodes, arcs)
        metrics = {
            "observation_count": len(assignments),
            "matched_count": sum(arc is not None for arc in assignments),
            "route_section_count": len(sections),
        }
        if trip_id == "00000001":
            with (FIXTURES[trip_id].parent / "aligned_reference.csv").open(
                encoding="utf-8", newline=""
            ) as stream:
                labels = [int(row["reference_arc_id"]) for row in csv.DictReader(stream)]
            if len(labels) != len(assignments):
                raise ValueError("Label count does not match fixture")
            metrics["provisional_accuracy"] = sum(a == b for a, b in zip(assignments, labels)) / len(labels)
    except (OSError, ValueError, KeyError) as error:
        logger.warning("request=%s fixture error: %s", request.state.request_id, error)
        raise HTTPException(503, "Development fixture unavailable or invalid") from error
    return {
        "trip_id": trip_id,
        "gps": {"type": "MultiPoint", "coordinates": [
            [row["longitude"], row["latitude"]] for row in observations
        ]},
        "predicted_route": {"type": "MultiLineString", "coordinates": sections},
        "metrics": metrics,
        "warnings": warnings,
    }
