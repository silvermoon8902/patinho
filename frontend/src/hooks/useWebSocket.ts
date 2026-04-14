import { useEffect, useRef, useCallback } from "react";
import { useSelector, useDispatch } from "react-redux";
import type { RootState, AppDispatch } from "@/store";
import { addMessage, setConnected } from "@/store/chatSlice";

const RECONNECT_DELAY = 3000;
const MAX_RECONNECT_ATTEMPTS = 5;

export function useWebSocket(betId: string | undefined) {
  const dispatch = useDispatch<AppDispatch>();
  const accessToken = useSelector((state: RootState) => state.auth.accessToken);
  const messages = useSelector((state: RootState) => state.chat.messages);
  const connected = useSelector((state: RootState) => state.chat.connected);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout>>();

  const connect = useCallback(() => {
    if (!betId || !accessToken) return;

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    const url = `${protocol}//${host}/ws/chat/${betId}?token=${accessToken}`;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      dispatch(setConnected(true));
      reconnectAttemptsRef.current = 0;
    };

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        dispatch(addMessage(message));
      } catch {
        // ignore invalid messages
      }
    };

    ws.onclose = () => {
      dispatch(setConnected(false));
      wsRef.current = null;

      if (reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
        reconnectAttemptsRef.current += 1;
        reconnectTimeoutRef.current = setTimeout(connect, RECONNECT_DELAY);
      }
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [betId, accessToken, dispatch]);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      dispatch(setConnected(false));
    };
  }, [connect, dispatch]);

  const sendMessage = useCallback(
    (content: string) => {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ content }));
      }
    },
    []
  );

  return { messages, sendMessage, connected };
}
