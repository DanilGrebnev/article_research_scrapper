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
  dateFrom: string;
  onDateFromChange: (value: string) => void;
  dateTo: string;
  onDateToChange: (value: string) => void;
  totalPages?: number;
  isLoadingPages: boolean;
  isFetchingPages: boolean;
  onApplyFilters: () => void;
  filtersChanged: boolean;
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
  dateFrom,
  onDateFromChange,
  dateTo,
  onDateToChange,
  totalPages,
  isLoadingPages,
  isFetchingPages,
  onApplyFilters,
  filtersChanged,
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
            disabled={isFetchingPages || query.length < 3}
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
            disabled={isFetchingPages || query.length < 3}
          />
        </div>
      </div>

      <div className="form-row">
        <div className="form-group">
          <label htmlFor="dateFrom">Год с</label>
          <input
            id="dateFrom"
            type="text"
            inputMode="numeric"
            pattern="\d{4}"
            placeholder="YYYY"
            value={dateFrom}
            maxLength={4}
            onChange={(e) => {
              const v = e.target.value.replace(/\D/g, "").slice(0, 4);
              onDateFromChange(v);
            }}
            disabled={isFetchingPages || query.length < 3}
          />
        </div>
        <div className="form-group">
          <label htmlFor="dateTo">Год по</label>
          <input
            id="dateTo"
            type="text"
            inputMode="numeric"
            pattern="\d{4}"
            placeholder="YYYY"
            value={dateTo}
            maxLength={4}
            onChange={(e) => {
              const v = e.target.value.replace(/\D/g, "").slice(0, 4);
              onDateToChange(v);
            }}
            disabled={isFetchingPages || query.length < 3}
          />
        </div>
      </div>

      <div className="form-group checkbox-group">
        <label>
          <input
            type="checkbox"
            checked={onlyFullAccess}
            onChange={(e) => onOnlyFullAccessChange(e.target.checked)}
            disabled={isFetchingPages || query.length < 3}
          />
          Только Full access
        </label>
      </div>

      <div className="form-row">
        <button
          onClick={onApplyFilters}
          disabled={!filtersChanged || isFetchingPages || query.length < 3}
          className="btn-secondary"
        >
          Применить фильтры
        </button>
        <button
          onClick={onScrape}
          disabled={isScraping || isFetchingPages || filtersChanged || query.length < 3}
          className="btn-primary"
        >
          {isScraping ? "Скраппинг..." : "Запустить скраппинг"}
        </button>
      </div>
    </div>
  );
}
