"use client";

import React, { useEffect, useState } from "react";
import { Activity, Radio, Calendar, Database, AlertCircle } from "lucide-react";

interface Game {
  game_id: string;
  season: string;
  game_date: string;
  matchup: string;
  home_team_abbr: string;
  away_team_abbr: string;
}

interface SidebarProps {
  selectedGameId: string | null;
  onSelectGame: (gameId: string) => void;
  connectionStatus: "connecting" | "connected" | "disconnected";
}

export function Sidebar({ selectedGameId, onSelectGame, connectionStatus }: SidebarProps) {
  const [games, setGames] = useState<Game[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchGames() {
      try {
        setLoading(true);
        setError(null);
        const res = await fetch("http://localhost:8000/api/games");
        if (!res.ok) {
          throw new Error(`Error fetching games: ${res.statusText}`);
        }
        const data = await res.json();
        setGames(data);
      } catch (err: any) {
        console.error(err);
        setError(err.message || "Failed to load game feed");
      } finally {
        setLoading(false);
      }
    }
    fetchGames();
  }, []);

  const getStatusColor = () => {
    switch (connectionStatus) {
      case "connected":
        return "bg-neon-green text-neon-green border-neon-green/20";
      case "connecting":
        return "bg-amber-400 text-amber-400 border-amber-400/20";
      case "disconnected":
      default:
        return "bg-neon-red text-neon-red border-neon-red/20";
    }
  };

  const getStatusText = () => {
    switch (connectionStatus) {
      case "connected":
        return "Live Connected";
      case "connecting":
        return "Connecting...";
      case "disconnected":
      default:
        return "Stream Offline";
    }
  };

  return (
    <aside
      id="game-select-sidebar"
      className="w-full md:w-80 flex flex-col glass-panel border-r border-slate-800 shrink-0 h-full overflow-hidden"
    >
      {/* Header / Brand */}
      <div className="p-6 border-b border-slate-800">
        <div className="flex items-center gap-2 mb-3">
          <Activity className="w-6 h-6 text-neon-blue pulse-indicator" />
          <span className="font-extrabold text-xl tracking-wider bg-gradient-to-r from-neon-blue to-neon-purple bg-clip-text text-transparent">
            CLUTCHNET
          </span>
        </div>
        <p className="text-xs text-slate-400 leading-relaxed font-light">
          Real-Time NBA Win Probability & Game State Inference Dashboard.
        </p>
      </div>

      {/* Stream Status indicator */}
      <div className="px-6 py-3 bg-slate-900/50 border-b border-slate-800 flex items-center justify-between">
        <span className="text-xs text-slate-400 font-medium">Connection Status</span>
        <div className="flex items-center gap-2">
          <span className={`w-2.5 h-2.5 rounded-full ${getStatusColor()} animate-pulse`} />
          <span className="text-xs font-semibold tracking-wide uppercase text-slate-200">
            {getStatusText()}
          </span>
        </div>
      </div>

      {/* Game Feed Selector */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        <div className="flex items-center gap-2 px-2 pb-2 text-slate-400 text-xs font-semibold uppercase tracking-wider">
          <Radio className="w-4 h-4 text-neon-purple" />
          <span>Select Game Feed</span>
        </div>

        {loading && (
          <div className="flex flex-col items-center justify-center py-12 space-y-2">
            <div className="w-8 h-8 border-4 border-slate-700 border-t-neon-blue rounded-full animate-spin" />
            <span className="text-xs text-slate-400">Loading NBA games database...</span>
          </div>
        )}

        {error && (
          <div className="p-4 bg-neon-red/10 border border-neon-red/20 rounded-xl flex items-start gap-2.5">
            <AlertCircle className="w-5 h-5 text-neon-red shrink-0 mt-0.5" />
            <div>
              <h5 className="text-sm font-semibold text-neon-red">Query Failed</h5>
              <p className="text-xs text-slate-400 mt-1 leading-normal">
                {error}. Please verify the backend FastAPI server is running on port 8000.
              </p>
            </div>
          </div>
        )}

        {!loading && !error && games.length === 0 && (
          <div className="text-center py-12 text-slate-500 flex flex-col items-center gap-2">
            <Database className="w-8 h-8 stroke-1 text-slate-600" />
            <p className="text-xs font-medium">No games found in the SQLite cache database.</p>
          </div>
        )}

        {!loading &&
          !error &&
          games.map((game) => {
            const isSelected = game.game_id === selectedGameId;
            return (
              <button
                key={game.game_id}
                id={`game-item-${game.game_id}`}
                onClick={() => onSelectGame(game.game_id)}
                className={`w-full text-left p-4 rounded-xl transition-all duration-300 border ${
                  isSelected
                    ? "bg-slate-900 border-neon-blue/40 shadow-[0_0_15px_rgba(6,182,212,0.08)]"
                    : "bg-slate-900/30 hover:bg-slate-900/60 border-slate-800/80 hover:border-slate-700"
                }`}
              >
                <div className="flex justify-between items-start mb-2">
                  <span className="text-[10px] text-slate-400 font-mono tracking-widest bg-slate-950 px-2 py-0.5 rounded-full border border-slate-800">
                    ID: {game.game_id}
                  </span>
                  <div className="flex items-center gap-1 text-[10px] text-slate-400 font-mono">
                    <Calendar className="w-3 h-3 text-slate-500" />
                    <span>{game.game_date}</span>
                  </div>
                </div>

                <h4 className="text-sm font-bold text-slate-100 tracking-wide mb-1.5 uppercase">
                  {game.matchup}
                </h4>

                <div className="flex justify-between items-center text-xs text-slate-400 font-medium">
                  <span>Season {game.season}</span>
                  <span className="text-[10px] uppercase font-bold text-neon-blue/80 font-mono">
                    {game.home_team_abbr} vs {game.away_team_abbr}
                  </span>
                </div>
              </button>
            );
          })}
      </div>
    </aside>
  );
}
