"use client";

import React, { useEffect, useState } from "react";
import { Play, Pause, Square, Gauge, RefreshCw, AlertTriangle } from "lucide-react";

interface ControlPanelProps {
  gameId: string | null;
  onSimulationUpdate?: () => void;
}

interface SimulatorStatus {
  game_id: string | null;
  is_running: boolean;
  current_idx: number;
  total_events: number;
  speed_multiplier: number;
}

export function ControlPanel({ gameId, onSimulationUpdate }: ControlPanelProps) {
  const [status, setStatus] = useState<SimulatorStatus>({
    game_id: null,
    is_running: false,
    current_idx: 0,
    total_events: 0,
    speed_multiplier: 10.0,
  });
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Poll simulator status periodically
  useEffect(() => {
    async function fetchStatus() {
      try {
        const res = await fetch("http://localhost:8000/api/simulator/status");
        if (res.ok) {
          const data = await res.json();
          setStatus(data);
        }
      } catch (err) {
        console.error("Failed to query simulator status:", err);
      }
    }

    fetchStatus();
    const interval = setInterval(fetchStatus, 2000);
    return () => clearInterval(interval);
  }, [gameId]);

  const sendControl = async (action: string, extraParams: Record<string, any> = {}) => {
    if (!gameId && action === "start") {
      setError("Please select a game from the sidebar first.");
      return;
    }

    try {
      setLoading(true);
      setError(null);
      
      const payload = {
        action,
        game_id: gameId,
        ...extraParams
      };

      const res = await fetch("http://localhost:8000/api/simulator/control", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        throw new Error(detail.detail || `Action failed: ${res.statusText}`);
      }

      const responseData = await res.json();
      
      // Update status immediately from response if provided
      if (responseData.speed !== undefined) {
        setStatus((prev) => ({ ...prev, speed_multiplier: responseData.speed }));
      }
      
      // Query full status after action
      const statusRes = await fetch("http://localhost:8000/api/simulator/status");
      if (statusRes.ok) {
        const statusData = await statusRes.json();
        setStatus(statusData);
      }

      if (onSimulationUpdate) {
        onSimulationUpdate();
      }
    } catch (err: any) {
      console.error(err);
      setError(err.message || "Failed to execute simulator action.");
    } finally {
      setLoading(false);
    }
  };

  const speeds = [1, 5, 10, 20, 50, 100];
  const isCurrentGameActive = status.game_id === gameId;

  return (
    <div
      id="sim-control-panel"
      className="p-6 rounded-2xl glass-panel-glow-cyan flex flex-col md:flex-row md:items-center justify-between gap-6"
    >
      <div className="space-y-1">
        <h3 className="text-base font-bold tracking-wide text-slate-100 flex items-center gap-2 uppercase">
          <Gauge className="w-4.5 h-4.5 text-neon-blue" />
          Simulation Control Room
        </h3>
        <p className="text-xs text-slate-400 font-light leading-relaxed">
          Replay archived NBA game-states through the neural prediction engine.
        </p>
        
        {status.game_id && (
          <div className="pt-1.5 flex items-center gap-2">
            <span className="text-[10px] bg-slate-900 border border-slate-800 text-neon-blue font-mono px-2 py-0.5 rounded-md">
              Loaded: {status.game_id}
            </span>
            <span className="text-[10px] text-slate-400 font-medium">
              Progress: {status.current_idx} / {status.total_events} events ({Math.round((status.current_idx / (status.total_events || 1)) * 100)}%)
            </span>
          </div>
        )}
      </div>

      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-4 shrink-0">
        {/* Main controls */}
        <div className="flex items-center bg-slate-950/80 border border-slate-800 rounded-xl p-1 gap-1">
          {(!status.is_running || !isCurrentGameActive) ? (
            <button
              id="btn-play"
              disabled={loading || !gameId}
              onClick={() => {
                if (isCurrentGameActive && status.game_id) {
                  sendControl("resume");
                } else {
                  sendControl("start");
                }
              }}
              className="px-4 py-2 bg-neon-blue/15 hover:bg-neon-blue/30 text-neon-blue disabled:opacity-30 disabled:hover:bg-neon-blue/15 rounded-lg flex items-center justify-center gap-2 transition-all duration-300 font-semibold text-xs tracking-wider uppercase border border-neon-blue/10"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>{isCurrentGameActive ? "Resume" : "Start"}</span>
            </button>
          ) : (
            <button
              id="btn-pause"
              disabled={loading}
              onClick={() => sendControl("pause")}
              className="px-4 py-2 bg-amber-500/10 hover:bg-amber-500/20 text-amber-400 rounded-lg flex items-center justify-center gap-2 transition-all duration-300 font-semibold text-xs tracking-wider uppercase border border-amber-500/10"
            >
              <Pause className="w-3.5 h-3.5 fill-current" />
              <span>Pause</span>
            </button>
          )}

          <button
            id="btn-stop"
            disabled={loading || !status.game_id}
            onClick={() => sendControl("stop")}
            className="p-2 bg-slate-900/40 hover:bg-neon-red/10 text-slate-400 hover:text-neon-red rounded-lg transition-all duration-300 border border-transparent hover:border-neon-red/10"
            title="Stop & Clear"
          >
            <Square className="w-4 h-4 fill-current" />
          </button>
        </div>

        {/* Speed Adjustment */}
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider hidden sm:inline">Speed:</span>
          <select
            id="speed-select"
            value={status.speed_multiplier}
            disabled={loading || !status.game_id}
            onChange={(e) => sendControl("speed", { speed: parseFloat(e.target.value) })}
            className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs font-mono font-bold text-slate-200 outline-none focus:border-neon-blue/40 transition-all duration-300"
          >
            {speeds.map((s) => (
              <option key={s} value={s}>
                {s}x Replay
              </option>
            ))}
          </select>
        </div>
      </div>

      {error && (
        <div className="w-full flex items-center gap-2 p-3 bg-neon-red/10 border border-neon-red/20 rounded-xl text-xs text-neon-red mt-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
}
