import { useSelector, useDispatch } from "react-redux";
import type { RootState, AppDispatch } from "@/store";
import {
  login as loginThunk,
  register as registerThunk,
  logout as logoutThunk,
  fetchMe as fetchMeThunk,
  clearError,
} from "@/store/authSlice";

export function useAuth() {
  const dispatch = useDispatch<AppDispatch>();
  const { user, accessToken, loading, error } = useSelector(
    (state: RootState) => state.auth
  );

  const isAuthenticated = !!accessToken;

  const login = async (email: string, password: string) => {
    const result = await dispatch(loginThunk({ email, password }));
    if (loginThunk.fulfilled.match(result)) {
      dispatch(fetchMeThunk());
    }
    return result;
  };

  const register = async (data: {
    email: string;
    username: string;
    password: string;
    phone: string;
    birth_date: string;
  }) => {
    const result = await dispatch(registerThunk(data));
    if (registerThunk.fulfilled.match(result)) {
      dispatch(fetchMeThunk());
    }
    return result;
  };

  const logout = () => dispatch(logoutThunk());
  const resetError = () => dispatch(clearError());

  return {
    user,
    isAuthenticated,
    loading,
    error,
    login,
    register,
    logout,
    resetError,
  };
}
