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
import { getTeamColorInfo } from "../utils/teamColors";
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
    period: play.period,
    displayTime: `Q${play.period} ${Math.floor(play.seconds_remaining_in_period / 60)}:${Math.floor(
      play.seconds_remaining_in_period % 60
    )
      .toString()
      .padStart(2, "0")}`,
  }));
  
  // Find indices where quarters start to use as custom ticks
  const ticks: number[] = [];
  let currentPeriod = 0;
  chartData.forEach((d) => {
    if (d.period !== currentPeriod) {
      ticks.push(d.index);
      currentPeriod = d.period;
    }
  });

  const homeColorInfo = getTeamColorInfo(homeTeam);
  const awayColorInfo = getTeamColorInfo(awayTeam);

  // Tooltip custom renderer for premium style
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      const prob = payload[0].value;
      const homeFavored = prob >= 50;
      const favoredTeam = homeFavored ? homeTeam : awayTeam;
      const margin = homeFavored ? prob - 50 : 50 - prob;
      const confidence = (50 + margin).toFixed(1);
      const favoredColor = homeFavored ? homeColorInfo.primary : awayColorInfo.primary;

      return (
        <div className="p-4 bg-slate-900/95 border border-slate-800 rounded-xl shadow-2xl backdrop-blur-md max-w-xs space-y-2">
          <div className="flex justify-between items-center border-b border-slate-800 pb-2">
            <span className="text-[10px] font-mono text-slate-400 font-semibold">{data.displayTime}</span>
            <span className="text-xs font-mono font-bold text-slate-200">
              {data.homeScore} - {data.awayScore}
            </span>
          </div>

          <p className="text-xs text-slate-300 font-light leading-relaxed">
            {data.description || "Play event recorded."}
          </p>

          <div className="pt-2 flex flex-col gap-1 text-[10px] uppercase font-bold tracking-wider font-athletic">
            <div className="flex justify-between">
              <span className="text-slate-400">Favored Team:</span>
              <span style={{ color: favoredColor }}>
                {favoredTeam}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Win Probability:</span>
              <span style={{ color: favoredColor }}>
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
    <div className="w-full stadium-panel p-6 rounded-2xl border border-slate-800 bg-stadium-charcoal/80 space-y-4">
      {/* Header Info */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="space-y-1">
          <h2 className="text-base font-bold uppercase tracking-wider text-slate-200 font-athletic">
            Win Probability Pulse Chart
          </h2>
          <p className="text-xs text-slate-400 font-light leading-relaxed">
            Live win probability updates. The chart splits at the <strong>50% Toss-Up line</strong>: area fills <strong>upward</strong> (increasing to 100% at the top) for {homeColorInfo.name}, and <strong>downward</strong> (increasing to 100% at the bottom) for {awayColorInfo.name}.
          </p>
        </div>
        <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-wider font-athletic">
          <div className="flex items-center gap-1.5" style={{ color: homeColorInfo.primary }}>
            <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: homeColorInfo.primary }} />
            <span>{homeTeam || "HOME"} favored (&gt;50%)</span>
          </div>
          <span className="text-slate-700">|</span>
          <div className="flex items-center gap-1.5" style={{ color: awayColorInfo.primary }}>
            <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: awayColorInfo.primary }} />
            <span>{awayTeam || "AWAY"} favored (&lt;50%)</span>
          </div>
        </div>
      </div>

      {/* Chart container */}
      <div className="h-72 w-full relative pt-2">
        {chartData.length === 0 ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-slate-500 gap-2">
            <HelpCircle className="w-10 h-10 stroke-1 text-slate-700 animate-pulse" />
            <p className="text-xs font-medium">Select a game feed and start playback to plot probability curves...</p>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart
              data={chartData}
              margin={{ top: 10, right: 10, left: -25, bottom: 0 }}
            >
              <defs>
                <linearGradient id="probabilityGlow" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={homeColorInfo.primary} stopOpacity={0.35} />
                  <stop offset="45%" stopColor={homeColorInfo.primary} stopOpacity={0.06} />
                  <stop offset="50%" stopColor="#18181b" stopOpacity={0.02} />
                  <stop offset="55%" stopColor={awayColorInfo.primary} stopOpacity={0.06} />
                  <stop offset="100%" stopColor={awayColorInfo.primary} stopOpacity={0.35} />
                </linearGradient>
                <linearGradient id="strokeGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={homeColorInfo.primary} />
                  <stop offset="48%" stopColor={homeColorInfo.primary} />
                  <stop offset="50%" stopColor="#71717a" />
                  <stop offset="52%" stopColor={awayColorInfo.primary} />
                  <stop offset="100%" stopColor={awayColorInfo.primary} />
                </linearGradient>
              </defs>

              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              
              <XAxis
                dataKey="index"
                ticks={ticks}
                tickFormatter={(idx) => {
                  const dataPoint = chartData[idx];
                  if (!dataPoint) return "";
                  if (dataPoint.period <= 4) return `Q${dataPoint.period}`;
                  return `OT${dataPoint.period - 4}`;
                }}
                axisLine={{ stroke: "rgba(255,255,255,0.08)" }}
                tickLine={false}
                style={{
                  fontSize: "9px",
                  fill: "rgba(148, 163, 184, 0.5)",
                  fontFamily: "var(--font-inter)",
                }}
              />

              <YAxis
                domain={[0, 100]}
                ticks={[0, 25, 50, 75, 100]}
                axisLine={false}
                tickLine={false}
                tickFormatter={(val) => {
                  if (val === 50) return "50%";
                  return val > 50 ? `${val}%` : `${100 - val}%`;
                }}
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
                stroke="url(#strokeGradient)"
                strokeWidth={2.5}
                fill="url(#probabilityGlow)"
                dot={false}
                activeDot={{ r: 4, strokeWidth: 0, fill: "#ffffff" }}
                baseValue={50}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
