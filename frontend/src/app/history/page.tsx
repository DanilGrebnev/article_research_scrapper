"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Session {
  id: number;
  query: string;
  created_at: string;
  article_count: number;
  pages_scanned: number;
}

export default function HistoryPage() {
  const queryClient = useQueryClient();

  const sessionsQuery = useQuery({
    queryKey: ["sessions"],
    queryFn: async () => {
      const res = await fetch(`${API_URL}/api/sessions`);
      if (!res.ok) throw new Error("Failed to fetch sessions");
      return res.json() as Promise<Session[]>;
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (sessionId: number) => {
      const res = await fetch(`${API_URL}/api/sessions/${sessionId}`, {
        method: "DELETE",
      });
      if (!res.ok) throw new Error("Failed to delete session");
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sessions"] });
    },
  });

  const handleDelete = (session: Session) => {
    if (confirm(`Удалить запрос "${session.query}" и все его статьи?`)) {
      deleteMutation.mutate(session.id);
    }
  };

  const formatDate = (iso: string) => {
    try {
      const d = new Date(iso);
      return d.toLocaleString("ru-RU", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return iso;
    }
  };

  return (
    <main>
      <h1>История запросов</h1>

      {sessionsQuery.isLoading && <p>Загрузка...</p>}
      {sessionsQuery.error && (
        <div className="error">
          Ошибка: {sessionsQuery.error.message}
        </div>
      )}

      {sessionsQuery.data && sessionsQuery.data.length === 0 && (
        <p className="history-empty">Нет сохранённых запросов</p>
      )}

      {sessionsQuery.data && sessionsQuery.data.length > 0 && (
        <div className="session-list">
          {sessionsQuery.data.map((session) => (
            <div key={session.id} className="session-card">
              <div className="session-card__main">
                <Link
                  href={`/history/${session.id}`}
                  className="session-card__query"
                >
                  {session.query}
                </Link>
                <div className="session-card__meta">
                  <span>{formatDate(session.created_at)}</span>
                  <span>Страниц: {session.pages_scanned}</span>
                  <span>Статей: {session.article_count}</span>
                </div>
              </div>
              <button
                className="btn-delete"
                onClick={() => handleDelete(session)}
                disabled={deleteMutation.isPending}
              >
                Удалить
              </button>
            </div>
          ))}
        </div>
      )}
    </main>
  );
}
