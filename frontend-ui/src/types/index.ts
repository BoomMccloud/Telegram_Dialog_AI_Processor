// Authentication types
export enum SessionStatus {
  PENDING = "PENDING",
  AUTHENTICATED = "AUTHENTICATED",
  ERROR = "ERROR",
  EXPIRED = "EXPIRED",
  UNAUTHENTICATED = "UNAUTHENTICATED"
}

export interface QRAuthResponse {
  session_id: string;
  qr_code: string;
  expires_at: string;
}

export interface SessionVerifyResponse {
  status: SessionStatus;
  telegram_id: number | null;
  expires_at: string;
  user: UserData | null;
  access_token?: string;  // Optional access token
  refresh_token?: string; // Optional refresh token
}

export interface UserData {
  id: string;
  telegram_id: number;
  username: string;
  first_name: string;
  last_name: string;
}

// Dialog types
export enum DialogType {
  PRIVATE = "PRIVATE",
  GROUP = "GROUP",
  CHANNEL = "CHANNEL"
}

export interface Dialog {
  id: number;
  telegram_dialog_id: string;
  name: string;
  unread_count: number;
  type: DialogType;
  is_processing_enabled: boolean;
  auto_send_enabled: boolean;
}

export interface DialogListResponse {
  dialogs: Dialog[];
} 