"use client";

import React from "react";
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

  return (
    <div className="w-full glass-panel p-5 rounded-2xl border border-slate-800 space-y-4">
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-1.5 text-xs font-bold text-slate-400 uppercase tracking-wider">
          <Zap className="w-4 h-4 text-amber-400" />
          <span>Last 3 Mins Momentum</span>
        </div>
        <div className="text-[10px] bg-slate-900 border border-slate-800 px-2 py-0.5 rounded-full font-mono text-slate-400">
          Tug-of-War Engine
        </div>
      </div>

      <div className="space-y-2">
        {/* Momentum bar graphic */}
        <div className="h-4 w-full bg-slate-950 rounded-full overflow-hidden flex border border-slate-900 relative">
          {/* Middle indicator line */}
          <div className="absolute top-0 bottom-0 left-1/2 w-0.5 bg-slate-800 z-10" />

          <div
            className="h-full bg-gradient-to-r from-neon-blue to-cyan-400 transition-all duration-700 ease-out relative"
            style={{ width: `${homePct}%` }}
          >
            {homeScoreVal > 0 && (
              <span className="absolute right-2 top-1/2 -translate-y-1/2 text-[9px] font-bold text-slate-950 font-mono">
                +{homeScoreVal} PTS
              </span>
            )}
          </div>
          <div
            className="h-full bg-gradient-to-l from-neon-purple to-pink-500 transition-all duration-700 ease-out relative"
            style={{ width: `${awayPct}%` }}
          >
            {awayScoreVal > 0 && (
              <span className="absolute left-2 top-1/2 -translate-y-1/2 text-[9px] font-bold text-slate-950 font-mono">
                +{awayScoreVal} PTS
              </span>
            )}
          </div>
        </div>

        {/* Legend */}
        <div className="flex justify-between text-xs font-extrabold font-mono tracking-wider px-1">
          <div className="flex items-center gap-1 text-neon-blue">
            <span className="uppercase">{homeTeam || "HOME"}</span>
            <span className="text-[10px] text-slate-500">({Math.round(homePct)}%)</span>
          </div>
          <div className="text-[10px] text-slate-500 font-normal uppercase tracking-normal">
            Neutral equilibrium (50/50)
          </div>
          <div className="flex items-center gap-1 text-neon-purple text-right">
            <span className="text-[10px] text-slate-500">({Math.round(awayPct)}%)</span>
            <span className="uppercase">{awayTeam || "AWAY"}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
