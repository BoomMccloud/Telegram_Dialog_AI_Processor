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
  PRIVATE = "private",
  GROUP = "group",
  CHANNEL = "channel"
}

// Base Dialog interface matching backend's TelegramDialog model
interface BaseDialog {
  id: number;
  name: string;
  unread_count: number;
  is_group: boolean;
  is_channel: boolean;
  is_user: boolean;
  type: string;
}

// Extended Dialog interface with UI-specific properties
export interface Dialog extends BaseDialog {
  // UI state properties not in the backend
  priority: number;
  is_processing_enabled: boolean;
  auto_send_enabled: boolean;
  telegram_dialog_id: string;
}

export interface DialogListResponse {
  dialogs: BaseDialog[]; // Use BaseDialog for the response, will be enhanced in the component
} 