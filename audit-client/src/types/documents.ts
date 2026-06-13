export type DocumentStatus = "pending" | "available";

export interface DocumentRecord {
  id: string;
  engagement_id: string;
  working_paper_id: string | null;
  filename: string;
  content_type: string;
  size_bytes: number | null;
  status: DocumentStatus;
  uploaded_by: string;
  created_at: string;
  updated_at: string;
}

export interface PresignUploadResponse {
  document_id: string;
  upload_url: string;
}

export interface DownloadResponse {
  download_url: string;
}
