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

interface SportsState {
  leagues: SportLeague[];
  leaguesLoading: boolean;
  leaguesError: string | null;

  fixtures: SportFixture[];
  fixturesLoading: boolean;
  fixturesError: string | null;
  fixturesLeagueId: string | null;

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

export interface CreateSportBetPayload {
  fixture_id: string;
  template: string;
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
      state.createError = null;
    },
    clearFixtures(state) {
      state.fixtures = [];
      state.fixturesLeagueId = null;
      state.fixturesError = null;
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

export const { clearSportsError, clearFixtures } = sportsSlice.actions;
export default sportsSlice.reducer;
