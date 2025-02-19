import { ResearchMessage } from "../lib/types";

type WebSocketCallbacks = {
  onMessage: (message: ResearchMessage) => void;
  onError: (error: string) => void;
  onStatusChange: (status: "connecting" | "connected" | "disconnected") => void;
};

export class WebSocketService {
  private socket: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private baseReconnectDelay = 1000;

  constructor(
    private readonly url: string,
    private readonly callbacks: WebSocketCallbacks
  ) {}

  connect() {
    this.callbacks.onStatusChange("connecting");
    this.socket = new WebSocket(this.url);

    this.socket.onopen = () => {
      this.reconnectAttempts = 0;
      this.callbacks.onStatusChange("connected");
    };

    this.socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data) as ResearchMessage;
        if (this.validateMessage(message)) {
          this.callbacks.onMessage(message);
        }
      } catch (error) {
        this.callbacks.onError("Invalid message format");
      }
    };

    this.socket.onerror = () => {
      this.callbacks.onError("WebSocket connection error");
    };

    this.socket.onclose = () => {
      this.handleReconnect();
    };
  }

  private validateMessage(message: any): message is ResearchMessage {
    return !!message?.node && !!message?.type && !!message?.timestamp;
  }

  private handleReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      const delay =
        this.baseReconnectDelay * Math.pow(2, this.reconnectAttempts);
      setTimeout(() => {
        this.reconnectAttempts++;
        this.connect();
      }, delay);
      this.callbacks.onStatusChange("disconnected");
    }
  }

  disconnect() {
    this.socket?.close();
    this.socket = null;
  }
}
