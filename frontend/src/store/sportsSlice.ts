import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import apiClient from "@/api/client";
import type { BetResponse } from "./betSlice";

function extractError(error: unknown, fallback: string): string {
  const err = error as { response?: { data?: { detail?: unknown } } };
  const detail = err.response?.data?.detail;
  if (!detail) return fallback;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail))
    return (
      detail.map((d: { msg?: string }) => d.msg || "").join(", ") || fallback
    );
  return fallback;
}

export interface SportLeague {
  id: string;
  name: string;
  api_id: number;
}

export interface SportFixture {
  fixture_id: string;
  date: string;
  home_team: string;
  away_team: string;
  home_logo: string | null;
  away_logo: string | null;
  league_name?: string | null;
}

export interface SportRace {
  race_id: string;
  date: string;
  circuit_name: string;
  circuit_location: string;
  competition_name: string;
}

export interface SportDriver {
  driver_id: string;
  name: string;
  team_name: string;
}

export interface TennisMatch {
  match_id: string;
  date: string;
  tour: string;
  player1_name: string;
  player2_name: string;
}

interface SportsState {
  leagues: SportLeague[];
  leaguesLoading: boolean;
  leaguesError: string | null;

  fixtures: SportFixture[];
  fixturesLoading: boolean;
  fixturesError: string | null;
  fixturesLeagueId: string | null;

  races: SportRace[];
  racesLoading: boolean;
  racesError: string | null;
  racesSeason: number | null;

  drivers: SportDriver[];
  driversLoading: boolean;
  driversError: string | null;
  driversRaceId: string | null;

  tennisMatches: TennisMatch[];
  tennisMatchesLoading: boolean;
  tennisMatchesError: string | null;
  tennisMatchesTour: string | null;

  createLoading: boolean;
  createError: string | null;
}

const initialState: SportsState = {
  leagues: [],
  leaguesLoading: false,
  leaguesError: null,

  fixtures: [],
  fixturesLoading: false,
  fixturesError: null,
  fixturesLeagueId: null,

  races: [],
  racesLoading: false,
  racesError: null,
  racesSeason: null,

  drivers: [],
  driversLoading: false,
  driversError: null,
  driversRaceId: null,

  tennisMatches: [],
  tennisMatchesLoading: false,
  tennisMatchesError: null,
  tennisMatchesTour: null,

  createLoading: false,
  createError: null,
};

export const fetchLeagues = createAsyncThunk(
  "sports/fetchLeagues",
  async (_: void, { rejectWithValue }) => {
    try {
      const response = await apiClient.get("/sports/leagues");
      return response.data as SportLeague[];
    } catch (error: unknown) {
      return rejectWithValue(extractError(error, "Erro ao carregar ligas"));
    }
  }
);

interface FetchFixturesArgs {
  leagueId: string;
  season?: number;
}

export const fetchFixtures = createAsyncThunk(
  "sports/fetchFixtures",
  async ({ leagueId, season }: FetchFixturesArgs, { rejectWithValue }) => {
    try {
      const params = season ? `?season=${season}` : "";
      const response = await apiClient.get(
        `/sports/leagues/${leagueId}/fixtures${params}`
      );
      return {
        leagueId,
        fixtures: response.data as SportFixture[],
      };
    } catch (error: unknown) {
      return rejectWithValue(extractError(error, "Erro ao carregar partidas"));
    }
  }
);

export const fetchRaces = createAsyncThunk(
  "sports/fetchRaces",
  async (season: number, { rejectWithValue }) => {
    try {
      const response = await apiClient.get(
        `/sports/f1/races?season=${season}`
      );
      return {
        season,
        races: response.data as SportRace[],
      };
    } catch (error: unknown) {
      return rejectWithValue(extractError(error, "Erro ao carregar corridas"));
    }
  }
);

export const fetchRaceDrivers = createAsyncThunk(
  "sports/fetchRaceDrivers",
  async (raceId: string, { rejectWithValue }) => {
    try {
      const response = await apiClient.get(
        `/sports/f1/races/${raceId}/drivers`
      );
      return {
        raceId,
        drivers: response.data as SportDriver[],
      };
    } catch (error: unknown) {
      return rejectWithValue(extractError(error, "Erro ao carregar pilotos"));
    }
  }
);

interface FetchTennisMatchesArgs {
  tour?: string;
  season?: number;
}

export const fetchTennisMatches = createAsyncThunk(
  "sports/fetchTennisMatches",
  async (
    { tour = "", season = 2026 }: FetchTennisMatchesArgs,
    { rejectWithValue }
  ) => {
    try {
      const params = new URLSearchParams();
      if (tour) params.set("tour", tour);
      if (season) params.set("season", String(season));
      const qs = params.toString() ? `?${params.toString()}` : "";
      const response = await apiClient.get(`/sports/tennis/matches${qs}`);
      return {
        tour,
        matches: response.data as TennisMatch[],
      };
    } catch (error: unknown) {
      return rejectWithValue(
        extractError(error, "Erro ao carregar partidas de tênis")
      );
    }
  }
);

export interface CreateSportBetPayload {
  template: string;
  fixture_id?: string | null;
  race_id?: string | null;
  tennis_match_id?: string | null;
  driver_names?: string[] | null;
  entry_amount: number;
  max_participants: number;
}

export const createSportBet = createAsyncThunk(
  "sports/createSportBet",
  async (data: CreateSportBetPayload, { rejectWithValue }) => {
    try {
      const response = await apiClient.post("/bets/sport", data);
      return response.data as BetResponse;
    } catch (error: unknown) {
      return rejectWithValue(
        extractError(error, "Erro ao criar previsão esportiva")
      );
    }
  }
);

const sportsSlice = createSlice({
  name: "sports",
  initialState,
  reducers: {
    clearSportsError(state) {
      state.leaguesError = null;
      state.fixturesError = null;
      state.racesError = null;
      state.driversError = null;
      state.tennisMatchesError = null;
      state.createError = null;
    },
    clearFixtures(state) {
      state.fixtures = [];
      state.fixturesLeagueId = null;
      state.fixturesError = null;
    },
    clearRaces(state) {
      state.races = [];
      state.racesSeason = null;
      state.racesError = null;
    },
    clearDrivers(state) {
      state.drivers = [];
      state.driversRaceId = null;
      state.driversError = null;
    },
    clearTennisMatches(state) {
      state.tennisMatches = [];
      state.tennisMatchesTour = null;
      state.tennisMatchesError = null;
    },
  },
  extraReducers: (builder) => {
    // Leagues
    builder.addCase(fetchLeagues.pending, (state) => {
      state.leaguesLoading = true;
      state.leaguesError = null;
    });
    builder.addCase(fetchLeagues.fulfilled, (state, action) => {
      state.leaguesLoading = false;
      state.leagues = action.payload;
    });
    builder.addCase(fetchLeagues.rejected, (state, action) => {
      state.leaguesLoading = false;
      state.leaguesError = action.payload as string;
    });

    // Fixtures
    builder.addCase(fetchFixtures.pending, (state, action) => {
      state.fixturesLoading = true;
      state.fixturesError = null;
      state.fixturesLeagueId = action.meta.arg.leagueId;
    });
    builder.addCase(fetchFixtures.fulfilled, (state, action) => {
      state.fixturesLoading = false;
      state.fixtures = action.payload.fixtures;
      state.fixturesLeagueId = action.payload.leagueId;
    });
    builder.addCase(fetchFixtures.rejected, (state, action) => {
      state.fixturesLoading = false;
      state.fixturesError = action.payload as string;
    });

    // Races
    builder.addCase(fetchRaces.pending, (state, action) => {
      state.racesLoading = true;
      state.racesError = null;
      state.racesSeason = action.meta.arg;
    });
    builder.addCase(fetchRaces.fulfilled, (state, action) => {
      state.racesLoading = false;
      state.races = action.payload.races;
      state.racesSeason = action.payload.season;
    });
    builder.addCase(fetchRaces.rejected, (state, action) => {
      state.racesLoading = false;
      state.racesError = action.payload as string;
    });

    // Drivers
    builder.addCase(fetchRaceDrivers.pending, (state, action) => {
      state.driversLoading = true;
      state.driversError = null;
      state.driversRaceId = action.meta.arg;
    });
    builder.addCase(fetchRaceDrivers.fulfilled, (state, action) => {
      state.driversLoading = false;
      state.drivers = action.payload.drivers;
      state.driversRaceId = action.payload.raceId;
    });
    builder.addCase(fetchRaceDrivers.rejected, (state, action) => {
      state.driversLoading = false;
      state.driversError = action.payload as string;
    });

    // Tennis matches
    builder.addCase(fetchTennisMatches.pending, (state, action) => {
      state.tennisMatchesLoading = true;
      state.tennisMatchesError = null;
      state.tennisMatchesTour = action.meta.arg.tour || "";
    });
    builder.addCase(fetchTennisMatches.fulfilled, (state, action) => {
      state.tennisMatchesLoading = false;
      state.tennisMatches = action.payload.matches;
      state.tennisMatchesTour = action.payload.tour;
    });
    builder.addCase(fetchTennisMatches.rejected, (state, action) => {
      state.tennisMatchesLoading = false;
      state.tennisMatchesError = action.payload as string;
    });

    // Create sport bet
    builder.addCase(createSportBet.pending, (state) => {
      state.createLoading = true;
      state.createError = null;
    });
    builder.addCase(createSportBet.fulfilled, (state) => {
      state.createLoading = false;
    });
    builder.addCase(createSportBet.rejected, (state, action) => {
      state.createLoading = false;
      state.createError = action.payload as string;
    });
  },
});

export const {
  clearSportsError,
  clearFixtures,
  clearRaces,
  clearDrivers,
  clearTennisMatches,
} = sportsSlice.actions;
export default sportsSlice.reducer;
