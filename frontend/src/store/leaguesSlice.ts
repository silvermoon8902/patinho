import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import apiClient from "@/api/client";

function extractError(error: unknown, fallback: string): string {
  const err = error as { response?: { data?: { detail?: unknown } } };
  const detail = err.response?.data?.detail;
  if (!detail) return fallback;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail))
    return detail.map((d: { msg?: string }) => d.msg || "").join(", ") || fallback;
  return fallback;
}

export interface LeagueMember {
  user_id: string;
  username: string;
  joined_at: string;
  is_owner: boolean;
}

export interface LeagueResponse {
  id: string;
  owner_id: string;
  name: string;
  description: string | null;
  invite_code: string;
  created_at: string;
  member_count: number;
}

export interface LeagueDetailResponse extends LeagueResponse {
  members: LeagueMember[];
  is_member: boolean;
  is_owner: boolean;
}

export interface LeagueRankingEntry {
  user_id: string;
  username: string;
  total_points: number;
  wins: number;
  participations: number;
}

export type InviteStatus =
  | "idle"
  | "success"
  | "error"
  | "already"
  | "notfound";

interface LeagueState {
  myLeagues: LeagueResponse[];
  currentLeague: LeagueDetailResponse | null;
  ranking: LeagueRankingEntry[];
  loading: boolean;
  error: string | null;
  createLoading: boolean;
  createError: string | null;
  inviteStatus: InviteStatus;
}

const initialState: LeagueState = {
  myLeagues: [],
  currentLeague: null,
  ranking: [],
  loading: false,
  error: null,
  createLoading: false,
  createError: null,
  inviteStatus: "idle",
};

export const fetchMyLeagues = createAsyncThunk(
  "leagues/fetchMyLeagues",
  async (_: void, { rejectWithValue }) => {
    try {
      const response = await apiClient.get("/leagues");
      return response.data as LeagueResponse[];
    } catch (error: unknown) {
      return rejectWithValue(extractError(error, "Erro ao carregar ligas"));
    }
  }
);

export const fetchLeagueDetail = createAsyncThunk(
  "leagues/fetchLeagueDetail",
  async (leagueId: string, { rejectWithValue }) => {
    try {
      const response = await apiClient.get(`/leagues/${leagueId}`);
      return response.data as LeagueDetailResponse;
    } catch (error: unknown) {
      return rejectWithValue(extractError(error, "Erro ao carregar liga"));
    }
  }
);

export const fetchLeagueRanking = createAsyncThunk(
  "leagues/fetchLeagueRanking",
  async (leagueId: string, { rejectWithValue }) => {
    try {
      const response = await apiClient.get(`/leagues/${leagueId}/ranking`);
      return response.data as LeagueRankingEntry[];
    } catch (error: unknown) {
      return rejectWithValue(extractError(error, "Erro ao carregar ranking"));
    }
  }
);

export const createLeague = createAsyncThunk(
  "leagues/createLeague",
  async (
    data: { name: string; description?: string },
    { rejectWithValue }
  ) => {
    try {
      const response = await apiClient.post("/leagues", data);
      return response.data as LeagueResponse;
    } catch (error: unknown) {
      return rejectWithValue(extractError(error, "Erro ao criar liga"));
    }
  }
);

export const inviteToLeague = createAsyncThunk(
  "leagues/inviteToLeague",
  async (
    { leagueId, identifier }: { leagueId: string; identifier: string },
    { rejectWithValue }
  ) => {
    try {
      const response = await apiClient.post(
        `/leagues/${leagueId}/invite`,
        { identifier }
      );
      return response.data as { status: string };
    } catch (error: unknown) {
      return rejectWithValue(extractError(error, "Erro ao convidar"));
    }
  }
);

export const joinLeague = createAsyncThunk(
  "leagues/joinLeague",
  async (
    { inviteCode }: { inviteCode: string },
    { rejectWithValue }
  ) => {
    try {
      const response = await apiClient.post("/leagues/join", {
        invite_code: inviteCode,
      });
      return response.data as LeagueResponse;
    } catch (error: unknown) {
      return rejectWithValue(
        extractError(error, "Erro ao entrar na liga")
      );
    }
  }
);

export const leaveLeague = createAsyncThunk(
  "leagues/leaveLeague",
  async (leagueId: string, { rejectWithValue }) => {
    try {
      await apiClient.post(`/leagues/${leagueId}/leave`);
      return leagueId;
    } catch (error: unknown) {
      return rejectWithValue(extractError(error, "Erro ao sair da liga"));
    }
  }
);

export const deleteLeague = createAsyncThunk(
  "leagues/deleteLeague",
  async (leagueId: string, { rejectWithValue }) => {
    try {
      await apiClient.delete(`/leagues/${leagueId}`);
      return leagueId;
    } catch (error: unknown) {
      return rejectWithValue(extractError(error, "Erro ao excluir liga"));
    }
  }
);

export const removeLeagueMember = createAsyncThunk(
  "leagues/removeLeagueMember",
  async (
    { leagueId, userId }: { leagueId: string; userId: string },
    { rejectWithValue }
  ) => {
    try {
      await apiClient.delete(`/leagues/${leagueId}/members/${userId}`);
      return { leagueId, userId };
    } catch (error: unknown) {
      return rejectWithValue(extractError(error, "Erro ao remover membro"));
    }
  }
);

const leaguesSlice = createSlice({
  name: "leagues",
  initialState,
  reducers: {
    clearLeagueError(state) {
      state.error = null;
      state.createError = null;
    },
    clearCurrentLeague(state) {
      state.currentLeague = null;
      state.ranking = [];
    },
    resetInviteStatus(state) {
      state.inviteStatus = "idle";
    },
  },
  extraReducers: (builder) => {
    // fetchMyLeagues
    builder.addCase(fetchMyLeagues.pending, (state) => {
      state.loading = true;
      state.error = null;
    });
    builder.addCase(fetchMyLeagues.fulfilled, (state, action) => {
      state.loading = false;
      state.myLeagues = action.payload;
    });
    builder.addCase(fetchMyLeagues.rejected, (state, action) => {
      state.loading = false;
      state.error = action.payload as string;
    });

    // fetchLeagueDetail
    builder.addCase(fetchLeagueDetail.pending, (state) => {
      state.loading = true;
      state.error = null;
    });
    builder.addCase(fetchLeagueDetail.fulfilled, (state, action) => {
      state.loading = false;
      state.currentLeague = action.payload;
    });
    builder.addCase(fetchLeagueDetail.rejected, (state, action) => {
      state.loading = false;
      state.error = action.payload as string;
    });

    // fetchLeagueRanking
    builder.addCase(fetchLeagueRanking.pending, (state) => {
      state.loading = true;
    });
    builder.addCase(fetchLeagueRanking.fulfilled, (state, action) => {
      state.loading = false;
      state.ranking = action.payload;
    });
    builder.addCase(fetchLeagueRanking.rejected, (state, action) => {
      state.loading = false;
      state.error = action.payload as string;
    });

    // createLeague
    builder.addCase(createLeague.pending, (state) => {
      state.createLoading = true;
      state.createError = null;
    });
    builder.addCase(createLeague.fulfilled, (state, action) => {
      state.createLoading = false;
      state.myLeagues.unshift(action.payload);
    });
    builder.addCase(createLeague.rejected, (state, action) => {
      state.createLoading = false;
      state.createError = action.payload as string;
    });

    // inviteToLeague
    builder.addCase(inviteToLeague.pending, (state) => {
      state.inviteStatus = "idle";
    });
    builder.addCase(inviteToLeague.fulfilled, (state, action) => {
      const s = action.payload?.status;
      if (s === "added") state.inviteStatus = "success";
      else if (s === "already_member") state.inviteStatus = "already";
      else if (s === "user_not_found") state.inviteStatus = "notfound";
      else state.inviteStatus = "error";
    });
    builder.addCase(inviteToLeague.rejected, (state, action) => {
      state.inviteStatus = "error";
      state.error = action.payload as string;
    });

    // joinLeague
    builder.addCase(joinLeague.pending, (state) => {
      state.loading = true;
      state.error = null;
    });
    builder.addCase(joinLeague.fulfilled, (state, action) => {
      state.loading = false;
      const exists = state.myLeagues.some((l) => l.id === action.payload.id);
      if (!exists) state.myLeagues.unshift(action.payload);
    });
    builder.addCase(joinLeague.rejected, (state, action) => {
      state.loading = false;
      state.error = action.payload as string;
    });

    // leaveLeague
    builder.addCase(leaveLeague.fulfilled, (state, action) => {
      state.myLeagues = state.myLeagues.filter(
        (l) => l.id !== action.payload
      );
      if (state.currentLeague?.id === action.payload) {
        state.currentLeague = null;
      }
    });
    builder.addCase(leaveLeague.rejected, (state, action) => {
      state.error = action.payload as string;
    });

    // deleteLeague
    builder.addCase(deleteLeague.fulfilled, (state, action) => {
      state.myLeagues = state.myLeagues.filter(
        (l) => l.id !== action.payload
      );
      if (state.currentLeague?.id === action.payload) {
        state.currentLeague = null;
      }
    });
    builder.addCase(deleteLeague.rejected, (state, action) => {
      state.error = action.payload as string;
    });

    // removeLeagueMember
    builder.addCase(removeLeagueMember.fulfilled, (state, action) => {
      if (
        state.currentLeague &&
        state.currentLeague.id === action.payload.leagueId
      ) {
        state.currentLeague.members = state.currentLeague.members.filter(
          (m) => m.user_id !== action.payload.userId
        );
        state.currentLeague.member_count = Math.max(
          0,
          state.currentLeague.member_count - 1
        );
      }
    });
    builder.addCase(removeLeagueMember.rejected, (state, action) => {
      state.error = action.payload as string;
    });
  },
});

export const { clearLeagueError, clearCurrentLeague, resetInviteStatus } =
  leaguesSlice.actions;
export default leaguesSlice.reducer;
