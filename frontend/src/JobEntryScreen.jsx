import { useState, useEffect } from "react";

// ---------------------------------------------------------------------------
// Backpack — Operative Job Entry Screen
// The Operative records the details of a completed job; the app computes a
// live cost estimate for the QS. Pure React + fetch, no UI library required
// so it deploys anywhere with zero extra dependencies.
// ---------------------------------------------------------------------------

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function JobEntryScreen() {
  const [rates, setRates] = useState(null);
  const [reference, setReference] = useState("");
  const [operative, setOperative] = useState("");
  const [description, setDescription] = useState("");
  const [hours, setHours] = useState("");
  const [materials, setMaterials] = useState("");
  const [vehicles, setVehicles] = useState([]);
  const [plant, setPlant] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  // Pull reference rates from the API on load
  useEffect(() => {
    fetch(`${API}/rates`)
      .then((r) => r.json())
      .then(setRates)
      .catch(() => setError("Could not load rates — is the API running?"));
  }, []);

  // ---- live client-side estimate (mirrors the server formula) ----
  const liveEstimate = () => {
    if (!rates) return 0;
    const labour = (parseFloat(hours) || 0) * rates.labour_rate_per_hour;
    const veh = vehicles.reduce(
      (s, v) => s + (rates.vehicle_rates_per_day[v.vehicle_type] || 0) * (parseFloat(v.days_on_site) || 0), 0);
    const pl = plant.reduce(
      (s, p) => s + (rates.plant_rates_per_day[p.plant_type] || 0) * (parseFloat(p.days_on_site) || 0), 0);
    const mat = parseFloat(materials) || 0;
    return labour + veh + pl + mat;
  };

  const addVehicle = () => {
    const first = Object.keys(rates.vehicle_rates_per_day)[0];
    setVehicles([...vehicles, { vehicle_type: first, days_on_site: 1 }]);
  };
  const addPlant = () => {
    const first = Object.keys(rates.plant_rates_per_day)[0];
    setPlant([...plant, { plant_type: first, days_on_site: 1 }]);
  };

  const submit = async () => {
    setError("");
    if (!reference || !operative || !hours) {
      setError("Reference, operative name and time on site are required.");
      return;
    }
    setSubmitting(true);
    try {
      const res = await fetch(`${API}/jobs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          reference, operative_name: operative, description,
          time_on_site_hours: parseFloat(hours),
          materials_cost: parseFloat(materials) || 0,
          vehicles: vehicles.map((v) => ({ vehicle_type: v.vehicle_type, days_on_site: parseFloat(v.days_on_site) })),
          plant: plant.map((p) => ({ plant_type: p.plant_type, days_on_site: parseFloat(p.days_on_site) })),
        }),
      });
      if (!res.ok) throw new Error("Submission failed");
      setResult(await res.json());
    } catch (e) {
      setError(e.message);
    } finally {
      setSubmitting(false);
    }
  };

  const reset = () => {
    setResult(null); setReference(""); setOperative(""); setDescription("");
    setHours(""); setMaterials(""); setVehicles([]); setPlant([]);
  };

  if (!rates) {
    return <div style={S.loading}>{error || "Loading…"}</div>;
  }

  // ---- confirmation view after submit ----
  if (result) {
    const b = result.breakdown;
    return (
      <div style={S.page}>
        <div style={S.card}>
          <div style={S.tick}>✓</div>
          <h2 style={S.h2}>Job submitted for QS review</h2>
          <p style={S.ref}>{result.reference}</p>
          <div style={S.breakRows}>
            <Row label="Labour" value={b.labour_cost} />
            <Row label="Vehicles" value={b.vehicle_cost} />
            <Row label="Plant / tools" value={b.plant_cost} />
            <Row label="Materials" value={b.materials_cost} />
            <div style={S.totalRow}>
              <span>Total job cost</span>
              <span>£{b.total_cost.toFixed(2)}</span>
            </div>
          </div>
          <button style={S.btnPrimary} onClick={reset}>Log another job</button>
        </div>
      </div>
    );
  }

  // ---- main entry form ----
  return (
    <div style={S.page}>
      <div style={S.card}>
        <header style={S.header}>
          <div style={S.logo}>BACKPACK</div>
          <span style={S.sub}>Operative · Job Entry</span>
        </header>

        <Field label="Job reference *">
          <input style={S.input} value={reference}
            onChange={(e) => setReference(e.target.value)}
            placeholder="e.g. STREETLIGHT-042" />
        </Field>
        <Field label="Operative name *">
          <input style={S.input} value={operative}
            onChange={(e) => setOperative(e.target.value)}
            placeholder="Your name" />
        </Field>
        <Field label="Job description">
          <input style={S.input} value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="What was the work?" />
        </Field>
        <Field label="Time on site (hours) *">
          <input style={S.input} type="number" min="0" step="0.25" value={hours}
            onChange={(e) => setHours(e.target.value)} placeholder="0" />
        </Field>

        {/* Vehicles */}
        <div style={S.sectionHead}>
          <span>Vehicles on site</span>
          <button style={S.btnAdd} onClick={addVehicle}>+ Add</button>
        </div>
        {vehicles.map((v, i) => (
          <div style={S.lineItem} key={i}>
            <select style={S.select} value={v.vehicle_type}
              onChange={(e) => {
                const c = [...vehicles]; c[i].vehicle_type = e.target.value; setVehicles(c);
              }}>
              {Object.keys(rates.vehicle_rates_per_day).map((k) => (
                <option key={k}>{k}</option>
              ))}
            </select>
            <input style={S.daysInput} type="number" min="0" step="0.5" value={v.days_on_site}
              onChange={(e) => {
                const c = [...vehicles]; c[i].days_on_site = e.target.value; setVehicles(c);
              }} />
            <span style={S.days}>days</span>
            <button style={S.btnDel}
              onClick={() => setVehicles(vehicles.filter((_, j) => j !== i))}>×</button>
          </div>
        ))}

        {/* Plant / tools */}
        <div style={S.sectionHead}>
          <span>Plant / tools used</span>
          <button style={S.btnAdd} onClick={addPlant}>+ Add</button>
        </div>
        {plant.map((p, i) => (
          <div style={S.lineItem} key={i}>
            <select style={S.select} value={p.plant_type}
              onChange={(e) => {
                const c = [...plant]; c[i].plant_type = e.target.value; setPlant(c);
              }}>
              {Object.keys(rates.plant_rates_per_day).map((k) => (
                <option key={k}>{k}</option>
              ))}
            </select>
            <input style={S.daysInput} type="number" min="0" step="0.5" value={p.days_on_site}
              onChange={(e) => {
                const c = [...plant]; c[i].days_on_site = e.target.value; setPlant(c);
              }} />
            <span style={S.days}>days</span>
            <button style={S.btnDel}
              onClick={() => setPlant(plant.filter((_, j) => j !== i))}>×</button>
          </div>
        ))}

        <Field label="Materials cost (£)">
          <input style={S.input} type="number" min="0" step="0.01" value={materials}
            onChange={(e) => setMaterials(e.target.value)} placeholder="0.00" />
        </Field>

        <div style={S.estimate}>
          <span>Live estimate</span>
          <strong>£{liveEstimate().toFixed(2)}</strong>
        </div>

        {error && <div style={S.error}>{error}</div>}

        <button style={S.btnPrimary} onClick={submit} disabled={submitting}>
          {submitting ? "Submitting…" : "Submit to QS"}
        </button>
      </div>
    </div>
  );
}

// -- small presentational helpers --
function Field({ label, children }) {
  return (
    <label style={S.field}>
      <span style={S.label}>{label}</span>
      {children}
    </label>
  );
}
function Row({ label, value }) {
  return (
    <div style={S.row}>
      <span>{label}</span>
      <span>£{value.toFixed(2)}</span>
    </div>
  );
}

// -- inline styles: keeps the deliverable to a single dependency-free file --
const ORANGE = "#E8541E";
const INK = "#1A1A2E";
const S = {
  page: { minHeight: "100vh", background: "#F4F3EF", display: "flex",
    justifyContent: "center", padding: "24px 16px",
    fontFamily: "'Segoe UI', system-ui, sans-serif" },
  card: { width: "100%", maxWidth: 460, background: "#fff", borderRadius: 18,
    padding: 28, boxShadow: "0 12px 40px rgba(26,26,46,0.10)", height: "fit-content" },
  header: { display: "flex", alignItems: "baseline", gap: 10, marginBottom: 22,
    borderBottom: `3px solid ${ORANGE}`, paddingBottom: 12 },
  logo: { fontWeight: 800, fontSize: 22, letterSpacing: 1, color: INK },
  sub: { color: "#888", fontSize: 13, fontWeight: 600 },
  field: { display: "block", marginBottom: 14 },
  label: { display: "block", fontSize: 13, fontWeight: 600, color: "#555", marginBottom: 6 },
  input: { width: "100%", boxSizing: "border-box", padding: "11px 13px",
    border: "1.5px solid #E2E0DA", borderRadius: 10, fontSize: 15, outline: "none" },
  sectionHead: { display: "flex", justifyContent: "space-between", alignItems: "center",
    margin: "18px 0 8px", fontSize: 14, fontWeight: 700, color: INK },
  btnAdd: { background: "#FDEDE6", color: ORANGE, border: "none", borderRadius: 8,
    padding: "5px 12px", fontWeight: 700, cursor: "pointer", fontSize: 13 },
  lineItem: { display: "flex", alignItems: "center", gap: 8, marginBottom: 8 },
  select: { flex: 1, padding: "9px 10px", border: "1.5px solid #E2E0DA",
    borderRadius: 9, fontSize: 14, background: "#fff" },
  daysInput: { width: 56, padding: "9px 8px", border: "1.5px solid #E2E0DA",
    borderRadius: 9, fontSize: 14, textAlign: "center" },
  days: { fontSize: 12, color: "#999" },
  btnDel: { background: "none", border: "none", color: "#C0392B", fontSize: 22,
    cursor: "pointer", lineHeight: 1, padding: "0 4px" },
  estimate: { display: "flex", justifyContent: "space-between", alignItems: "center",
    background: INK, color: "#fff", borderRadius: 12, padding: "14px 18px",
    margin: "20px 0 16px", fontSize: 15 },
  error: { background: "#FDECEA", color: "#C0392B", padding: "10px 14px",
    borderRadius: 9, fontSize: 14, marginBottom: 12 },
  btnPrimary: { width: "100%", background: ORANGE, color: "#fff", border: "none",
    borderRadius: 11, padding: "14px", fontSize: 16, fontWeight: 700, cursor: "pointer" },
  loading: { minHeight: "100vh", display: "flex", alignItems: "center",
    justifyContent: "center", fontFamily: "system-ui", color: "#666" },
  tick: { width: 54, height: 54, borderRadius: "50%", background: "#27AE60",
    color: "#fff", fontSize: 30, display: "flex", alignItems: "center",
    justifyContent: "center", margin: "0 auto 14px" },
  h2: { textAlign: "center", color: INK, margin: "0 0 4px", fontSize: 20 },
  ref: { textAlign: "center", color: ORANGE, fontWeight: 700, marginBottom: 20 },
  breakRows: { marginBottom: 22 },
  row: { display: "flex", justifyContent: "space-between", padding: "9px 0",
    borderBottom: "1px solid #F0EEE9", fontSize: 15, color: "#444" },
  totalRow: { display: "flex", justifyContent: "space-between", padding: "14px 0 4px",
    fontSize: 18, fontWeight: 800, color: INK },
};
