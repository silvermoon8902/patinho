import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import apiClient from "@/api/client";

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

export interface TournamentFixture {
  fixture_id: string;
  phase: string;
  kickoff_at: string;
  locks_at: string;
  home_team: string | null;
  away_team: string | null;
  home_logo: string | null;
  away_logo: string | null;
  my_palpite: {
    home_score: number | null;
    away_score: number | null;
    points_earned: number;
  } | null;
}

export interface RankingEntry {
  user_id: string;
  username: string;
  points: number;
  rank: number;
}

interface TournamentState {
  fixtures: TournamentFixture[];
  ranking: RankingEntry[];
  loading: boolean;
  saving: boolean;
  error: string | null;
}

const initialState: TournamentState = {
  fixtures: [],
  ranking: [],
  loading: false,
  saving: false,
  error: null,
};

export const createTournamentBet = createAsyncThunk(
  "tournament/create",
  async (
    data: { template_code: string; entry_amount: number; max_participants: number },
    { rejectWithValue }
  ) => {
    try {
      const res = await apiClient.post("/bets/tournament", data);
      return res.data as { id: string; title: string; invite_token: string };
    } catch (error: unknown) {
      return rejectWithValue(extractError(error, "Erro ao criar Bolão"));
    }
  }
);

export const fetchTournamentFixtures = createAsyncThunk(
  "tournament/fetchFixtures",
  async (betId: string, { rejectWithValue }) => {
    try {
      const res = await apiClient.get(`/bets/${betId}/palpites`);
      return res.data.fixtures as TournamentFixture[];
    } catch (error: unknown) {
      return rejectWithValue(extractError(error, "Erro ao carregar partidas"));
    }
  }
);

export const submitPalpitesBulk = createAsyncThunk(
  "tournament/submitBulk",
  async (
    args: {
      betId: string;
      palpites: Array<{
        fixture_id: string;
        home_score: number;
        away_score: number;
        phase?: string;
        locks_at?: string | null;
      }>;
    },
    { rejectWithValue }
  ) => {
    try {
      const res = await apiClient.post(
        `/bets/${args.betId}/palpites/bulk`,
        { palpites: args.palpites }
      );
      return res.data as { saved: number; rejected_locked: number };
    } catch (error: unknown) {
      return rejectWithValue(extractError(error, "Erro ao salvar palpites"));
    }
  }
);

export const submitChampionPalpite = createAsyncThunk(
  "tournament/submitChampion",
  async (args: { betId: string; team: string }, { rejectWithValue }) => {
    try {
      const res = await apiClient.post(
        `/bets/${args.betId}/champion-palpite`,
        { team: args.team }
      );
      return res.data as { predicted_champion: string };
    } catch (error: unknown) {
      return rejectWithValue(extractError(error, "Erro ao salvar campeão"));
    }
  }
);

export const fetchTournamentRanking = createAsyncThunk(
  "tournament/fetchRanking",
  async (betId: string, { rejectWithValue }) => {
    try {
      const res = await apiClient.get(`/bets/${betId}/ranking`);
      return res.data.ranking as RankingEntry[];
    } catch (error: unknown) {
      return rejectWithValue(extractError(error, "Erro ao carregar ranking"));
    }
  }
);

const tournamentSlice = createSlice({
  name: "tournament",
  initialState,
  reducers: {
    clearTournamentError(state) {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder.addCase(fetchTournamentFixtures.pending, (state) => {
      state.loading = true;
      state.error = null;
    });
    builder.addCase(fetchTournamentFixtures.fulfilled, (state, action) => {
      state.loading = false;
      state.fixtures = action.payload;
    });
    builder.addCase(fetchTournamentFixtures.rejected, (state, action) => {
      state.loading = false;
      state.error = action.payload as string;
    });

    builder.addCase(submitPalpitesBulk.pending, (state) => {
      state.saving = true;
    });
    builder.addCase(submitPalpitesBulk.fulfilled, (state) => {
      state.saving = false;
    });
    builder.addCase(submitPalpitesBulk.rejected, (state, action) => {
      state.saving = false;
      state.error = action.payload as string;
    });

    builder.addCase(fetchTournamentRanking.fulfilled, (state, action) => {
      state.ranking = action.payload;
    });
    builder.addCase(fetchTournamentRanking.rejected, (state, action) => {
      state.error = action.payload as string;
    });
  },
});

export const { clearTournamentError } = tournamentSlice.actions;
export default tournamentSlice.reducer;
