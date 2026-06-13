import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";

import { useMe } from "../contexts/MeContext";
import { useApi } from "../hooks/useApi";
import type {
  DocumentRecord,
  DownloadResponse,
  PresignUploadResponse,
} from "../types/documents";
import type { WorkingPaperRecord } from "../types/workingPapers";

function formatSize(bytes: number | null): string {
  if (bytes === null) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function DocumentsScreen() {
  const { engagementId } = useParams<{ engagementId: string }>();
  const api = useApi();
  const { me } = useMe();
  const role = me?.role ?? null;
  const canWrite = role !== null;
  const isManager = role === "admin" || role === "partner" || role === "manager";

  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [papers, setPapers] = useState<WorkingPaperRecord[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [linkWp, setLinkWp] = useState("");

  const base = `/api/engagements/${engagementId}/documents`;

  const load = useCallback(() => {
    if (!engagementId) return;
    api
      .get<DocumentRecord[]>(base)
      .then((rows) => {
        setDocuments(rows);
        setError(null);
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)))
      .finally(() => setLoaded(true));
    api
      .get<WorkingPaperRecord[]>(`/api/engagements/${engagementId}/working-papers`)
      .then(setPapers)
      .catch(() => setPapers([]));
  }, [api, base, engagementId]);

  useEffect(load, [load]);

  function paperLabel(workingPaperId: string | null): string {
    if (!workingPaperId) return "—";
    const wp = papers.find((p) => p.id === workingPaperId);
    return wp ? `${wp.index_ref} ${wp.title}` : "working paper";
  }

  async function upload(event: FormEvent) {
    event.preventDefault();
    if (!file) return;
    setBusy(true);
    setNotice(null);
    setError(null);
    try {
      const contentType = file.type || "application/octet-stream";
      // 1. Ask the API for a presigned PUT URL (creates a pending row).
      const presign = await api.post<PresignUploadResponse>(`${base}/presign-upload`, {
        filename: file.name,
        content_type: contentType,
        working_paper_id: linkWp || null,
      });
      // 2. Upload the bytes straight to S3 (not through the API).
      const put = await fetch(presign.upload_url, {
        method: "PUT",
        body: file,
        headers: { "Content-Type": contentType },
      });
      if (!put.ok) throw new Error(`Upload failed (${put.status})`);
      // 3. Confirm so the API records size + version and marks it available.
      await api.post(`${base}/${presign.document_id}/confirm`);
      setNotice("Document uploaded");
      setFile(null);
      setLinkWp("");
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function download(doc: DocumentRecord) {
    try {
      const { download_url } = await api.get<DownloadResponse>(`${base}/${doc.id}/download`);
      window.open(download_url, "_blank", "noopener");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function remove(doc: DocumentRecord) {
    setBusy(true);
    setNotice(null);
    setError(null);
    try {
      await api.delete(`${base}/${doc.id}`);
      setNotice("Document removed");
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  if (!loaded && !error) {
    return <p className="text-slate-500">Loading…</p>;
  }

  return (
    <div>
      <div>
        <h2 className="text-xl font-semibold text-slate-800">Documents</h2>
        <p className="mt-0.5 text-sm text-slate-500">
          <Link to={`/engagements/${engagementId}`} className="underline">
            Back to engagement
          </Link>
        </p>
      </div>

      {notice && <p className="mt-3 text-sm text-green-700">{notice}</p>}
      {error && <p className="mt-3 break-all text-sm text-red-700">{error}</p>}

      {canWrite && (
        <form
          onSubmit={upload}
          className="mt-4 flex flex-wrap items-end gap-3 rounded border border-slate-200 bg-white p-4"
        >
          <label className="flex flex-col text-sm text-slate-600">
            File
            <input
              type="file"
              aria-label="Evidence file"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              className="mt-1 text-sm"
            />
          </label>
          <label className="flex flex-col text-sm text-slate-600">
            Attach to working paper
            <select
              value={linkWp}
              onChange={(e) => setLinkWp(e.target.value)}
              className="mt-1 w-64 rounded border border-slate-300 bg-white px-2 py-1.5"
            >
              <option value="">None</option>
              {papers.map((wp) => (
                <option key={wp.id} value={wp.id}>
                  {wp.index_ref} {wp.title}
                </option>
              ))}
            </select>
          </label>
          <button
            type="submit"
            disabled={busy || !file}
            className="rounded bg-slate-800 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            Upload
          </button>
        </form>
      )}

      {documents.length === 0 ? (
        <p className="mt-6 text-slate-500">No documents uploaded yet.</p>
      ) : (
        <div className="mt-4 overflow-x-auto rounded border border-slate-200 bg-white">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-left text-slate-500">
                <th className="px-4 py-2 font-medium">File</th>
                <th className="px-4 py-2 font-medium">Size</th>
                <th className="px-4 py-2 font-medium">Working paper</th>
                <th className="px-4 py-2 font-medium">Status</th>
                <th className="px-4 py-2 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => {
                const canDelete = isManager || doc.uploaded_by === me?.user_id;
                return (
                  <tr key={doc.id} className="border-b border-slate-100">
                    <td className="px-4 py-2 text-slate-800">{doc.filename}</td>
                    <td className="px-4 py-2 text-slate-600">{formatSize(doc.size_bytes)}</td>
                    <td className="px-4 py-2 text-slate-600">
                      {paperLabel(doc.working_paper_id)}
                    </td>
                    <td className="px-4 py-2 text-slate-600 capitalize">{doc.status}</td>
                    <td className="px-4 py-2">
                      <div className="flex gap-2">
                        <button
                          type="button"
                          disabled={doc.status !== "available"}
                          onClick={() => void download(doc)}
                          className="rounded border border-slate-300 px-2 py-1 text-xs text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                        >
                          Download
                        </button>
                        {canDelete && (
                          <button
                            type="button"
                            disabled={busy}
                            onClick={() => void remove(doc)}
                            className="rounded border border-red-300 px-2 py-1 text-xs text-red-700 hover:bg-red-50 disabled:opacity-50"
                          >
                            Remove
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
