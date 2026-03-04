"use client";

interface Article {
  title: string;
  description: string;
  authors: string;
}

interface ResultsTableProps {
  articles: Article[];
  total: number;
  skipped: number;
}

export default function ResultsTable({ articles, total, skipped }: ResultsTableProps) {
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
        Найдено статей: <strong>{total}</strong>
        {skipped > 0 && <span> | Пропущено (без полного доступа): {skipped}</span>}
      </div>
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>Название</th>
            <th>Описание</th>
            <th>Авторы</th>
          </tr>
        </thead>
        <tbody>
          {articles.map((article, index) => (
            <tr key={index}>
              <td>{index + 1}</td>
              <td>{article.title}</td>
              <td className="description-cell">{article.description}</td>
              <td>{article.authors}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
