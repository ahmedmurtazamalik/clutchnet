import { useEffect, useState, useRef } from "react";

export interface PlayEvent {
  eventnum: number;
  period: number;
  seconds_remaining_in_period: number;
  seconds_remaining_in_game: number;
  home_score: number;
  away_score: number;
  score_margin: number;
  possession: number;
  home_timeouts_remaining: number;
  away_timeouts_remaining: number;
  home_fouls: number;
  away_fouls: number;
  home_pregame_rating: number;
  away_pregame_rating: number;
  is_overtime: number;
  is_clutch: number;
  largest_lead: number;
  lead_changes: number;
  home_pts_last_3_min: number;
  away_pts_last_3_min: number;
  home_team_abbr: string;
  away_team_abbr: string;
  matchup: string;
  win_probability: number;
  play_delta: number;
  description: string;
  is_finished?: boolean;
}

export function useWebSocket(gameId: string | null) {
  const [plays, setPlays] = useState<PlayEvent[]>([]);
  const [latestEvent, setLatestEvent] = useState<PlayEvent | null>(null);
  const [status, setStatus] = useState<"connecting" | "connected" | "disconnected">("disconnected");
  
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!gameId) {
      setPlays([]);
      setLatestEvent(null);
      setStatus("disconnected");
      if (wsRef.current) {
        wsRef.current.close();
      }
      return;
    }

    // Reset state for the new game
    setPlays([]);
    setLatestEvent(null);
    setStatus("connecting");

    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
    const wsProtocol = backendUrl.startsWith("https") ? "wss" : "ws";
    const cleanBackendUrl = backendUrl.replace(/^https?:\/\//, "");
    const wsUrl = `${wsProtocol}://${cleanBackendUrl}/ws/live-game/${gameId}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setStatus("connected");
      console.log(`[WS] Connected to game: ${gameId}`);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        // Handle termination frame / completion message
        if (data.is_finished) {
          setLatestEvent((prev) => {
            if (prev) {
              const finishedEvent = {
                ...prev,
                eventnum: prev.eventnum + 1,
                description: data.description || "GAME COMPLETED",
                is_finished: true,
                home_score: data.home_score ?? prev.home_score,
                away_score: data.away_score ?? prev.away_score,
              };
              setPlays((prevPlays) => [...prevPlays, finishedEvent]);
              return finishedEvent;
            }
            return null;
          });
          return;
        }

        // It is a regular PlayEvent
        const play = data as PlayEvent;
        setLatestEvent(play);
        setPlays((prevPlays) => {
          // Prevent duplicates by checking eventnum
          if (prevPlays.some((p) => p.eventnum === play.eventnum)) {
            return prevPlays;
          }
          const updated = [...prevPlays, play];
          // Sort by eventnum just to be safe
          return updated.sort((a, b) => a.eventnum - b.eventnum);
        });
      } catch (err) {
        console.error("[WS] Error parsing message:", err);
      }
    };

    ws.onerror = (err) => {
      console.error("[WS] WebSocket error:", err);
      setStatus("disconnected");
    };

    ws.onclose = () => {
      setStatus("disconnected");
      console.log(`[WS] Closed connection for game: ${gameId}`);
    };

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [gameId]);

  return { plays, latestEvent, status };
}
