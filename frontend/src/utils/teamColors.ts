export interface TeamColorInfo {
  primary: string;
  secondary: string;
  textColor: string;
  name: string;
}

export const NBA_TEAMS: Record<string, TeamColorInfo> = {
  BOS: { primary: "#00A94F", secondary: "#BA9653", textColor: "#FFFFFF", name: "Boston Celtics" }, // Brighter Green
  LAL: { primary: "#FDB927", secondary: "#552583", textColor: "#552583", name: "LA Lakers" }, // Swapped to Gold Primary for readability
  CHI: { primary: "#FF1A3D", secondary: "#000000", textColor: "#FFFFFF", name: "Chicago Bulls" }, // Brighter Red
  GSW: { primary: "#2463E2", secondary: "#FFC72C", textColor: "#FFC72C", name: "Golden State Warriors" }, // Brighter Blue
  NYK: { primary: "#0088EC", secondary: "#F58426", textColor: "#FFFFFF", name: "New York Knicks" }, // Brighter Blue
  MIA: { primary: "#F9A01B", secondary: "#98002E", textColor: "#FFFFFF", name: "Miami Heat" }, // Swapped to Orange/Yellow Primary
  MIL: { primary: "#EEE1C6", secondary: "#00471B", textColor: "#00471B", name: "Milwaukee Bucks" }, // Swapped to Cream Primary for dark background
  PHX: { primary: "#E56020", secondary: "#1D1160", textColor: "#FFFFFF", name: "Phoenix Suns" }, // Swapped to Orange Primary for dark background
  CLE: { primary: "#C1004F", secondary: "#FDBB30", textColor: "#FFFFFF", name: "Cleveland Cavaliers" }, // Brighter Wine/Red
  PHI: { primary: "#0088EC", secondary: "#ED174C", textColor: "#FFFFFF", name: "Philadelphia 76ers" }, // Brighter Blue
  BKN: { primary: "#FFFFFF", secondary: "#000000", textColor: "#000000", name: "Brooklyn Nets" }, // Swapped to White Primary for dark background
  LAC: { primary: "#FF1A3D", secondary: "#1D428A", textColor: "#FFFFFF", name: "LA Clippers" }, // Brighter Red
  DAL: { primary: "#007BC4", secondary: "#002B5E", textColor: "#FFFFFF", name: "Dallas Mavericks" }, // Brighter Blue
  DEN: { primary: "#FEC524", secondary: "#0E2240", textColor: "#FFFFFF", name: "Denver Nuggets" }, // Swapped to Gold Primary
  SAC: { primary: "#8B5CF6", secondary: "#63727A", textColor: "#FFFFFF", name: "Sacramento Kings" }, // Brighter Purple (Tailwind Violet-500)
  IND: { primary: "#FDBB30", secondary: "#002D62", textColor: "#FFFFFF", name: "Indiana Pacers" }, // Swapped to Gold Primary
  NOP: { primary: "#C8102E", secondary: "#0C2340", textColor: "#FFFFFF", name: "New Orleans Pelicans" }, // Swapped to Red Primary
  MIN: { primary: "#236192", secondary: "#0C2340", textColor: "#FFFFFF", name: "Minnesota Timberwolves" }, // Swapped to Slate Blue Primary
  OKC: { primary: "#00A1FF", secondary: "#EF3B24", textColor: "#FFFFFF", name: "Oklahoma City Thunder" }, // Brighter Blue
  POR: { primary: "#FF1F22", secondary: "#000000", textColor: "#FFFFFF", name: "Portland Trail Blazers" }, // Brighter Red
  MEM: { primary: "#5D76A9", secondary: "#12BBF4", textColor: "#FFFFFF", name: "Memphis Grizzlies" },
  UTA: { primary: "#F9A01B", secondary: "#002B5C", textColor: "#FFFFFF", name: "Utah Jazz" }, // Swapped to Gold Primary
  CHA: { primary: "#00A8C1", secondary: "#1D1160", textColor: "#FFFFFF", name: "Charlotte Hornets" }, // Swapped to Teal Primary
  ORL: { primary: "#0099FF", secondary: "#C4CED4", textColor: "#FFFFFF", name: "Orlando Magic" }, // Brighter Blue
  ATL: { primary: "#FF474A", secondary: "#C1D32F", textColor: "#FFFFFF", name: "Atlanta Hawks" }, // Brighter Red
  TOR: { primary: "#C72441", secondary: "#000000", textColor: "#FFFFFF", name: "Toronto Raptors" }, // Brighter Red
  HOU: { primary: "#FF1E56", secondary: "#000000", textColor: "#FFFFFF", name: "Houston Rockets" }, // Brighter Red
  DET: { primary: "#FF1A3D", secondary: "#1D428A", textColor: "#FFFFFF", name: "Detroit Pistons" }, // Brighter Red
  SAS: { primary: "#C4CED4", secondary: "#000000", textColor: "#000000", name: "San Antonio Spurs" }, // Swapped to Silver Primary
  WAS: { primary: "#E31837", secondary: "#002B5C", textColor: "#FFFFFF", name: "Washington Wizards" }, // Swapped to Red Primary
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
