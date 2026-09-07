import { useEffect, useState } from "react";

interface RiskEntity {
  entity_id: string;
  relationship_count: number;
  average_anomaly_score: number;
  maximum_anomaly_score: number;
  average_confidence: number;
  risk_score: number;
  risk_level: "HIGH" | "MEDIUM" | "LOW";
}

interface RiskResponse {
  total_entities: number;
  anomalies: number;
  high_risk: number;
  medium_risk: number;
  low_risk: number;
  entities: RiskEntity[];
}

export default function MLRiskPanel() {
  const [data, setData] = useState<RiskResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadRiskData = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch("/api/ml/risk");
      let res = response;
      if (!res.ok) {
        res = await fetch("/ml/risk");
      }

      if (!res.ok) {
        throw new Error(`ML API returned ${res.status}`);
      }

      const result: RiskResponse = await res.json();
      setData(result);
    } catch (err) {
      console.error("Failed to load trained ML results:", err);
      setError("Unable to load trained model results.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRiskData();
  }, []);

  if (loading) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-slate-300 border-t-blue-600" />
          <span className="text-sm font-medium text-slate-600">
            Loading trained ML Isolation Forest risk models...
          </span>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50/60 p-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-bold text-red-700">
              ML Risk Analysis
            </h3>
            <p className="mt-1 text-sm text-red-600">
              {error || "No trained model data available."}
            </p>
          </div>

          <button
            onClick={loadRiskData}
            className="rounded-lg border border-red-300 bg-white px-3 py-2 text-sm font-semibold text-red-700 hover:bg-red-50 shadow-sm"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <section className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
      <div className="flex items-center justify-between border-b border-slate-100 p-5 bg-gradient-to-r from-slate-50 to-white">
        <div>
          <div className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full bg-[rgb(16,185,129)] animate-pulse" />
            <h2 className="text-base font-black text-slate-900 tracking-tight">
              ML RISK INTELLIGENCE ENGINE
            </h2>
            <span className="text-[9px] font-mono font-bold px-2 py-0.5 rounded bg-[rgba(59,130,246,0.1)] text-[rgb(37,99,235)] border border-[rgba(59,130,246,0.2)]">
              ISOLATION FOREST v1.2
            </span>
          </div>

          <p className="mt-1 text-xs text-slate-500">
            Live unsupervised anomaly detection scoring entities across graph topology and transaction vectors.
          </p>
        </div>

        <button
          onClick={loadRiskData}
          className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-bold text-slate-700 hover:bg-slate-50 shadow-sm transition-all"
        >
          Refresh Models
        </button>
      </div>

      <div className="grid grid-cols-2 gap-3 p-5 md:grid-cols-4">
        <div className="rounded-lg border border-slate-200 bg-slate-50/70 p-4 shadow-sm">
          <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Entities Analyzed</p>
          <p className="mt-1 text-2xl font-black text-slate-900">
            {data.total_entities}
          </p>
          <span className="text-[10px] text-slate-500">Resolved Profiles</span>
        </div>

        <div className="rounded-lg border border-[rgba(239,68,68,0.3)] bg-[rgba(239,68,68,0.04)] p-4 shadow-sm border-l-4 border-l-[rgb(239,68,68)]">
          <p className="text-[10px] font-bold uppercase tracking-wider text-[rgb(185,28,28)]">Critical High Risk</p>
          <p className="mt-1 text-2xl font-black text-[rgb(220,38,38)]">
            {data.high_risk}
          </p>
          <span className="text-[10px] text-[rgb(239,68,68)] font-medium">Anomaly Score &gt; 70%</span>
        </div>

        <div className="rounded-lg border border-[rgba(245,158,11,0.3)] bg-[rgba(245,158,11,0.04)] p-4 shadow-sm border-l-4 border-l-[rgb(245,158,11)]">
          <p className="text-[10px] font-bold uppercase tracking-wider text-[rgb(180,83,9)]">Medium Risk Conduits</p>
          <p className="mt-1 text-2xl font-black text-[rgb(217,119,6)]">
            {data.medium_risk}
          </p>
          <span className="text-[10px] text-[rgb(245,158,11)] font-medium">Anomaly Score 40-70%</span>
        </div>

        <div className="rounded-lg border border-[rgba(16,185,129,0.3)] bg-[rgba(16,185,129,0.04)] p-4 shadow-sm border-l-4 border-l-[rgb(16,185,129)]">
          <p className="text-[10px] font-bold uppercase tracking-wider text-[rgb(4,120,87)]">Low Risk Normal</p>
          <p className="mt-1 text-2xl font-black text-[rgb(5,150,105)]">
            {data.low_risk}
          </p>
          <span className="text-[10px] text-[rgb(16,185,129)] font-medium">Verified Baseline</span>
        </div>
      </div>

      <div className="px-5 pb-5">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-800">
            Top Flagged Network Entities (ML Scored)
          </h3>

          <span className="text-[11px] text-slate-500 font-medium">
            Sorted by Isolation Forest Anomaly Index
          </span>
        </div>

        <div className="overflow-x-auto rounded-lg border border-slate-200">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="px-4 py-2.5 font-bold uppercase tracking-wider text-slate-600">
                  Rank
                </th>
                <th className="px-4 py-2.5 font-bold uppercase tracking-wider text-slate-600">
                  Target Entity ID
                </th>
                <th className="px-4 py-2.5 font-bold uppercase tracking-wider text-slate-600">
                  ML Risk Score
                </th>
                <th className="px-4 py-2.5 font-bold uppercase tracking-wider text-slate-600">
                  Risk Level
                </th>
                <th className="px-4 py-2.5 font-bold uppercase tracking-wider text-slate-600">
                  Connections
                </th>
                <th className="px-4 py-2.5 font-bold uppercase tracking-wider text-slate-600">
                  Model Confidence
                </th>
              </tr>
            </thead>

            <tbody className="divide-y divide-slate-100">
              {data.entities.slice(0, 10).map((entity, index) => (
                <tr
                  key={entity.entity_id}
                  className="hover:bg-slate-50/80 transition-colors"
                >
                  <td className="px-4 py-2.5 font-mono text-slate-400">
                    #{index + 1}
                  </td>

                  <td className="px-4 py-2.5 font-bold text-blue-700">
                    {entity.entity_id}
                  </td>

                  <td className="px-4 py-2.5">
                    <div className="flex items-center gap-2.5">
                      <div className="h-2 w-20 overflow-hidden rounded-full bg-slate-100">
                        <div
                          className={`h-full rounded-full ${
                            entity.risk_level === "HIGH" 
                              ? "bg-[rgb(239,68,68)]" 
                              : entity.risk_level === "MEDIUM" 
                              ? "bg-[rgb(245,158,11)]" 
                              : "bg-[rgb(16,185,129)]"
                          }`}
                          style={{
                            width: `${Math.min(entity.risk_score, 100)}%`,
                          }}
                        />
                      </div>

                      <span className="font-bold text-slate-900 font-mono">
                        {entity.risk_score.toFixed(2)}
                      </span>
                    </div>
                  </td>

                  <td className="px-4 py-2.5">
                    <span
                      className={`inline-block rounded px-2 py-0.5 text-[9px] font-bold uppercase border ${
                        entity.risk_level === "HIGH"
                          ? "bg-[rgba(239,68,68,0.1)] border-[rgba(239,68,68,0.3)] text-[rgb(185,28,28)]"
                          : entity.risk_level === "MEDIUM"
                          ? "bg-[rgba(245,158,11,0.1)] border-[rgba(245,158,11,0.3)] text-[rgb(180,83,9)]"
                          : "bg-[rgba(16,185,129,0.1)] border-[rgba(16,185,129,0.3)] text-[rgb(4,120,87)]"
                      }`}
                    >
                      {entity.risk_level}
                    </span>
                  </td>

                  <td className="px-4 py-2.5 font-semibold text-slate-700">
                    {entity.relationship_count}
                  </td>

                  <td className="px-4 py-2.5 font-semibold text-slate-700">
                    {(entity.average_confidence * 100).toFixed(1)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="mt-3.5 rounded-lg border border-blue-200 bg-blue-50/60 p-3">
          <p className="text-[11px] leading-relaxed text-blue-900">
            <span className="font-bold text-blue-800">
              Verified Pipeline:
            </span>{" "}
            Scores reflect multi-dimensional Isolation Forest anomaly predictions trained on graph degree, maximum transaction deviation, and cellular frequency anomalies.
          </p>
        </div>
      </div>
    </section>
  );
}
