"use client";

import React, { useState } from "react";
import { Sidebar } from "../components/Sidebar";
import { ControlPanel } from "../components/ControlPanel";
import { PulseChart } from "../components/PulseChart";
import { ImpactTicker } from "../components/ImpactTicker";
import { MomentumBar } from "../components/MomentumBar";
import { useWebSocket } from "../hooks/useWebSocket";
import { getTeamColorInfo } from "../utils/teamColors";
import { Clock, ShieldAlert, Award, AlertCircle } from "lucide-react";

export default function Dashboard() {
  const [selectedGameId, setSelectedGameId] = useState<string | null>(null);
  
  // Custom hook for websocket messaging stream
  const { plays, latestEvent, status } = useWebSocket(selectedGameId);

  // Scoreboard details derived from latest play event
  const homeTeam = latestEvent?.home_team_abbr || "HOME";
  const awayTeam = latestEvent?.away_team_abbr || "AWAY";
  const homeScore = latestEvent?.home_score ?? 0;
  const awayScore = latestEvent?.away_score ?? 0;
  
  // Dynamic Team Colors
  const homeColorInfo = getTeamColorInfo(homeTeam);
  const awayColorInfo = getTeamColorInfo(awayTeam);

  // Temporal details
  const period = latestEvent?.period ?? 1;
  const secondsInPeriod = latestEvent?.seconds_remaining_in_period ?? 720;
  const clockText = `${Math.floor(secondsInPeriod / 60)}:${Math.floor(secondsInPeriod % 60)
    .toString()
    .padStart(2, "0")}`;
  
  const getQuarterText = (q: number) => {
    if (q <= 4) return `Quarter ${q}`;
    return `Overtime ${q - 4}`;
  };

  // Possession trackers
  const possession = latestEvent?.possession ?? 0;

  return (
    <div
      id="main-dashboard-container"
      className="flex flex-col md:flex-row h-screen w-screen overflow-hidden bg-stadium-black court-grid text-slate-100 font-sans"
    >
      {/* Sidebar Selector */}
      <Sidebar
        selectedGameId={selectedGameId}
        onSelectGame={setSelectedGameId}
        connectionStatus={status}
      />

      {/* Main Content Pane */}
      <main className="flex-1 flex flex-col h-full overflow-y-auto md:overflow-hidden p-6 gap-6">
        
        {/* Top Scoreboard Banner */}
        <section
          id="scoreboard-header"
          className="w-full stadium-panel-glow rounded-2xl p-6 border border-slate-800 flex flex-col md:flex-row items-center justify-between gap-6 shrink-0 relative overflow-hidden"
        >
          {/* Dynamic home team background glow */}
          {selectedGameId && (
            <div 
              className="absolute left-0 top-0 bottom-0 w-1/3 opacity-[0.04] pointer-events-none transition-all duration-500"
              style={{
                background: `radial-gradient(circle at 0% 50%, ${homeColorInfo.primary} 0%, transparent 70%)`
              }}
            />
          )}
          {/* Dynamic away team background glow */}
          {selectedGameId && (
            <div 
              className="absolute right-0 top-0 bottom-0 w-1/3 opacity-[0.04] pointer-events-none transition-all duration-500"
              style={{
                background: `radial-gradient(circle at 100% 50%, ${awayColorInfo.primary} 0%, transparent 70%)`
              }}
            />
          )}

          {selectedGameId ? (
            <>
              {/* Home Team */}
              <div className="flex items-center gap-4 w-full md:w-auto justify-end md:justify-start">
                <div className="text-right">
                  <h2 
                    className="text-3xl font-athletic font-black tracking-widest uppercase transition-all duration-500"
                    style={{ color: homeColorInfo.primary }}
                  >
                    {homeTeam}
                  </h2>
                  <span className="text-[10px] text-slate-400 font-semibold tracking-wider font-mono">
                    HOME TEAM
                  </span>
                </div>
                {possession === 1 && (
                  <span 
                    className="w-3.5 h-3.5 rounded-full animate-pulse transition-all duration-500" 
                    style={{ 
                      backgroundColor: homeColorInfo.primary,
                      boxShadow: `0 0 14px ${homeColorInfo.primary}`
                    }}
                    title="Possession" 
                  />
                )}
              </div>

              {/* Central Match Status & Score */}
              <div className="flex flex-col items-center gap-2 shrink-0 bg-stadium-black/90 px-8 py-3 rounded-xl border border-slate-800 shadow-[inset_0_1px_10px_rgba(230,95,0,0.02)] min-w-[200px]">
                <div className="flex items-center gap-6 font-athletic">
                  <span 
                    className="text-5xl font-extrabold tracking-wider transition-all duration-500 glow-text-orange"
                    style={{ color: homeColorInfo.primary }}
                  >
                    {homeScore}
                  </span>
                  <span className="text-slate-700 text-2xl font-light font-sans">:</span>
                  <span 
                    className="text-5xl font-extrabold tracking-wider transition-all duration-500 glow-text-amber"
                    style={{ color: awayColorInfo.primary }}
                  >
                    {awayScore}
                  </span>
                </div>

                <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-wider text-slate-400 bg-slate-900/60 px-3 py-1 rounded border border-slate-800 font-athletic">
                  <Clock className="w-3.5 h-3.5 text-court-orange" />
                  <span>{getQuarterText(period)}</span>
                  <span className="text-slate-700 font-light">|</span>
                  <span className="scoreboard-digital text-court-orange">{clockText}</span>
                </div>
              </div>

              {/* Away Team */}
              <div className="flex items-center gap-4 w-full md:w-auto justify-start md:justify-end">
                {possession === -1 && (
                  <span 
                    className="w-3.5 h-3.5 rounded-full animate-pulse transition-all duration-500" 
                    style={{ 
                      backgroundColor: awayColorInfo.primary,
                      boxShadow: `0 0 14px ${awayColorInfo.primary}`
                    }}
                    title="Possession" 
                  />
                )}
                <div className="text-left">
                  <h2 
                    className="text-3xl font-athletic font-black tracking-widest uppercase transition-all duration-500"
                    style={{ color: awayColorInfo.primary }}
                  >
                    {awayTeam}
                  </h2>
                  <span className="text-[10px] text-slate-400 font-semibold tracking-wider font-mono">
                    VISITOR TEAM
                  </span>
                </div>
              </div>
            </>
          ) : (
            <div className="w-full flex items-center justify-center gap-3 py-4 text-slate-400 text-sm font-medium">
              <AlertCircle className="w-5 h-5 text-court-orange" />
              <span>Select an NBA game match from the sidebar to activate the scoreboard feed.</span>
            </div>
          )}
        </section>

        {/* Dashboard Grid Workspace */}
        <div className="flex-1 min-h-0 flex flex-col md:flex-row gap-6 overflow-hidden">
          
          {/* Left Column: Visual Analytics */}
          <div className="flex-1 flex flex-col gap-6 min-w-0 overflow-y-auto md:overflow-hidden h-full">
            {/* Simulation controls */}
            <ControlPanel gameId={selectedGameId} />

            {/* Pulse Chart area curve */}
            <div className="flex-1 min-h-0">
              <PulseChart
                plays={plays}
                homeTeam={homeTeam}
                awayTeam={awayTeam}
              />
            </div>
          </div>

          {/* Right Column: Live Logs & Momentum */}
          <div className="w-full md:w-96 flex flex-col gap-6 shrink-0 h-full overflow-hidden">
            {/* Momentum progress indicators */}
            <MomentumBar
              homeTeam={homeTeam}
              awayTeam={awayTeam}
              homePtsLast3Min={latestEvent?.home_pts_last_3_min ?? 0}
              awayPtsLast3Min={latestEvent?.away_pts_last_3_min ?? 0}
            />

            {/* Scrolling Play impact log */}
            <div className="flex-1 min-h-0">
              <ImpactTicker plays={plays} />
            </div>
          </div>

        </div>
      </main>
    </div>
  );
}
