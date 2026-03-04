"use client";

interface SearchFormProps {
  query: string;
  onQueryChange: (value: string) => void;
  pageFrom: number;
  onPageFromChange: (value: number) => void;
  pageTo: number;
  onPageToChange: (value: number) => void;
  onlyFullAccess: boolean;
  onOnlyFullAccessChange: (value: boolean) => void;
  totalPages?: number;
  isLoadingPages: boolean;
  onScrape: () => void;
  isScraping: boolean;
}

export default function SearchForm({
  query,
  onQueryChange,
  pageFrom,
  onPageFromChange,
  pageTo,
  onPageToChange,
  onlyFullAccess,
  onOnlyFullAccessChange,
  totalPages,
  isLoadingPages,
  onScrape,
  isScraping,
}: SearchFormProps) {
  return (
    <div className="search-form">
      <div className="form-group">
        <label htmlFor="query">Ключевые слова</label>
        <input
          id="query"
          type="text"
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          placeholder="Введите поисковый запрос..."
        />
        {isLoadingPages && <span className="hint">Загрузка...</span>}
        {!isLoadingPages && totalPages !== undefined && (
          <span className="hint">Найдено страниц: {totalPages}</span>
        )}
      </div>

      <div className="form-row">
        <div className="form-group">
          <label htmlFor="pageFrom">Страница с</label>
          <input
            id="pageFrom"
            type="number"
            min={1}
            max={totalPages || 999}
            value={pageFrom}
            onChange={(e) => onPageFromChange(Number(e.target.value))}
          />
        </div>
        <div className="form-group">
          <label htmlFor="pageTo">Страница по</label>
          <input
            id="pageTo"
            type="number"
            min={pageFrom}
            max={totalPages || 999}
            value={pageTo}
            onChange={(e) => onPageToChange(Number(e.target.value))}
          />
        </div>
      </div>

      <div className="form-group checkbox-group">
        <label>
          <input
            type="checkbox"
            checked={onlyFullAccess}
            onChange={(e) => onOnlyFullAccessChange(e.target.checked)}
          />
          Только Full access
        </label>
      </div>

      <button
        onClick={onScrape}
        disabled={isScraping || query.length < 3}
        className="btn-primary"
      >
        {isScraping ? "Скраппинг..." : "Запустить скраппинг"}
      </button>
    </div>
  );
}
