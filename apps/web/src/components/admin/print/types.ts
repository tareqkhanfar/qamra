/** Print batches (API: routers/admin_print_batches.py). */

export type OrderBrief = {
  id: string;
  code: string;
  status: string;
  city: string | null;
  organization: string | null;
  books: number;
  approved: number;
  ready: boolean;
};

export type BatchRow = {
  id: string;
  code: string;
  batch_date: string;
  status: "open" | "sent" | "printing" | "done";
  organization: string | null;
  orders: number;
  books: number;
  copies: number;
  sent_at: string | null;
  printer_notified_at: string | null;
  done_at: string | null;
};

export type Batches = { ready: OrderBrief[]; waiting: OrderBrief[]; batches: BatchRow[]; printer_email_set: boolean };

export type ItemRow = {
  n: number | null;
  book_id: string | null;
  title: string;
  child_name: string | null;
  format: string;
  copies: number;
  book_status: string | null;
  files: boolean;
};

export type BatchDetail = BatchRow & {
  orders_list: OrderBrief[];
  items: { id: string; code: string; status: string; city: string | null; items: ItemRow[] }[];
  email: "pending" | "sent" | "logged" | "skipped" | "failed" | null;
  link_expires_at: string | null;
  actions: ("send" | "printing" | "done" | "resend" | "ship")[];
};

export const BATCH_TONE: Record<BatchRow["status"], string> = {
  open: "bg-amber-100 text-amber-700",
  sent: "bg-night-100 text-night-900",
  printing: "bg-info-bg text-info",
  done: "bg-success-bg text-success",
};
