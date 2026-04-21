import { configureStore } from "@reduxjs/toolkit";
import authReducer from "./authSlice";
import walletReducer from "./walletSlice";
import betReducer from "./betSlice";
import chatReducer from "./chatSlice";
import rankingReducer from "./rankingSlice";
import adminReducer from "./adminSlice";
import sportsReducer from "./sportsSlice";

export const store = configureStore({
  reducer: {
    auth: authReducer,
    wallet: walletReducer,
    bets: betReducer,
    chat: chatReducer,
    ranking: rankingReducer,
    admin: adminReducer,
    sports: sportsReducer,
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
