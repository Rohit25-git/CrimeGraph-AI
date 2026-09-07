import os
import joblib
import pandas as pd
import networkx as nx

from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


DATA_PATH = "data/relationships.csv"
MODEL_DIR = "backend/app/ml/models"

os.makedirs(MODEL_DIR, exist_ok=True)


def load_data():
    df = pd.read_csv(DATA_PATH)

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)

    return df


def build_features(df):
    G = nx.DiGraph()

    for _, row in df.iterrows():
        source = row["source_id"]
        target = row["target_id"]

        G.add_edge(
            source,
            target,
            rel_type=row["rel_type"],
            amount=row["amount"]
        )

    features = []

    for node in G.nodes():

        out_degree = G.out_degree(node)
        in_degree = G.in_degree(node)

        total_degree = G.degree(node)

        weighted_amount = 0

        for _, target, data in G.out_edges(node, data=True):
            weighted_amount += float(data.get("amount", 0))

        features.append({
            "entity_id": node,
            "in_degree": in_degree,
            "out_degree": out_degree,
            "total_degree": total_degree,
            "transaction_amount": weighted_amount
        })

    return pd.DataFrame(features)


def train():

    print("Loading relationship data...")

    df = load_data()

    print(f"Loaded {len(df)} relationships")

    print("Building graph features...")

    features = build_features(df)

    feature_columns = [
        "in_degree",
        "out_degree",
        "total_degree",
        "transaction_amount"
    ]

    X = features[feature_columns]

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    print("Training Isolation Forest...")

    model = IsolationForest(
        n_estimators=200,
        contamination=0.10,
        random_state=42
    )

    model.fit(X_scaled)

    features["anomaly_score"] = -model.decision_function(X_scaled)

    features["is_anomaly"] = model.predict(X_scaled)

    features["is_anomaly"] = (
        features["is_anomaly"] == -1
    ).astype(int)

    # Convert anomaly score to 0-100 risk score
    min_score = features["anomaly_score"].min()
    max_score = features["anomaly_score"].max()

    if max_score > min_score:
        features["risk_score"] = (
            (features["anomaly_score"] - min_score)
            / (max_score - min_score)
            * 100
        )
    else:
        features["risk_score"] = 0

    features["risk_level"] = pd.cut(
        features["risk_score"],
        bins=[-1, 40, 70, 101],
        labels=["LOW", "MEDIUM", "HIGH"]
    )

    model_path = os.path.join(
        MODEL_DIR,
        "network_anomaly_model.joblib"
    )

    scaler_path = os.path.join(
        MODEL_DIR,
        "feature_scaler.joblib"
    )

    results_path = os.path.join(
        MODEL_DIR,
        "entity_risk_scores.csv"
    )

    joblib.dump(model, model_path)
    joblib.dump(scaler, scaler_path)

    features.to_csv(results_path, index=False)

    print()
    print("================================")
    print("ML TRAINING COMPLETE")
    print("================================")
    print(f"Entities analysed: {len(features)}")
    print(
        f"Anomalies detected: "
        f"{features['is_anomaly'].sum()}"
    )

    print()
    print("Top suspicious entities:")

    print(
        features[
            [
                "entity_id",
                "risk_score",
                "risk_level",
                "total_degree"
            ]
        ]
        .sort_values(
            "risk_score",
            ascending=False
        )
        .head(10)
        .to_string(index=False)
    )

    print()
    print(f"Model saved: {model_path}")
    print(f"Results saved: {results_path}")


if __name__ == "__main__":
    train()