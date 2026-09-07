import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline


BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data" / "relationships_5000.csv"
OUTPUT_DIR = BASE_DIR / "models"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


print("=" * 60)
print("CRIMEGRAPH AI - UNSUPERVISED TRAINING")
print("=" * 60)

# ---------------------------------------------------------
# 1. Load dataset
# ---------------------------------------------------------

df = pd.read_csv(DATA_FILE)
print(f"\nLoaded rows: {len(df)}")
print(f"Columns: {df.columns.tolist()}")

# ---------------------------------------------------------
# 2. Parse properties JSON
# ---------------------------------------------------------

def parse_properties(value):
    if pd.isna(value):
        return {}

    try:
        return json.loads(value)
    except Exception:
        return {}


properties = df["properties"].apply(parse_properties)

df["source_type"] = properties.apply(
    lambda x: x.get("source_type", "unknown")
)

df["verified"] = properties.apply(
    lambda x: int(bool(x.get("verified", False)))
)

# ---------------------------------------------------------
# 3. Timestamp features
# ---------------------------------------------------------

df["timestamp"] = pd.to_datetime(
    df["timestamp"],
    errors="coerce"
)

df["hour"] = df["timestamp"].dt.hour.fillna(0)

df["day_of_week"] = df["timestamp"].dt.dayofweek.fillna(0)

df["month"] = df["timestamp"].dt.month.fillna(0)

# ---------------------------------------------------------
# 4. Relationship-level features
# ---------------------------------------------------------

df["confidence"] = pd.to_numeric(
    df["confidence"],
    errors="coerce"
).fillna(0)

df["relationship_type"] = df["type"].fillna("UNKNOWN")

# ---------------------------------------------------------
# 5. Entity activity features
# ---------------------------------------------------------

source_counts = df["source_entity_id"].value_counts()

target_counts = df["target_entity_id"].value_counts()

df["source_activity"] = (
    df["source_entity_id"].map(source_counts).fillna(0)
)

df["target_activity"] = (
    df["target_entity_id"].map(target_counts).fillna(0)
)

df["total_entity_activity"] = (
    df["source_activity"] +
    df["target_activity"]
)

# ---------------------------------------------------------
# 6. Suspicious relationship indicators
# ---------------------------------------------------------

df["low_confidence"] = (
    df["confidence"] < 0.60
).astype(int)

df["unverified"] = (
    df["verified"] == 0
).astype(int)

# ---------------------------------------------------------
# 7. Features used by Isolation Forest
# ---------------------------------------------------------

numeric_features = [
    "confidence",
    "verified",
    "hour",
    "day_of_week",
    "month",
    "source_activity",
    "target_activity",
    "total_entity_activity",
    "low_confidence",
    "unverified",
]

categorical_features = [
    "relationship_type",
    "source_type",
]

X = df[
    numeric_features +
    categorical_features
].copy()

# ---------------------------------------------------------
# 8. Preprocessing
# ---------------------------------------------------------

preprocessor = ColumnTransformer(
    transformers=[
        (
            "numeric",
            StandardScaler(),
            numeric_features
        ),
        (
            "categorical",
            OneHotEncoder(
                handle_unknown="ignore",
                sparse_output=False
            ),
            categorical_features
        ),
    ]
)

# ---------------------------------------------------------
# 9. Isolation Forest
# ---------------------------------------------------------

model = IsolationForest(
    n_estimators=300,
    contamination="auto",
    random_state=42,
    n_jobs=-1
)

pipeline = Pipeline(
    steps=[
        ("preprocessor", preprocessor),
        ("model", model)
    ]
)

print("\nTraining Isolation Forest...")

pipeline.fit(X)

print("Training completed.")

# ---------------------------------------------------------
# 10. Generate anomaly scores
# ---------------------------------------------------------

# Isolation Forest:
# larger decision_function = more normal
# smaller = more anomalous

decision_scores = pipeline.decision_function(X)

# Convert so larger score = higher risk

risk_raw = -decision_scores

# Normalize to 0-100

minimum = risk_raw.min()
maximum = risk_raw.max()

if maximum > minimum:
    risk_score = (
        (risk_raw - minimum) /
        (maximum - minimum)
    ) * 100
else:
    risk_score = np.zeros(len(df))

df["anomaly_score"] = risk_score

# ---------------------------------------------------------
# 11. Classify anomaly level
# ---------------------------------------------------------

def classify(score):
    if score >= 80:
        return "HIGH"
    elif score >= 60:
        return "MEDIUM"
    else:
        return "LOW"


df["risk_level"] = df["anomaly_score"].apply(classify)

# ---------------------------------------------------------
# 12. Save relationship anomaly results
# ---------------------------------------------------------

relationship_output = df[
    [
        "id",
        "source_entity_id",
        "target_entity_id",
        "relationship_type",
        "confidence",
        "verified",
        "source_type",
        "timestamp",
        "source_activity",
        "target_activity",
        "anomaly_score",
        "risk_level",
    ]
].sort_values(
    "anomaly_score",
    ascending=False
)

relationship_output.to_csv(
    OUTPUT_DIR / "relationship_anomaly_scores.csv",
    index=False
)

# ---------------------------------------------------------
# 13. Aggregate risk by entity
# ---------------------------------------------------------

source_entities = df[
    [
        "source_entity_id",
        "anomaly_score",
        "confidence"
    ]
].rename(
    columns={
        "source_entity_id": "entity_id"
    }
)

target_entities = df[
    [
        "target_entity_id",
        "anomaly_score",
        "confidence"
    ]
].rename(
    columns={
        "target_entity_id": "entity_id"
    }
)

entity_data = pd.concat(
    [source_entities, target_entities],
    ignore_index=True
)

entity_scores = (
    entity_data
    .groupby("entity_id")
    .agg(
        relationship_count=("entity_id", "size"),
        average_anomaly_score=("anomaly_score", "mean"),
        maximum_anomaly_score=("anomaly_score", "max"),
        average_confidence=("confidence", "mean"),
    )
    .reset_index()
)

# Weighted entity risk

entity_scores["risk_score"] = (
    entity_scores["average_anomaly_score"] * 0.6
    +
    entity_scores["maximum_anomaly_score"] * 0.4
)

entity_scores["risk_score"] = (
    entity_scores["risk_score"]
    .clip(0, 100)
    .round(2)
)

entity_scores["risk_level"] = (
    entity_scores["risk_score"]
    .apply(classify)
)

entity_scores = entity_scores.sort_values(
    "risk_score",
    ascending=False
)

entity_scores.to_csv(
    OUTPUT_DIR / "entity_risk_scores.csv",
    index=False
)

# ---------------------------------------------------------
# 14. Print results
# ---------------------------------------------------------

print("\n" + "=" * 60)
print("TOP 20 HIGH-RISK ENTITIES")
print("=" * 60)

print(
    entity_scores.head(20).to_string(index=False)
)

print("\n" + "=" * 60)
print("TOP 20 ANOMALOUS RELATIONSHIPS")
print("=" * 60)

print(
    relationship_output.head(20).to_string(index=False)
)

print("\n" + "=" * 60)
print("OUTPUT FILES")
print("=" * 60)

print(
    OUTPUT_DIR / "relationship_anomaly_scores.csv"
)

print(
    OUTPUT_DIR / "entity_risk_scores.csv"
)

print("\nTraining pipeline completed successfully.")
