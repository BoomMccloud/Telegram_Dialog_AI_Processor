import { Message } from './index';

// Interface for dialog messages
export interface DialogMessage extends Message {
  dialog_id: string;
} 