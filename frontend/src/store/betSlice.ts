import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import apiClient from "@/api/client";

function extractError(error: unknown, fallback: string): string {
  const err = error as { response?: { data?: { detail?: unknown } } };
  const detail = err.response?.data?.detail;
  if (!detail) return fallback;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((d: { msg?: string }) => d.msg || "").join(", ") || fallback;
  return fallback;
}

export interface BetOption {
  id: string;
  label: string;
  is_winner: boolean;
}

export interface BetParticipant {
  id: string;
  user_id: string;
  username: string;
  bet_option_id: string;
  amount: number;
  prize_amount: number | null;
}

export interface BetResponse {
  id: string;
  title: string;
  description?: string;
  category: string;
  status: "open" | "locked" | "pending_confirmation" | "voting" | "disputed" | "resolved" | "cancelled";
  resolution_type: "auto_api" | "voting";
  entry_amount: number;
  max_participants: number;
  closes_at: string;
  resolved_at?: string;
  created_at: string;
  creator_id: string;
  invite_token: string;
  options: BetOption[];
  current_participants: number;
  participations?: BetParticipant[];
  declared_winner_option_id?: string;
  declared_at?: string;
  confirmation_closes_at?: string;
}

interface CreateBetPayload {
  title: string;
  description?: string;
  category: string;
  options: string[];
  resolution_type: "auto_api" | "voting";
  entry_amount: number;
  max_participants: number;
  closes_at: string;
}

interface JoinBetPayload {
  betId: string;
  optionId: string;
}

interface CastVotePayload {
  betId: string;
  optionId: string;
}

interface DeclareWinnerPayload {
  betId: string;
  winningOptionId: string;
}

interface ContestResultPayload {
  betId: string;
  reason: string;
}

interface AcceptResultPayload {
  betId: string;
}

interface BetState {
  bets: BetResponse[];
  currentBet: BetResponse | null;
  loading: boolean;
  error: string | null;
}

const initialState: BetState = {
  bets: [],
  currentBet: null,
  loading: false,
  error: null,
};

export const fetchMyBets = createAsyncThunk(
  "bets/fetchMyBets",
  async (status: string | undefined, { rejectWithValue }) => {
    try {
      const params = status ? `?status=${status}` : "";
      const response = await apiClient.get(`/bets${params}`);
      return response.data;
    } catch (error: unknown) {
      return rejectWithValue(extractError(error, "Erro ao carregar desafios"));
    }
  }
);

export const fetchBetDetail = createAsyncThunk(
  "bets/fetchBetDetail",
  async (betId: string, { rejectWithValue }) => {
    try {
      const response = await apiClient.get(`/bets/${betId}`);
      return response.data;
    } catch (error: unknown) {
      return rejectWithValue(extractError(error, "Erro ao carregar desafio"));
    }
  }
);

export const fetchBetByInvite = createAsyncThunk(
  "bets/fetchBetByInvite",
  async (inviteToken: string, { rejectWithValue }) => {
    try {
      const response = await apiClient.get(`/bets/invite/${inviteToken}`);
      return response.data;
    } catch (error: unknown) {
      return rejectWithValue(extractError(error, "Erro ao carregar convite"));
    }
  }
);

export const createBet = createAsyncThunk(
  "bets/createBet",
  async (data: CreateBetPayload, { rejectWithValue }) => {
    try {
      const response = await apiClient.post("/bets", data);
      return response.data;
    } catch (error: unknown) {
      return rejectWithValue(extractError(error, "Erro ao criar desafio"));
    }
  }
);

export const joinBet = createAsyncThunk(
  "bets/joinBet",
  async ({ betId, optionId }: JoinBetPayload, { rejectWithValue }) => {
    try {
      const response = await apiClient.post(`/bets/${betId}/join`, {
        bet_option_id: optionId,
      });
      return response.data;
    } catch (error: unknown) {
      return rejectWithValue(extractError(error, "Erro ao entrar no desafio"));
    }
  }
);

export const castVote = createAsyncThunk(
  "bets/castVote",
  async ({ betId, optionId }: CastVotePayload, { rejectWithValue }) => {
    try {
      const response = await apiClient.post(`/bets/${betId}/vote`, {
        bet_option_id: optionId,
      });
      return response.data;
    } catch (error: unknown) {
      return rejectWithValue(extractError(error, "Erro ao votar"));
    }
  }
);

export const declareWinner = createAsyncThunk(
  "bets/declareWinner",
  async ({ betId, winningOptionId }: DeclareWinnerPayload, { rejectWithValue, dispatch }) => {
    try {
      await apiClient.post(`/bets/${betId}/declare-winner`, {
        winning_option_id: winningOptionId,
      });
      const refreshed = await dispatch(fetchBetDetail(betId));
      return refreshed.payload;
    } catch (error: unknown) {
      return rejectWithValue(extractError(error, "Erro ao declarar vencedor"));
    }
  }
);

export const contestResult = createAsyncThunk(
  "bets/contestResult",
  async ({ betId, reason }: ContestResultPayload, { rejectWithValue, dispatch }) => {
    try {
      await apiClient.post(`/bets/${betId}/contest`, { reason });
      const refreshed = await dispatch(fetchBetDetail(betId));
      return refreshed.payload;
    } catch (error: unknown) {
      return rejectWithValue(extractError(error, "Erro ao contestar resultado"));
    }
  }
);

export const acceptResult = createAsyncThunk(
  "bets/acceptResult",
  async ({ betId }: AcceptResultPayload, { rejectWithValue, dispatch }) => {
    try {
      await apiClient.post(`/bets/${betId}/accept`);
      const refreshed = await dispatch(fetchBetDetail(betId));
      return refreshed.payload;
    } catch (error: unknown) {
      return rejectWithValue(extractError(error, "Erro ao aceitar resultado"));
    }
  }
);

const betSlice = createSlice({
  name: "bets",
  initialState,
  reducers: {
    clearCurrentBet(state) {
      state.currentBet = null;
    },
    clearBetError(state) {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    // Fetch my bets
    builder.addCase(fetchMyBets.pending, (state) => {
      state.loading = true;
      state.error = null;
    });
    builder.addCase(fetchMyBets.fulfilled, (state, action) => {
      state.loading = false;
      state.bets = action.payload;
    });
    builder.addCase(fetchMyBets.rejected, (state, action) => {
      state.loading = false;
      state.error = action.payload as string;
    });

    // Fetch bet detail
    builder.addCase(fetchBetDetail.pending, (state) => {
      state.loading = true;
      state.error = null;
    });
    builder.addCase(fetchBetDetail.fulfilled, (state, action) => {
      state.loading = false;
      state.currentBet = action.payload;
    });
    builder.addCase(fetchBetDetail.rejected, (state, action) => {
      state.loading = false;
      state.error = action.payload as string;
    });

    // Fetch bet by invite
    builder.addCase(fetchBetByInvite.pending, (state) => {
      state.loading = true;
      state.error = null;
    });
    builder.addCase(fetchBetByInvite.fulfilled, (state, action) => {
      state.loading = false;
      state.currentBet = action.payload;
    });
    builder.addCase(fetchBetByInvite.rejected, (state, action) => {
      state.loading = false;
      state.error = action.payload as string;
    });

    // Create bet
    builder.addCase(createBet.pending, (state) => {
      state.loading = true;
      state.error = null;
    });
    builder.addCase(createBet.fulfilled, (state, action) => {
      state.loading = false;
      state.currentBet = action.payload;
      state.bets.unshift(action.payload);
    });
    builder.addCase(createBet.rejected, (state, action) => {
      state.loading = false;
      state.error = action.payload as string;
    });

    // Join bet
    builder.addCase(joinBet.pending, (state) => {
      state.loading = true;
      state.error = null;
    });
    builder.addCase(joinBet.fulfilled, (state, action) => {
      state.loading = false;
      state.currentBet = action.payload;
    });
    builder.addCase(joinBet.rejected, (state, action) => {
      state.loading = false;
      state.error = action.payload as string;
    });

    // Cast vote
    builder.addCase(castVote.pending, (state) => {
      state.loading = true;
      state.error = null;
    });
    builder.addCase(castVote.fulfilled, (state, action) => {
      state.loading = false;
      state.currentBet = action.payload;
    });
    builder.addCase(castVote.rejected, (state, action) => {
      state.loading = false;
      state.error = action.payload as string;
    });

    // Declare winner
    builder.addCase(declareWinner.pending, (state) => {
      state.loading = true;
      state.error = null;
    });
    builder.addCase(declareWinner.fulfilled, (state) => {
      state.loading = false;
    });
    builder.addCase(declareWinner.rejected, (state, action) => {
      state.loading = false;
      state.error = action.payload as string;
    });

    // Contest result
    builder.addCase(contestResult.pending, (state) => {
      state.loading = true;
      state.error = null;
    });
    builder.addCase(contestResult.fulfilled, (state) => {
      state.loading = false;
    });
    builder.addCase(contestResult.rejected, (state, action) => {
      state.loading = false;
      state.error = action.payload as string;
    });

    // Accept result
    builder.addCase(acceptResult.pending, (state) => {
      state.loading = true;
      state.error = null;
    });
    builder.addCase(acceptResult.fulfilled, (state) => {
      state.loading = false;
    });
    builder.addCase(acceptResult.rejected, (state, action) => {
      state.loading = false;
      state.error = action.payload as string;
    });
  },
});

export const { clearCurrentBet, clearBetError } = betSlice.actions;
export default betSlice.reducer;
