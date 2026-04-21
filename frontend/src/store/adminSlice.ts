import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import apiClient from "@/api/client";

export interface AdminUser {
  id: string;
  email: string;
  username: string;
  phone: string;
  is_admin: boolean;
  is_active: boolean;
  total_points: number;
  created_at: string;
}

export interface BetOption {
  id: string;
  label: string;
  is_winner: boolean;
}

export interface AdminBet {
  id: string;
  title: string;
  category: string;
  status: string;
  current_participants: number;
  pot_total: number;
  created_at: string;
  options: BetOption[];
}

export interface DashboardStats {
  total_users: number;
  total_bets: number;
  active_bets: number;
  total_revenue: number;
  total_deposits: number;
}

export interface FeeConfig {
  fee_type: "percent" | "fixed";
  fee_value: number;
}

interface AdminState {
  stats: DashboardStats | null;
  users: AdminUser[];
  bets: AdminBet[];
  feeConfig: FeeConfig | null;
  loading: boolean;
  error: string | null;
}

const initialState: AdminState = {
  stats: null,
  users: [],
  bets: [],
  feeConfig: null,
  loading: false,
  error: null,
};

export const fetchDashboardStats = createAsyncThunk(
  "admin/fetchDashboardStats",
  async (_, { rejectWithValue }) => {
    try {
      const response = await apiClient.get("/admin/dashboard");
      return response.data;
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      return rejectWithValue(
        err.response?.data?.detail || "Erro ao carregar estatísticas"
      );
    }
  }
);

export const fetchAdminUsers = createAsyncThunk(
  "admin/fetchAdminUsers",
  async (
    params: { search?: string; page?: number },
    { rejectWithValue }
  ) => {
    try {
      const skip = ((params.page || 1) - 1) * 20;
      const query = new URLSearchParams({ skip: String(skip), limit: "20" });
      if (params.search) query.set("search", params.search);
      const response = await apiClient.get(`/admin/users?${query}`);
      return response.data;
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      return rejectWithValue(
        err.response?.data?.detail || "Erro ao carregar usuários"
      );
    }
  }
);

export const fetchAdminBets = createAsyncThunk(
  "admin/fetchAdminBets",
  async (
    params: { status?: string; page?: number },
    { rejectWithValue }
  ) => {
    try {
      const skip = ((params.page || 1) - 1) * 20;
      const query = new URLSearchParams({ skip: String(skip), limit: "20" });
      if (params.status) query.set("status", params.status);
      const response = await apiClient.get(`/admin/bets?${query}`);
      return response.data;
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      return rejectWithValue(
        err.response?.data?.detail || "Erro ao carregar desafios"
      );
    }
  }
);

export const toggleUserActive = createAsyncThunk(
  "admin/toggleUserActive",
  async (
    params: { userId: string; isActive: boolean },
    { rejectWithValue }
  ) => {
    try {
      const response = await apiClient.put(
        `/admin/users/${params.userId}/toggle-active`,
        { is_active: params.isActive }
      );
      return { userId: params.userId, isActive: response.data.is_active };
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      return rejectWithValue(
        err.response?.data?.detail || "Erro ao alterar status do usuário"
      );
    }
  }
);

export const makeAdmin = createAsyncThunk(
  "admin/makeAdmin",
  async (userId: string, { rejectWithValue }) => {
    try {
      const response = await apiClient.put(
        `/admin/users/${userId}/make-admin`
      );
      return { userId, isAdmin: response.data.is_admin };
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      return rejectWithValue(
        err.response?.data?.detail || "Erro ao promover usuário"
      );
    }
  }
);

export const fetchFeeConfig = createAsyncThunk(
  "admin/fetchFeeConfig",
  async (_, { rejectWithValue }) => {
    try {
      const response = await apiClient.get("/admin/config/fee");
      return response.data;
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      return rejectWithValue(
        err.response?.data?.detail || "Erro ao carregar configuração de taxa"
      );
    }
  }
);

export const updateFeeConfig = createAsyncThunk(
  "admin/updateFeeConfig",
  async (
    params: { fee_type: string; fee_value: number },
    { rejectWithValue }
  ) => {
    try {
      const response = await apiClient.put("/admin/config/fee", params);
      return response.data.value;
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      return rejectWithValue(
        err.response?.data?.detail || "Erro ao atualizar taxa"
      );
    }
  }
);

export const forceResolveBet = createAsyncThunk(
  "admin/forceResolveBet",
  async (
    params: { betId: string; winningOptionId: string },
    { rejectWithValue }
  ) => {
    try {
      const response = await apiClient.post(
        `/admin/bets/${params.betId}/force-resolve`,
        { winning_option_id: params.winningOptionId }
      );
      return { betId: params.betId, status: response.data.status };
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      return rejectWithValue(
        err.response?.data?.detail || "Erro ao resolver desafio"
      );
    }
  }
);

export const forceCancelBet = createAsyncThunk(
  "admin/forceCancelBet",
  async (betId: string, { rejectWithValue }) => {
    try {
      const response = await apiClient.post(
        `/admin/bets/${betId}/force-cancel`
      );
      return { betId, status: response.data.status };
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      return rejectWithValue(
        err.response?.data?.detail || "Erro ao cancelar desafio"
      );
    }
  }
);

const adminSlice = createSlice({
  name: "admin",
  initialState,
  reducers: {
    clearAdminError(state) {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    // Dashboard stats
    builder.addCase(fetchDashboardStats.pending, (state) => {
      state.loading = true;
      state.error = null;
    });
    builder.addCase(fetchDashboardStats.fulfilled, (state, action) => {
      state.loading = false;
      state.stats = action.payload;
    });
    builder.addCase(fetchDashboardStats.rejected, (state, action) => {
      state.loading = false;
      state.error = action.payload as string;
    });

    // Users
    builder.addCase(fetchAdminUsers.pending, (state) => {
      state.loading = true;
      state.error = null;
    });
    builder.addCase(fetchAdminUsers.fulfilled, (state, action) => {
      state.loading = false;
      state.users = action.payload;
    });
    builder.addCase(fetchAdminUsers.rejected, (state, action) => {
      state.loading = false;
      state.error = action.payload as string;
    });

    // Toggle user active
    builder.addCase(toggleUserActive.fulfilled, (state, action) => {
      const user = state.users.find((u) => u.id === action.payload.userId);
      if (user) user.is_active = action.payload.isActive;
    });

    // Make admin
    builder.addCase(makeAdmin.fulfilled, (state, action) => {
      const user = state.users.find((u) => u.id === action.payload.userId);
      if (user) user.is_admin = action.payload.isAdmin;
    });

    // Bets
    builder.addCase(fetchAdminBets.pending, (state) => {
      state.loading = true;
      state.error = null;
    });
    builder.addCase(fetchAdminBets.fulfilled, (state, action) => {
      state.loading = false;
      state.bets = action.payload;
    });
    builder.addCase(fetchAdminBets.rejected, (state, action) => {
      state.loading = false;
      state.error = action.payload as string;
    });

    // Force resolve
    builder.addCase(forceResolveBet.fulfilled, (state, action) => {
      const bet = state.bets.find((b) => b.id === action.payload.betId);
      if (bet) bet.status = action.payload.status;
    });

    // Force cancel
    builder.addCase(forceCancelBet.fulfilled, (state, action) => {
      const bet = state.bets.find((b) => b.id === action.payload.betId);
      if (bet) bet.status = action.payload.status;
    });

    // Fee config
    builder.addCase(fetchFeeConfig.pending, (state) => {
      state.loading = true;
      state.error = null;
    });
    builder.addCase(fetchFeeConfig.fulfilled, (state, action) => {
      state.loading = false;
      state.feeConfig = action.payload;
    });
    builder.addCase(fetchFeeConfig.rejected, (state, action) => {
      state.loading = false;
      state.error = action.payload as string;
    });

    // Update fee config
    builder.addCase(updateFeeConfig.fulfilled, (state, action) => {
      state.feeConfig = action.payload;
    });
  },
});

export const { clearAdminError } = adminSlice.actions;
export default adminSlice.reducer;
