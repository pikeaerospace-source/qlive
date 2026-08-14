import { useState } from "react";
import Stat from "../components/Stat";

export default function DashboardPage() {
  const [live, setLive] = useState(false);
  const [title, setTitle] = useState("My Live Stream");
  const [category, setCategory] = useState("gaming");

  return (
    <>
      <h1 className="page-title">Broadcaster Dashboard</h1>
      <p className="page-subtitle">
        Manage your live stream and monitor its health.
      </p>

      <div className="card" style={{ maxWidth: 560, marginBottom: 20 }}>
        <div className="field">
          <label htmlFor="title">Stream title</label>
          <input
            id="title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="category">Category</label>
          <select
            id="category"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          >
            <option value="gaming">Gaming</option>
            <option value="tech">Tech</option>
            <option value="music">Music</option>
            <option value="other">Other</option>
          </select>
        </div>
        <div>
          {live ? (
            <button
              type="button"
              className="btn btn--danger"
              onClick={() => setLive(false)}
            >
              Stop broadcast
            </button>
          ) : (
            <button
              type="button"
              className="btn"
              onClick={() => setLive(true)}
            >
              Start broadcast
            </button>
          )}
        </div>
      </div>

      <div className="stats-row">
        <Stat label="Status" value={live ? "Live" : "Idle"} />
        <Stat label="Viewers" value={live ? 128 : 0} />
        <Stat label="Bandwidth" value={live ? "4.5 Mbps" : "—"} />
        <Stat label="Buffer" value="healthy" />
        <Stat label="Chunks" value={live ? 4321 : 0} />
        <Stat label="Retransmissions" value={3} />
      </div>
    </>
  );
}
