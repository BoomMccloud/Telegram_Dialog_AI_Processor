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
export interface BaseDialog {
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
  is_processing_enabled: boolean;
  auto_send_enabled: boolean;
  telegram_dialog_id: string;
}

export interface DialogListResponse {
  dialogs: BaseDialog[]; // Use BaseDialog for the response, will be enhanced in the component
}

// Response types
export enum ResponseStatus {
  PENDING_APPROVAL = "pending_approval",
  APPROVED = "approved",
  REJECTED = "rejected",
  SENT = "sent",
  FAILED = "failed"
}

export interface Response {
  id: string;
  dialog_id: string;
  dialog_name: string;
  last_message_id: string;
  last_message_timestamp: string;
  suggested_response: string;
  edited_response: string | null;
  status: string;
  model_name: string;
  processed_at: string;
}

export interface ResponseListResponse {
  responses: Response[];
  total: number;
}

export interface ResponseUpdateRequest {
  edited_response: string;
}

// Message types
export interface Message {
  id: string;
  dialog_id: string;
  text: string;
  timestamp: string;
  is_unread: boolean;
  has_mention: boolean;
  sender: {
    id: string;
    name: string;
    is_self: boolean;
  };
}

export interface MessageListResponse {
  messages: Message[];
  total: number;
}

export interface MessageFetchOptions {
  limit?: number;
  unread_only?: boolean;
  mentions_only?: boolean;
}

export interface ResponseWithDialog extends Response {
  dialog_name: string;
  last_message_timestamp: string;
}

// Dialog selection response from backend
export interface DialogSelectionResponse {
  selection_id: string;
  dialog_id: string;
  dialog_name: string;
  is_active: boolean;
  is_processing_enabled: boolean;
  auto_send_enabled: boolean;
  created_at: string;
  updated_at: string;
} 