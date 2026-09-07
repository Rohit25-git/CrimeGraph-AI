from fastapi import APIRouter, HTTPException
from pathlib import Path
import pandas as pd

router = APIRouter(prefix="/ml", tags=["Machine Learning"])

MODEL_DIR = Path(__file__).resolve().parent.parent / "ml" / "models"
RESULTS_FILE = MODEL_DIR / "entity_risk_scores.csv"


@router.get("/risk")
def get_risk_scores():
    if not RESULTS_FILE.exists():
        raise HTTPException(
            status_code=404,
            detail="ML results not found. Train the model first."
        )

    df = pd.read_csv(RESULTS_FILE)

    high_risk_count = int((df["risk_level"] == "HIGH").sum())

    return {
        "total_entities": len(df),
        "anomalies": high_risk_count,
        "high_risk": int((df["risk_level"] == "HIGH").sum()),
        "medium_risk": int((df["risk_level"] == "MEDIUM").sum()),
        "low_risk": int((df["risk_level"] == "LOW").sum()),
        "entities": df.to_dict(orient="records")
    }


@router.get("/risk/{entity_id}")
def get_entity_risk(entity_id: str):
    if not RESULTS_FILE.exists():
        raise HTTPException(
            status_code=404,
            detail="ML results not found. Train the model first."
        )

    df = pd.read_csv(RESULTS_FILE)

    result = df[
        df["entity_id"].astype(str).str.upper()
        == entity_id.upper()
    ]

    if result.empty:
        raise HTTPException(
            status_code=404,
            detail=f"Entity {entity_id} not found"
        )

    return result.iloc[0].to_dict()
