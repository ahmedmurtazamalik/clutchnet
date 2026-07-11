"use client";

import React, { useEffect, useState } from "react";
import { Activity, Radio, Calendar, Database, AlertCircle } from "lucide-react";
import { getTeamColorInfo } from "../utils/teamColors";

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
  const [selectedSeason, setSelectedSeason] = useState<string>("local");
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchGames() {
      try {
        setLoading(true);
        setError(null);
        const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
        const url = selectedSeason === "local"
          ? `${backendUrl}/api/games`
          : `${backendUrl}/api/games/season/${selectedSeason}`;
        const res = await fetch(url);
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
  }, [selectedSeason]);

  const getStatusColor = () => {
    switch (connectionStatus) {
      case "connected":
        return "bg-emerald-500 text-emerald-500 border-emerald-500/20 shadow-[0_0_8px_rgba(16,185,129,0.3)]";
      case "connecting":
        return "bg-court-amber text-court-amber border-court-amber/20 shadow-[0_0_8px_rgba(245,158,11,0.3)]";
      case "disconnected":
      default:
        return "bg-rose-600 text-rose-600 border-rose-600/20";
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
      className="w-full md:w-80 flex flex-col stadium-panel border-r border-slate-800 shrink-0 h-full overflow-hidden bg-stadium-charcoal/90 z-20"
    >
      {/* Header / Brand */}
      <div className="p-6 border-b border-slate-800 bg-stadium-black/40">
        <div className="flex items-center gap-2 mb-3">
          <Activity className="w-6 h-6 text-court-orange pulse-indicator" />
          <span className="font-athletic font-black text-2xl tracking-wider bg-gradient-to-r from-court-orange to-court-amber bg-clip-text text-transparent">
            CLUTCHNET
          </span>
        </div>
        <p className="text-xs text-slate-400 leading-relaxed font-light">
          Real-Time NBA Win Probability & Game State Inference Dashboard.
        </p>
      </div>

      {/* Stream Status indicator */}
      <div className="px-6 py-3 bg-stadium-black/60 border-b border-slate-800 flex items-center justify-between">
        <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider font-athletic">Connection Status</span>
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${getStatusColor()} animate-pulse`} />
          <span className="text-xs font-semibold tracking-wide uppercase text-slate-200">
            {getStatusText()}
          </span>
        </div>
      </div>

      {/* Game Feed Selector */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <div className="flex items-center gap-2 px-2 text-slate-400 text-xs font-bold uppercase tracking-wider font-athletic">
          <Radio className="w-4 h-4 text-court-orange" />
          <span>Select Game Feed</span>
        </div>

        <div className="px-2">
          <label className="text-[10px] uppercase font-bold text-slate-500 tracking-wider block mb-1.5 font-athletic">
            Season Catalog
          </label>
          <select
            value={selectedSeason}
            onChange={(e) => setSelectedSeason(e.target.value)}
            disabled={loading}
            className="w-full bg-slate-900 border border-slate-800 text-slate-200 text-xs rounded-lg px-3 py-2.5 focus:outline-none focus:border-court-orange transition-all font-mono disabled:opacity-50"
          >
            <option value="local">Local Demo Cache</option>
            <option value="2024-25">2024-25 Season</option>
            <option value="2023-24">2023-24 Season</option>
            <option value="2022-23">2022-23 Season</option>
            <option value="2021-22">2021-22 Season</option>
          </select>
        </div>

        {loading && (
          <div className="flex flex-col items-center justify-center py-12 space-y-2 text-center px-4">
            <div className="w-8 h-8 border-4 border-slate-800 border-t-court-orange rounded-full animate-spin" />
            <span className="text-xs text-slate-400">
              {selectedSeason === "local"
                ? "Loading NBA games database..."
                : `Scraping & caching ${selectedSeason} season schedule from NBA API...`}
            </span>
          </div>
        )}

        {error && (
          <div className="p-4 bg-rose-500/10 border border-rose-500/20 rounded-xl flex items-start gap-2.5">
            <AlertCircle className="w-5 h-5 text-rose-500 shrink-0 mt-0.5" />
            <div>
              <h5 className="text-sm font-semibold text-rose-400">Query Failed</h5>
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
            const homeColor = getTeamColorInfo(game.home_team_abbr).primary;
            return (
              <button
                key={game.game_id}
                id={`game-item-${game.game_id}`}
                onClick={() => onSelectGame(game.game_id)}
                className={`w-full text-left p-4 ticket-card transition-all duration-300 ${
                  isSelected
                    ? "shadow-[0_0_15px_rgba(230,95,0,0.06)]"
                    : "hover:bg-slate-900/40"
                }`}
                style={{
                  borderColor: isSelected ? homeColor : '#202024',
                  borderWidth: isSelected ? '1.5px' : '1px'
                }}
              >
                <div className="flex justify-between items-start mb-2">
                  <span className="text-[9px] text-slate-400 font-mono tracking-widest bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                    ID: {game.game_id}
                  </span>
                  <div className="flex items-center gap-1 text-[10px] text-slate-400 font-mono">
                    <Calendar className="w-3 h-3 text-slate-500" />
                    <span>{game.game_date}</span>
                  </div>
                </div>

                <h4 className="text-base font-bold font-athletic text-slate-100 tracking-wider mb-1.5 uppercase">
                  {game.matchup}
                </h4>

                <div className="ticket-stub-line flex justify-between items-center text-xs text-slate-400 font-medium">
                  <span>Season {game.season}</span>
                  <span className="text-[10px] uppercase font-bold font-athletic" style={{ color: homeColor }}>
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
