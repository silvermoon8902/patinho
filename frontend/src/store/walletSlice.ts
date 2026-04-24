import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import apiClient from "@/api/client";

export interface WalletResponse {
  id: string;
  user_id: string;
  balance: number;
  locked_balance: number;
  currency: string;
  created_at: string;
  updated_at: string;
}

export interface TransactionResponse {
  id: string;
  wallet_id: string;
  type: "deposit" | "withdrawal" | "bet_placed" | "bet_won" | "bet_refund";
  amount: number;
  description: string;
  created_at: string;
}

export interface PaymentResponse {
  id: string;
  amount: number;
  status: string;
  pix_qr_code: string | null;
  pix_copy_paste: string | null;
  expires_at: string;
}

interface WalletState {
  wallet: WalletResponse | null;
  transactions: TransactionResponse[];
  depositPayment: PaymentResponse | null;
  loading: boolean;
  error: string | null;
}

const initialState: WalletState = {
  wallet: null,
  transactions: [],
  depositPayment: null,
  loading: false,
  error: null,
};

export const fetchWallet = createAsyncThunk(
  "wallet/fetchWallet",
  async (_, { rejectWithValue }) => {
    try {
      const response = await apiClient.get("/wallet");
      return response.data;
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      return rejectWithValue(
        err.response?.data?.detail || "Erro ao carregar carteira"
      );
    }
  }
);

export const createDeposit = createAsyncThunk(
  "wallet/createDeposit",
  async (amount: number, { rejectWithValue }) => {
    try {
      const response = await apiClient.post("/wallet/deposit", { amount });
      return response.data;
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      return rejectWithValue(
        err.response?.data?.detail || "Erro ao criar depósito"
      );
    }
  }
);

export const fetchTransactions = createAsyncThunk(
  "wallet/fetchTransactions",
  async (page: number = 1, { rejectWithValue }) => {
    try {
      const response = await apiClient.get(`/wallet/transactions?page=${page}`);
      return response.data;
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      return rejectWithValue(
        err.response?.data?.detail || "Erro ao carregar extrato"
      );
    }
  }
);

/**
 * Ask the backend to poll Mercado Pago for a specific deposit and credit
 * the wallet if MP reports it approved. Webhook-independent — used when the
 * VPS can't receive MP webhooks (HTTP/IP).
 */
export const reconcileDeposit = createAsyncThunk(
  "wallet/reconcileDeposit",
  async (paymentId: string, { rejectWithValue }) => {
    try {
      const response = await apiClient.post(
        `/wallet/deposit/${paymentId}/reconcile`
      );
      return response.data as WalletResponse;
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      return rejectWithValue(
        err.response?.data?.detail || "Erro ao verificar pagamento"
      );
    }
  }
);

/** Fallback: reconcile every pending deposit for the authed user at once. */
export const reconcilePending = createAsyncThunk(
  "wallet/reconcilePending",
  async (_, { rejectWithValue }) => {
    try {
      const response = await apiClient.post("/wallet/reconcile-pending");
      return response.data as WalletResponse;
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      return rejectWithValue(
        err.response?.data?.detail || "Erro ao atualizar saldo"
      );
    }
  }
);

const walletSlice = createSlice({
  name: "wallet",
  initialState,
  reducers: {
    clearDepositPayment(state) {
      state.depositPayment = null;
    },
    clearWalletError(state) {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    // Fetch wallet
    builder.addCase(fetchWallet.pending, (state) => {
      state.loading = true;
      state.error = null;
    });
    builder.addCase(fetchWallet.fulfilled, (state, action) => {
      state.loading = false;
      state.wallet = action.payload;
    });
    builder.addCase(fetchWallet.rejected, (state, action) => {
      state.loading = false;
      state.error = action.payload as string;
    });

    // Create deposit
    builder.addCase(createDeposit.pending, (state) => {
      state.loading = true;
      state.error = null;
    });
    builder.addCase(createDeposit.fulfilled, (state, action) => {
      state.loading = false;
      state.depositPayment = action.payload;
    });
    builder.addCase(createDeposit.rejected, (state, action) => {
      state.loading = false;
      state.error = action.payload as string;
    });

    // Fetch transactions
    builder.addCase(fetchTransactions.pending, (state) => {
      state.loading = true;
      state.error = null;
    });
    builder.addCase(fetchTransactions.fulfilled, (state, action) => {
      state.loading = false;
      state.transactions = action.payload;
    });
    builder.addCase(fetchTransactions.rejected, (state, action) => {
      state.loading = false;
      state.error = action.payload as string;
    });
  },
});

export const { clearDepositPayment, clearWalletError } = walletSlice.actions;
export default walletSlice.reducer;
