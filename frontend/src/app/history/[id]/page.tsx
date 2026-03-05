"use client";

import { useState, useEffect, useMemo } from "react";
import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import Link from "next/link";
import ArticleCard, { Article } from "../../components/ArticleCard";
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface SessionDetail {
  id: number;
  query: string;
  created_at: string;
  articles: Article[];
}

const ARTICLES_PER_PAGE = 20;

export default function SessionDetailPage() {
  const params = useParams();
  const sessionId = params.id as string;

  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [currentPage, setCurrentPage] = useState(1);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(search), 400);
    return () => clearTimeout(timer);
  }, [search]);

  useEffect(() => {
    setCurrentPage(1);
  }, [debouncedSearch]);

  const sessionQuery = useQuery({
    queryKey: ["session", sessionId, debouncedSearch],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (debouncedSearch) params.set("search", debouncedSearch);
      const res = await fetch(`${API_URL}/api/sessions/${sessionId}?${params}`);
      if (!res.ok) throw new Error("Failed to fetch session");
      return res.json() as Promise<SessionDetail>;
    },
    placeholderData: keepPreviousData,
  });

  const articles = sessionQuery.data?.articles ?? [];
  const totalPages = Math.max(1, Math.ceil(articles.length / ARTICLES_PER_PAGE));

  const paginatedArticles = useMemo(() => {
    const start = (currentPage - 1) * ARTICLES_PER_PAGE;
    return articles.slice(start, start + ARTICLES_PER_PAGE);
  }, [articles, currentPage]);

  const pageNumbers = useMemo(() => {
    const pages: number[] = [];
    const maxVisible = 7;
    if (totalPages <= maxVisible) {
      for (let i = 1; i <= totalPages; i++) pages.push(i);
    } else {
      pages.push(1);
      let start = Math.max(2, currentPage - 1);
      let end = Math.min(totalPages - 1, currentPage + 1);
      if (currentPage <= 3) {
        start = 2;
        end = 5;
      } else if (currentPage >= totalPages - 2) {
        start = totalPages - 4;
        end = totalPages - 1;
      }
      if (start > 2) pages.push(-1);
      for (let i = start; i <= end; i++) pages.push(i);
      if (end < totalPages - 1) pages.push(-2);
      pages.push(totalPages);
    }
    return pages;
  }, [totalPages, currentPage]);

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

  const isSearching = sessionQuery.isFetching && !sessionQuery.isLoading;

  return (
    <main>
      <div className="session-detail__back">
        <Link href="/history">← Назад к истории</Link>
      </div>

      {sessionQuery.isLoading && !sessionQuery.data && <p>Загрузка...</p>}
      {sessionQuery.error && !sessionQuery.data && (
        <div className="error">
          Ошибка: {sessionQuery.error.message}
        </div>
      )}

      {sessionQuery.data && (
        <div className="session-detail__header">
          <h1>{sessionQuery.data.query}</h1>
          <div className="session-detail__meta">
            <span>{formatDate(sessionQuery.data.created_at)}</span>
            <span>Всего статей: {articles.length}</span>
          </div>
        </div>
      )}

      <div className="session-detail__search">
        <input
          type="text"
          placeholder="Поиск по заголовку..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="session-detail__search-input"
        />
      </div>

      {sessionQuery.data && (
        <>
          <div className={`results ${isSearching ? "results--loading" : ""}`}>
            {paginatedArticles.length === 0 ? (
              <p className="history-empty">Статьи не найдены</p>
            ) : (
              <div className="article-list">
                {paginatedArticles.map((article) => (
                  <ArticleCard key={article.id} article={article} />
                ))}
              </div>
            )}
          </div>

          {totalPages > 1 && (
            <div className="pagination">
              <button
                className="pagination__btn"
                disabled={currentPage === 1}
                onClick={() => setCurrentPage((p) => p - 1)}
              >
                ← Назад
              </button>
              {pageNumbers.map((num, i) =>
                num < 0 ? (
                  <span key={`ellipsis-${i}`} className="pagination__ellipsis">
                    …
                  </span>
                ) : (
                  <button
                    key={num}
                    className={`pagination__btn ${
                      num === currentPage ? "pagination__btn--active" : ""
                    }`}
                    onClick={() => setCurrentPage(num)}
                  >
                    {num}
                  </button>
                )
              )}
              <button
                className="pagination__btn"
                disabled={currentPage === totalPages}
                onClick={() => setCurrentPage((p) => p + 1)}
              >
                Вперёд →
              </button>
            </div>
          )}
        </>
      )}
    </main>
  );
}
