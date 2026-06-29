"use client";

import React from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import { PlayEvent } from "../hooks/useWebSocket";
import { HelpCircle } from "lucide-react";

interface PulseChartProps {
  plays: PlayEvent[];
  homeTeam: string;
  awayTeam: string;
}

export function PulseChart({ plays, homeTeam, awayTeam }: PulseChartProps) {
  // Map plays to chart data structure
  const chartData = plays.map((play, idx) => ({
    index: idx,
    eventnum: play.eventnum,
    probability: play.win_probability * 100, // percentage: 0 to 100
    homeScore: play.home_score,
    awayScore: play.away_score,
    description: play.description,
    displayTime: `Q${play.period} ${Math.floor(play.seconds_remaining_in_period / 60)}:${Math.floor(
      play.seconds_remaining_in_period % 60
    )
      .toString()
      .padStart(2, "0")}`,
  }));

  // Tooltip custom renderer for premium style
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      const prob = payload[0].value;
      const homeFavored = prob >= 50;
      const favoredTeam = homeFavored ? homeTeam : awayTeam;
      const margin = homeFavored ? prob - 50 : 50 - prob;
      const confidence = (50 + margin).toFixed(1);

      return (
        <div className="p-4 bg-slate-950/95 border border-slate-800 rounded-xl shadow-2xl backdrop-blur-md max-w-xs space-y-2">
          <div className="flex justify-between items-center border-b border-slate-900 pb-2">
            <span className="text-[10px] font-mono text-slate-400 font-semibold">{data.displayTime}</span>
            <span className="text-xs font-mono font-bold text-slate-200">
              {data.homeScore} - {data.awayScore}
            </span>
          </div>

          <p className="text-xs text-slate-300 font-light leading-normal leading-relaxed">
            {data.description || "Play event recorded."}
          </p>

          <div className="pt-2 flex flex-col gap-1 text-[10px] uppercase font-bold tracking-wider">
            <div className="flex justify-between">
              <span className="text-slate-400">Favored Team:</span>
              <span className={homeFavored ? "text-neon-blue" : "text-neon-purple"}>
                {favoredTeam}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Win Probability:</span>
              <span className={homeFavored ? "text-neon-blue" : "text-neon-purple"}>
                {confidence}%
              </span>
            </div>
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="w-full glass-panel p-6 rounded-2xl border border-slate-800 space-y-4">
      {/* Header Info */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="space-y-1">
          <h2 className="text-base font-bold uppercase tracking-wider text-slate-200">
            Win Probability Pulse Chart
          </h2>
          <p className="text-xs text-slate-400 font-light leading-relaxed">
            Live updates mapping the home team&apos;s win expectation (0% represents complete away advantage, 100% represents home certainty).
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs font-bold font-mono">
          <div className="flex items-center gap-1.5 text-neon-blue">
            <span className="w-2.5 h-2.5 bg-neon-blue rounded-full" />
            <span>{homeTeam || "HOME"} favored (&gt;50%)</span>
          </div>
          <span className="text-slate-600">|</span>
          <div className="flex items-center gap-1.5 text-neon-purple">
            <span className="w-2.5 h-2.5 bg-neon-purple rounded-full" />
            <span>{awayTeam || "AWAY"} favored (&lt;50%)</span>
          </div>
        </div>
      </div>

      {/* Chart container */}
      <div className="h-72 w-full relative pt-2">
        {chartData.length === 0 ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-slate-500 gap-2">
            <HelpCircle className="w-10 h-10 stroke-1 text-slate-600 animate-pulse" />
            <p className="text-xs font-medium">Select a game feed and start playback to plot probability curves...</p>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart
              data={chartData}
              margin={{ top: 10, right: 10, left: -25, bottom: 0 }}
            >
              <defs>
                {/* 
                  Vertical gradient matching the full range [0, 100].
                  Top (y1=0) is Home WP 100% -> Colored cyan.
                  Middle (offset=50%) is toss-up -> transitions.
                  Bottom (y2=100) is Home WP 0% (Away WP 100%) -> Colored purple.
                */}
                <linearGradient id="probabilityGlow" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#06b6d4" stopOpacity={0.4} />
                  <stop offset="45%" stopColor="#06b6d4" stopOpacity={0.08} />
                  <stop offset="50%" stopColor="#1e293b" stopOpacity={0.02} />
                  <stop offset="55%" stopColor="#d946ef" stopOpacity={0.08} />
                  <stop offset="100%" stopColor="#d946ef" stopOpacity={0.4} />
                </linearGradient>
              </defs>

              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              
              <XAxis
                dataKey="index"
                hide={true}
              />

              <YAxis
                domain={[0, 100]}
                tickCount={5}
                axisLine={false}
                tickLine={false}
                tickFormatter={(val) => `${val}%`}
                style={{
                  fontSize: "10px",
                  fill: "rgba(148, 163, 184, 0.7)",
                  fontFamily: "var(--font-mono)",
                }}
              />

              <Tooltip content={<CustomTooltip />} cursor={{ stroke: "rgba(255,255,255,0.08)", strokeWidth: 1.5 }} />

              {/* Toss up reference line at 50% */}
              <ReferenceLine
                y={50}
                stroke="rgba(255,255,255,0.15)"
                strokeDasharray="4 4"
                label={{
                  value: "Toss Up",
                  position: "insideBottomRight",
                  fill: "rgba(148, 163, 184, 0.4)",
                  fontSize: 9,
                  fontFamily: "var(--font-inter)",
                }}
              />

              <Area
                type="monotone"
                dataKey="probability"
                stroke="#06b6d4"
                strokeWidth={2}
                fill="url(#probabilityGlow)"
                dot={false}
                activeDot={{ r: 4, strokeWidth: 0, fill: "#ffffff" }}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
