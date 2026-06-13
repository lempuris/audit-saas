import { useCallback, useEffect, useState } from "react";

import { useMe } from "../contexts/MeContext";
import { useApi } from "../hooks/useApi";
import type { TeamMemberRecord } from "../types/engagements";
import type { ReviewNoteRecord } from "../types/reviewNotes";

interface Props {
  engagementId: string;
  workingPaperId: string;
  team: TeamMemberRecord[];
}

function memberLabel(team: TeamMemberRecord[], clerkUserId: string | null): string {
  if (!clerkUserId) return "Unassigned";
  const member = team.find((m) => m.clerk_user_id === clerkUserId);
  return member ? (member.display_name ?? member.email ?? clerkUserId) : clerkUserId;
}

export default function ReviewNotesPanel({ engagementId, workingPaperId, team }: Props) {
  const api = useApi();
  const { me } = useMe();
  const role = me?.role ?? null;
  const isReviewer = role === "admin" || role === "partner" || role === "manager";

  const base = `/api/engagements/${engagementId}/review-notes`;

  const [notes, setNotes] = useState<ReviewNoteRecord[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [newText, setNewText] = useState("");
  const [newAssignee, setNewAssignee] = useState("");
  const [responseText, setResponseText] = useState<Record<string, string>>({});

  const load = useCallback(() => {
    api
      .get<ReviewNoteRecord[]>(`${base}?working_paper_id=${workingPaperId}`)
      .then(setNotes)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)));
  }, [api, base, workingPaperId]);

  useEffect(load, [load]);

  async function run(action: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await action();
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  function raise() {
    if (!newText) return;
    void run(() =>
      api.post(base, {
        text: newText,
        assigned_to: newAssignee || null,
        working_paper_id: workingPaperId,
      }),
    ).then(() => {
      setNewText("");
      setNewAssignee("");
    });
  }

  function respond(noteId: string) {
    const text = responseText[noteId];
    if (!text) return;
    void run(() => api.patch(`${base}/${noteId}/respond`, { response: text })).then(() =>
      setResponseText((prev) => ({ ...prev, [noteId]: "" })),
    );
  }

  function clear(noteId: string) {
    void run(() => api.patch(`${base}/${noteId}/clear`, {}));
  }

  return (
    <div className="mt-3 rounded border border-slate-100 bg-slate-50 p-3">
      <p className="text-xs font-semibold text-slate-600">Review notes</p>
      {error && <p className="mt-1 break-all text-xs text-red-700">{error}</p>}

      {notes.length === 0 && <p className="mt-1 text-xs text-slate-400">No review notes.</p>}

      <ul className="mt-1.5 space-y-2">
        {notes.map((note) => {
          const canClear = isReviewer || note.raised_by === me?.user_id;
          return (
            <li key={note.id} className="rounded border border-slate-200 bg-white p-2 text-xs">
              <div className="flex items-center justify-between gap-2">
                <span className="font-medium text-slate-800">{note.text}</span>
                <span
                  className={
                    note.status === "cleared"
                      ? "rounded bg-green-100 px-1.5 py-0.5 text-green-800"
                      : note.status === "responded"
                        ? "rounded bg-amber-100 px-1.5 py-0.5 text-amber-800"
                        : "rounded bg-red-100 px-1.5 py-0.5 text-red-800"
                  }
                >
                  {note.status}
                </span>
              </div>
              <p className="mt-0.5 text-slate-400">
                Assigned to {memberLabel(team, note.assigned_to)}
              </p>
              {note.response && (
                <p className="mt-1 text-slate-600">
                  <span className="font-medium">Response:</span> {note.response}
                </p>
              )}
              {note.status !== "cleared" && (
                <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                  <input
                    aria-label={`Respond to note ${note.id}`}
                    value={responseText[note.id] ?? ""}
                    onChange={(e) =>
                      setResponseText((prev) => ({ ...prev, [note.id]: e.target.value }))
                    }
                    placeholder="Response…"
                    className="flex-1 rounded border border-slate-300 px-2 py-1"
                  />
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => respond(note.id)}
                    className="rounded border border-slate-300 px-2 py-1 text-slate-700 hover:bg-slate-50"
                  >
                    Respond
                  </button>
                  {canClear && (
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => clear(note.id)}
                      className="rounded border border-green-300 px-2 py-1 text-green-700 hover:bg-green-50"
                    >
                      Clear
                    </button>
                  )}
                </div>
              )}
            </li>
          );
        })}
      </ul>

      {isReviewer && (
        <div className="mt-2 flex flex-wrap items-center gap-1.5">
          <input
            aria-label="New review note"
            value={newText}
            onChange={(e) => setNewText(e.target.value)}
            placeholder="Raise a note…"
            className="flex-1 rounded border border-slate-300 px-2 py-1 text-xs"
          />
          <select
            aria-label="Assign review note to"
            value={newAssignee}
            onChange={(e) => setNewAssignee(e.target.value)}
            className="rounded border border-slate-300 bg-white px-2 py-1 text-xs"
          >
            <option value="">Unassigned</option>
            {team.map((member) => (
              <option key={member.clerk_user_id} value={member.clerk_user_id}>
                {memberLabel(team, member.clerk_user_id)}
              </option>
            ))}
          </select>
          <button
            type="button"
            disabled={busy || !newText}
            onClick={raise}
            className="rounded bg-slate-800 px-2 py-1 text-xs font-medium text-white disabled:opacity-50"
          >
            Raise
          </button>
        </div>
      )}
    </div>
  );
}
