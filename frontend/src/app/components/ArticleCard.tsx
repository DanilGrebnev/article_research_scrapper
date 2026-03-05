"use client";

import { useState } from "react";
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Article {
  id: number;
  title: string;
  url: string;
  published_date: string;
  description: string;
  authors: string;
  abstract: string | null;
}

export default function ArticleCard({ article }: { article: Article }) {
  const [abstract, setAbstract] = useState<string | null>(article.abstract);
  const [isLoading, setIsLoading] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAbstract = async () => {
    if (abstract) {
      setIsExpanded(!isExpanded);
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/api/springer/article/${article.id}/abstract`, {
        method: "POST",
      });
      if (!res.ok) throw new Error("Failed to fetch abstract");
      const data = await res.json();
      setAbstract(data.abstract);
      setIsExpanded(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="article-card">
      <div className="article-card__header">
        <h3 className="article-card__title">
          {article.url ? (
            <a href={article.url} target="_blank" rel="noopener noreferrer">
              {article.title}
            </a>
          ) : (
            article.title
          )}
        </h3>
        {article.published_date && (
          <span className="article-card__date">{article.published_date}</span>
        )}
      </div>

      {article.authors && article.authors !== "—" && (
        <p className="article-card__authors">{article.authors}</p>
      )}

      {article.description && article.description !== "—" && (
        <p className="article-card__description">{article.description}</p>
      )}

      <div className="article-card__actions">
        <button
          className="btn-deep-analysis"
          onClick={fetchAbstract}
          disabled={isLoading}
        >
          {isLoading
            ? "Загрузка..."
            : abstract
            ? isExpanded
              ? "Скрыть Abstract"
              : "Показать Abstract"
            : "Глубокий анализ"}
        </button>
      </div>

      {error && <div className="article-card__error">{error}</div>}

      {abstract && isExpanded && (
        <div className="article-card__abstract">
          <h4>Abstract</h4>
          <p>{abstract}</p>
        </div>
      )}

      {article.url && (
        <div className="article-card__source">
          <a href={article.url} target="_blank" rel="noopener noreferrer">
            Оригинал на SpringerLink ↗
          </a>
        </div>
      )}
    </div>
  );
}
