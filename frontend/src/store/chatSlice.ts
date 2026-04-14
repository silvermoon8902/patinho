import { createSlice, createAsyncThunk, PayloadAction } from "@reduxjs/toolkit";
import apiClient from "@/api/client";

export interface ChatMessage {
  id: string;
  bet_id: string;
  user_id: string;
  username: string;
  content: string;
  is_system: boolean;
  created_at: string;
}

interface ChatState {
  messages: ChatMessage[];
  connected: boolean;
  loading: boolean;
  error: string | null;
}

const initialState: ChatState = {
  messages: [],
  connected: false,
  loading: false,
  error: null,
};

export const fetchMessages = createAsyncThunk(
  "chat/fetchMessages",
  async (
    { betId, page }: { betId: string; page: number },
    { rejectWithValue }
  ) => {
    try {
      const response = await apiClient.get(
        `/chat/${betId}/messages?page=${page}`
      );
      return response.data;
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      return rejectWithValue(
        err.response?.data?.detail || "Erro ao carregar mensagens"
      );
    }
  }
);

const chatSlice = createSlice({
  name: "chat",
  initialState,
  reducers: {
    addMessage(state, action: PayloadAction<ChatMessage>) {
      const exists = state.messages.some((m) => m.id === action.payload.id);
      if (!exists) {
        state.messages.push(action.payload);
      }
    },
    setMessages(state, action: PayloadAction<ChatMessage[]>) {
      state.messages = action.payload;
    },
    setConnected(state, action: PayloadAction<boolean>) {
      state.connected = action.payload;
    },
    clearChat(state) {
      state.messages = [];
      state.connected = false;
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder.addCase(fetchMessages.pending, (state) => {
      state.loading = true;
      state.error = null;
    });
    builder.addCase(fetchMessages.fulfilled, (state, action) => {
      state.loading = false;
      state.messages = action.payload;
    });
    builder.addCase(fetchMessages.rejected, (state, action) => {
      state.loading = false;
      state.error = action.payload as string;
    });
  },
});

export const { addMessage, setMessages, setConnected, clearChat } =
  chatSlice.actions;
export default chatSlice.reducer;
