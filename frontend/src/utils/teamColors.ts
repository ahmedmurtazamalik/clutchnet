export interface TeamColorInfo {
  primary: string;
  secondary: string;
  textColor: string;
  name: string;
}

export const NBA_TEAMS: Record<string, TeamColorInfo> = {
  BOS: { primary: "#007A33", secondary: "#BA9653", textColor: "#FFFFFF", name: "Boston Celtics" },
  LAL: { primary: "#552583", secondary: "#FDB927", textColor: "#FDB927", name: "LA Lakers" },
  CHI: { primary: "#C8102E", secondary: "#000000", textColor: "#FFFFFF", name: "Chicago Bulls" },
  GSW: { primary: "#1D428A", secondary: "#FFC72C", textColor: "#FFC72C", name: "Golden State Warriors" },
  NYK: { primary: "#006BB6", secondary: "#F58426", textColor: "#FFFFFF", name: "New York Knicks" },
  MIA: { primary: "#98002E", secondary: "#F9A01B", textColor: "#FFFFFF", name: "Miami Heat" },
  MIL: { primary: "#00471B", secondary: "#EEE1C6", textColor: "#EEE1C6", name: "Milwaukee Bucks" },
  PHX: { primary: "#1D1160", secondary: "#E56020", textColor: "#FFFFFF", name: "Phoenix Suns" },
  CLE: { primary: "#860038", secondary: "#FDBB30", textColor: "#FFFFFF", name: "Cleveland Cavaliers" },
  PHI: { primary: "#006BB6", secondary: "#ED174C", textColor: "#FFFFFF", name: "Philadelphia 76ers" },
  BKN: { primary: "#000000", secondary: "#FFFFFF", textColor: "#FFFFFF", name: "Brooklyn Nets" },
  LAC: { primary: "#C8102E", secondary: "#1D428A", textColor: "#FFFFFF", name: "LA Clippers" },
  DAL: { primary: "#00538C", secondary: "#002B5E", textColor: "#FFFFFF", name: "Dallas Mavericks" },
  DEN: { primary: "#0E2240", secondary: "#FEC524", textColor: "#FFFFFF", name: "Denver Nuggets" },
  SAC: { primary: "#5A2D81", secondary: "#63727A", textColor: "#FFFFFF", name: "Sacramento Kings" },
  IND: { primary: "#002D62", secondary: "#FDBB30", textColor: "#FFFFFF", name: "Indiana Pacers" },
  NOP: { primary: "#0C2340", secondary: "#C8102E", textColor: "#FFFFFF", name: "New Orleans Pelicans" },
  MIN: { primary: "#0C2340", secondary: "#236192", textColor: "#FFFFFF", name: "Minnesota Timberwolves" },
  OKC: { primary: "#007AC1", secondary: "#EF3B24", textColor: "#FFFFFF", name: "Oklahoma City Thunder" },
  POR: { primary: "#E03A3E", secondary: "#000000", textColor: "#FFFFFF", name: "Portland Trail Blazers" },
  MEM: { primary: "#5D76A9", secondary: "#12BBF4", textColor: "#FFFFFF", name: "Memphis Grizzlies" },
  UTA: { primary: "#002B5C", secondary: "#F9A01B", textColor: "#FFFFFF", name: "Utah Jazz" },
  CHA: { primary: "#1D1160", secondary: "#00788C", textColor: "#FFFFFF", name: "Charlotte Hornets" },
  ORL: { primary: "#0077C0", secondary: "#C4CED4", textColor: "#FFFFFF", name: "Orlando Magic" },
  ATL: { primary: "#E03A3E", secondary: "#C1D32F", textColor: "#FFFFFF", name: "Atlanta Hawks" },
  TOR: { primary: "#A11E36", secondary: "#000000", textColor: "#FFFFFF", name: "Toronto Raptors" },
  HOU: { primary: "#CE1141", secondary: "#000000", textColor: "#FFFFFF", name: "Houston Rockets" },
  DET: { primary: "#C8102E", secondary: "#1D428A", textColor: "#FFFFFF", name: "Detroit Pistons" },
  SAS: { primary: "#000000", secondary: "#C4CED4", textColor: "#FFFFFF", name: "San Antonio Spurs" },
  WAS: { primary: "#002B5C", secondary: "#E31837", textColor: "#FFFFFF", name: "Washington Wizards" },
};

export function getTeamColorInfo(abbr: string | null | undefined): TeamColorInfo {
  if (!abbr) {
    return { primary: "#E65F00", secondary: "#1E1E20", textColor: "#FFFFFF", name: "NBA" };
  }
  const cleanAbbr = abbr.trim().toUpperCase();
  // Handle some common name mismatches
  if (cleanAbbr === "BKN" || cleanAbbr === "BRK") return NBA_TEAMS.BKN;
  if (cleanAbbr === "CHO" || cleanAbbr === "CHA") return NBA_TEAMS.CHA;
  if (cleanAbbr === "NOP" || cleanAbbr === "NOH") return NBA_TEAMS.NOP;
  if (cleanAbbr === "PHX" || cleanAbbr === "PHO") return NBA_TEAMS.PHX;
  if (cleanAbbr === "UTA" || cleanAbbr === "UTAH") return NBA_TEAMS.UTA;

  return NBA_TEAMS[cleanAbbr] || { primary: "#E65F00", secondary: "#1E1E20", textColor: "#FFFFFF", name: cleanAbbr };
}
