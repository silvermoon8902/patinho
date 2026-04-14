import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import apiClient from "@/api/client";

export interface BetOption {
  id: string;
  text: string;
  participant_count: number;
}

export interface BetParticipant {
  id: string;
  user_id: string;
  username: string;
  option_id: string;
  amount: number;
  joined_at: string;
}

export interface BetResponse {
  id: string;
  title: string;
  description?: string;
  category: string;
  status: "open" | "locked" | "voting" | "disputed" | "resolved" | "cancelled";
  resolution_type: "auto" | "voting";
  min_entry: number;
  max_entry: number;
  max_participants: number;
  closes_at: string;
  created_at: string;
  creator_id: string;
  creator_username: string;
  invite_token: string;
  options: BetOption[];
  participants: BetParticipant[];
  total_pot: number;
  participant_count: number;
  winning_option_id?: string;
}

interface CreateBetPayload {
  title: string;
  description?: string;
  category: string;
  options: string[];
  resolution_type: "auto" | "voting";
  min_entry: number;
  max_entry: number;
  max_participants: number;
  closes_at: string;
}

interface JoinBetPayload {
  betId: string;
  optionId: string;
  amount: number;
}

interface CastVotePayload {
  betId: string;
  optionId: string;
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
      const err = error as { response?: { data?: { detail?: string } } };
      return rejectWithValue(
        err.response?.data?.detail || "Erro ao carregar apostas"
      );
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
      const err = error as { response?: { data?: { detail?: string } } };
      return rejectWithValue(
        err.response?.data?.detail || "Erro ao carregar aposta"
      );
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
      const err = error as { response?: { data?: { detail?: string } } };
      return rejectWithValue(
        err.response?.data?.detail || "Erro ao carregar convite"
      );
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
      const err = error as { response?: { data?: { detail?: string } } };
      return rejectWithValue(
        err.response?.data?.detail || "Erro ao criar aposta"
      );
    }
  }
);

export const joinBet = createAsyncThunk(
  "bets/joinBet",
  async ({ betId, optionId, amount }: JoinBetPayload, { rejectWithValue }) => {
    try {
      const response = await apiClient.post(`/bets/${betId}/join`, {
        option_id: optionId,
        amount,
      });
      return response.data;
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      return rejectWithValue(
        err.response?.data?.detail || "Erro ao entrar na aposta"
      );
    }
  }
);

export const castVote = createAsyncThunk(
  "bets/castVote",
  async ({ betId, optionId }: CastVotePayload, { rejectWithValue }) => {
    try {
      const response = await apiClient.post(`/bets/${betId}/vote`, {
        option_id: optionId,
      });
      return response.data;
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      return rejectWithValue(
        err.response?.data?.detail || "Erro ao votar"
      );
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
  },
});

export const { clearCurrentBet, clearBetError } = betSlice.actions;
export default betSlice.reducer;
