"use client";

import React, { useRef, useEffect } from "react";
import { Sparkles, TrendingUp, TrendingDown, RefreshCcw } from "lucide-react";
import { PlayEvent } from "../hooks/useWebSocket";

interface ImpactTickerProps {
  plays: PlayEvent[];
}

export function ImpactTicker({ plays }: ImpactTickerProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  // Auto scroll to bottom when new plays arrive
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [plays.length]);

  // Sort plays by eventnum to render chronologically.
  // We reverse them if we want the newest at the top,
  // but if we are scrolling to the bottom, chronological order is standard.
  const sortedPlays = [...plays].sort((a, b) => a.eventnum - b.eventnum);

  const formatDelta = (delta: number) => {
    const pct = delta * 100;
    if (pct === 0) return "0.0%";
    const sign = pct > 0 ? "+" : "";
    return `${sign}${pct.toFixed(1)}%`;
  };

  const getDeltaBadgeStyle = (delta: number) => {
    if (delta > 0.05) {
      return "bg-emerald-500/20 text-emerald-400 border-emerald-500/40 shadow-[0_0_10px_rgba(16,185,129,0.2)] animate-pulse";
    }
    if (delta > 0) {
      return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
    }
    if (delta < -0.05) {
      return "bg-rose-500/20 text-rose-400 border-rose-500/40 shadow-[0_0_10px_rgba(244,63,94,0.2)] animate-pulse";
    }
    if (delta < 0) {
      return "bg-rose-500/10 text-rose-400 border-rose-500/20";
    }
    return "bg-slate-800 text-slate-400 border-slate-700";
  };

  const getQuarterText = (period: number) => {
    if (period <= 4) return `Q${period}`;
    return `OT${period - 4}`;
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  return (
    <div
      id="impact-ticker"
      className="stadium-panel flex flex-col rounded-2xl border border-slate-800 bg-stadium-charcoal/80 h-full overflow-hidden"
    >
      {/* Header */}
      <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-stadium-black/50">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-court-orange" />
          <span className="text-xs font-bold uppercase tracking-wider text-slate-200 font-athletic">
            Play Impact Ticker
          </span>
        </div>
        <span className="text-[10px] text-slate-500 font-mono">
          {sortedPlays.length} Plays Logged
        </span>
      </div>

      {/* Plays Feed */}
      <div
        ref={containerRef}
        className="flex-1 overflow-y-auto p-4 space-y-3"
      >
        {sortedPlays.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-slate-500 gap-2">
            <RefreshCcw className="w-8 h-8 stroke-1 text-slate-700 animate-spin" />
            <p className="text-xs font-medium">Awaiting live play-by-play feed...</p>
          </div>
        ) : (
          sortedPlays.map((play) => {
            const isHighImpact = Math.abs(play.play_delta) >= 0.04;
            return (
              <div
                key={play.eventnum}
                id={`play-item-${play.eventnum}`}
                className={`p-3 rounded-xl border transition-all duration-300 ${
                  isHighImpact
                    ? "bg-stadium-black/90 border-court-orange/30 shadow-[inset_0_1px_10px_rgba(230,95,0,0.01)]"
                    : "bg-slate-900/30 border-slate-800/80 hover:border-slate-800"
                }`}
              >
                <div className="flex items-center justify-between gap-3 mb-1.5">
                  {/* Time metadata */}
                  <div className="flex items-center gap-1.5 text-[10px] font-mono text-slate-400 font-medium">
                    <span className="bg-slate-950 px-1.5 py-0.5 rounded border border-slate-800 text-court-orange font-bold font-athletic uppercase">
                      {getQuarterText(play.period)}
                    </span>
                    <span>{formatTime(play.seconds_remaining_in_period)}</span>
                    <span className="text-slate-600">|</span>
                    <span className="text-slate-300 font-bold">
                      {play.home_score} - {play.away_score}
                    </span>
                  </div>

                  {/* WP Delta Badge */}
                  <div
                    className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border flex items-center gap-1 ${getDeltaBadgeStyle(
                      play.play_delta
                    )}`}
                  >
                    {play.play_delta > 0 ? (
                      <TrendingUp className="w-3 h-3" />
                    ) : play.play_delta < 0 ? (
                      <TrendingDown className="w-3 h-3" />
                    ) : null}
                    <span>{formatDelta(play.play_delta)} WP</span>
                  </div>
                </div>

                <p className="text-xs text-slate-300 leading-normal tracking-wide font-light">
                  {play.description || "Play state change event recorded."}
                </p>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
