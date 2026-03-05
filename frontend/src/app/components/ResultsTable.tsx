"use client";

import ArticleCard, { Article } from "./ArticleCard";

interface ResultsTableProps {
  query: string;
  articles: Article[];
  total: number;
  skipped: number;
}

export default function ResultsTable({
  query,
  articles,
  total,
  skipped,
}: ResultsTableProps) {
  if (articles.length === 0) {
    return (
      <div className="results">
        <div className="results-summary">Статьи не найдены</div>
      </div>
    );
  }

  return (
    <div className="results">
      <div className="results-summary">
        <div>
          Запрос: <strong>{query}</strong>
        </div>
        <div>
          Проанализировано статей: <strong>{total}</strong>
          {skipped > 0 && (
            <span> | Пропущено (без полного доступа): {skipped}</span>
          )}
        </div>
      </div>
      <div className="article-list">
        {articles.map((article, index) => (
          <ArticleCard key={article.id ?? index} article={article} />
        ))}
      </div>
    </div>
  );
}
