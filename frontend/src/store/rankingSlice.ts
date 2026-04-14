import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import apiClient from "@/api/client";

export interface LeaderboardEntry {
  user_id: string;
  username: string;
  points: number;
  rank: number;
}

export interface UserRank {
  user_id: string;
  username: string;
  global: { user_id: string; rank: number | null; points: number };
  weekly: { user_id: string; rank: number | null; points: number };
}

export interface BadgeItem {
  id: string;
  name: string;
  description: string;
  icon: string;
  category: string;
  earned: boolean;
  awarded_at: string | null;
}

interface RankingState {
  leaderboard: LeaderboardEntry[];
  weeklyLeaderboard: LeaderboardEntry[];
  userRank: UserRank | null;
  badges: BadgeItem[];
  loading: boolean;
  error: string | null;
}

const initialState: RankingState = {
  leaderboard: [],
  weeklyLeaderboard: [],
  userRank: null,
  badges: [],
  loading: false,
  error: null,
};

export const fetchLeaderboard = createAsyncThunk(
  "ranking/fetchLeaderboard",
  async (_, { rejectWithValue }) => {
    try {
      const response = await apiClient.get("/ranking/");
      return response.data;
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      return rejectWithValue(
        err.response?.data?.detail || "Erro ao carregar ranking"
      );
    }
  }
);

export const fetchWeeklyLeaderboard = createAsyncThunk(
  "ranking/fetchWeeklyLeaderboard",
  async (_, { rejectWithValue }) => {
    try {
      const response = await apiClient.get("/ranking/weekly");
      return response.data;
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      return rejectWithValue(
        err.response?.data?.detail || "Erro ao carregar ranking semanal"
      );
    }
  }
);

export const fetchUserRank = createAsyncThunk(
  "ranking/fetchUserRank",
  async (_, { rejectWithValue }) => {
    try {
      const response = await apiClient.get("/ranking/me");
      return response.data;
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      return rejectWithValue(
        err.response?.data?.detail || "Erro ao carregar sua posicao"
      );
    }
  }
);

export const fetchUserBadges = createAsyncThunk(
  "ranking/fetchUserBadges",
  async (_, { rejectWithValue }) => {
    try {
      const response = await apiClient.get("/ranking/badges");
      return response.data;
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      return rejectWithValue(
        err.response?.data?.detail || "Erro ao carregar conquistas"
      );
    }
  }
);

const rankingSlice = createSlice({
  name: "ranking",
  initialState,
  reducers: {
    clearRankingError(state) {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    // Fetch leaderboard
    builder.addCase(fetchLeaderboard.pending, (state) => {
      state.loading = true;
      state.error = null;
    });
    builder.addCase(fetchLeaderboard.fulfilled, (state, action) => {
      state.loading = false;
      state.leaderboard = action.payload;
    });
    builder.addCase(fetchLeaderboard.rejected, (state, action) => {
      state.loading = false;
      state.error = action.payload as string;
    });

    // Fetch weekly leaderboard
    builder.addCase(fetchWeeklyLeaderboard.pending, (state) => {
      state.loading = true;
      state.error = null;
    });
    builder.addCase(fetchWeeklyLeaderboard.fulfilled, (state, action) => {
      state.loading = false;
      state.weeklyLeaderboard = action.payload;
    });
    builder.addCase(fetchWeeklyLeaderboard.rejected, (state, action) => {
      state.loading = false;
      state.error = action.payload as string;
    });

    // Fetch user rank
    builder.addCase(fetchUserRank.pending, (state) => {
      state.loading = true;
      state.error = null;
    });
    builder.addCase(fetchUserRank.fulfilled, (state, action) => {
      state.loading = false;
      state.userRank = action.payload;
    });
    builder.addCase(fetchUserRank.rejected, (state, action) => {
      state.loading = false;
      state.error = action.payload as string;
    });

    // Fetch badges
    builder.addCase(fetchUserBadges.pending, (state) => {
      state.loading = true;
      state.error = null;
    });
    builder.addCase(fetchUserBadges.fulfilled, (state, action) => {
      state.loading = false;
      state.badges = action.payload;
    });
    builder.addCase(fetchUserBadges.rejected, (state, action) => {
      state.loading = false;
      state.error = action.payload as string;
    });
  },
});

export const { clearRankingError } = rankingSlice.actions;
export default rankingSlice.reducer;
