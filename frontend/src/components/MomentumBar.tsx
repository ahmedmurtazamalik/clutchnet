"use client";

import React from "react";
import { getTeamColorInfo } from "../utils/teamColors";
import { Zap } from "lucide-react";

interface MomentumBarProps {
  homeTeam: string;
  awayTeam: string;
  homePtsLast3Min: number;
  awayPtsLast3Min: number;
}

export function MomentumBar({
  homeTeam,
  awayTeam,
  homePtsLast3Min,
  awayPtsLast3Min,
}: MomentumBarProps) {
  const homeScoreVal = homePtsLast3Min || 0;
  const awayScoreVal = awayPtsLast3Min || 0;
  
  const total = homeScoreVal + awayScoreVal;
  const homePct = total === 0 ? 50 : (homeScoreVal / total) * 100;
  const awayPct = 100 - homePct;

  const homeColorInfo = getTeamColorInfo(homeTeam);
  const awayColorInfo = getTeamColorInfo(awayTeam);

  return (
    <div className="w-full stadium-panel p-5 rounded-2xl border border-slate-800 bg-stadium-charcoal/80 space-y-4">
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-1.5 text-xs font-bold text-slate-400 uppercase tracking-wider font-athletic">
          <Zap className="w-4 h-4 text-court-amber" />
          <span>Last 3 Mins Momentum</span>
        </div>
        <div className="text-[9px] bg-slate-900 border border-slate-800 px-2 py-0.5 rounded font-mono text-slate-400 font-bold uppercase tracking-wider">
          Tug-of-War Engine
        </div>
      </div>

      <div className="space-y-2">
        {/* Momentum bar graphic */}
        <div className="h-4.5 w-full bg-stadium-black rounded overflow-hidden flex border border-slate-800 relative">
          {/* Middle indicator line */}
          <div className="absolute top-0 bottom-0 left-1/2 w-0.5 bg-slate-700 z-10" />

          <div
            className="h-full transition-all duration-700 ease-out relative flex items-center justify-end pr-2"
            style={{ 
              width: `${homePct}%`,
              backgroundColor: homeColorInfo.primary
            }}
          >
            {homeScoreVal > 0 && (
              <span className="text-[9px] font-bold text-white font-mono drop-shadow-[0_1px_2px_rgba(0,0,0,0.8)]">
                +{homeScoreVal} PTS
              </span>
            )}
          </div>
          <div
            className="h-full transition-all duration-700 ease-out relative flex items-center justify-start pl-2"
            style={{ 
              width: `${awayPct}%`,
              backgroundColor: awayColorInfo.primary
            }}
          >
            {awayScoreVal > 0 && (
              <span className="text-[9px] font-bold text-white font-mono drop-shadow-[0_1px_2px_rgba(0,0,0,0.8)]">
                +{awayScoreVal} PTS
              </span>
            )}
          </div>
        </div>

        {/* Legend */}
        <div className="flex justify-between text-xs font-bold font-athletic tracking-wider px-1">
          <div className="flex items-center gap-1" style={{ color: homeColorInfo.primary }}>
            <span className="uppercase">{homeTeam || "HOME"}</span>
            <span className="text-[10px] text-slate-500">({Math.round(homePct)}%)</span>
          </div>
          <div className="text-[9px] text-slate-500 font-normal uppercase tracking-normal hidden sm:inline">
            Equilibrium (50/50)
          </div>
          <div className="flex items-center gap-1 text-right" style={{ color: awayColorInfo.primary }}>
            <span className="text-[10px] text-slate-500">({Math.round(awayPct)}%)</span>
            <span className="uppercase">{awayTeam || "AWAY"}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
