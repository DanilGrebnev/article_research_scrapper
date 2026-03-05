"use client";

interface ScrapeProgress {
  currentPage: number;
  totalPages: number;
  articlesFound: number;
  skipped: number;
}

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
  pageCountError: string | null;
  onScrape: () => void;
  onStopScrape: () => void;
  isScraping: boolean;
  scrapeProgress: ScrapeProgress | null;
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
  pageCountError,
  onScrape,
  onStopScrape,
  isScraping,
  scrapeProgress,
}: SearchFormProps) {
  const progressPercent =
    scrapeProgress && scrapeProgress.totalPages > 0
      ? Math.round(
          (scrapeProgress.currentPage / scrapeProgress.totalPages) * 100,
        )
      : 0;

  return (
    <div className='search-form'>
      <div className='form-group'>
        <label htmlFor='query'>Ключевые слова</label>
        <input
          id='query'
          type='text'
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          placeholder='Введите поисковый запрос...'
        />
        {isLoadingPages && <span className='hint'>Загрузка...</span>}
        {!isLoadingPages && pageCountError && (
          <span className='hint hint--error'>Ошибка: {pageCountError}</span>
        )}
        {!isLoadingPages && !pageCountError && totalPages !== undefined && (
          <span className='hint'>Найдено страниц: {totalPages}</span>
        )}
      </div>

      <div className='form-row'>
        <div className='form-group'>
          <label htmlFor='pageFrom'>Страница с</label>
          <input
            id='pageFrom'
            type='number'
            min={1}
            max={totalPages || 999}
            value={pageFrom}
            onChange={(e) => onPageFromChange(Number(e.target.value))}
            disabled={isFetchingPages || query.length < 3}
          />
        </div>
        <div className='form-group'>
          <label htmlFor='pageTo'>Страница по</label>
          <input
            id='pageTo'
            type='number'
            min={pageFrom}
            max={totalPages || 999}
            value={pageTo}
            onChange={(e) => onPageToChange(Number(e.target.value))}
            disabled={isFetchingPages || query.length < 3}
          />
        </div>
      </div>

      <div className='form-row'>
        <div className='form-group'>
          <label htmlFor='dateFrom'>Год с</label>
          <input
            id='dateFrom'
            type='text'
            inputMode='numeric'
            pattern='\d{4}'
            placeholder='YYYY'
            value={dateFrom}
            maxLength={4}
            onChange={(e) => {
              const v = e.target.value.replace(/\D/g, "").slice(0, 4);
              onDateFromChange(v);
            }}
            disabled={isFetchingPages || query.length < 3}
          />
        </div>
        <div className='form-group'>
          <label htmlFor='dateTo'>Год по</label>
          <input
            id='dateTo'
            type='text'
            inputMode='numeric'
            pattern='\d{4}'
            placeholder='YYYY'
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

      <div className='form-group checkbox-group'>
        <label>
          <input
            type='checkbox'
            checked={onlyFullAccess}
            onChange={(e) => onOnlyFullAccessChange(e.target.checked)}
            disabled={isFetchingPages || query.length < 3}
          />
          Только Full access
        </label>
      </div>

      <div className='form-row'>
        {isScraping ? (
          <button onClick={onStopScrape} className='btn-danger'>
            Остановить скрапинг
          </button>
        ) : (
          <button
            onClick={onScrape}
            disabled={isFetchingPages || query.length < 3}
            className='btn-primary'
          >
            Запустить скраппинг
          </button>
        )}
      </div>

      {isScraping && scrapeProgress && (
        <div className='scrape-progress'>
          <div className='scrape-progress__text'>
            Скраплено {scrapeProgress.currentPage} из{" "}
            {scrapeProgress.totalPages} страниц
            {" | "}Найдено {scrapeProgress.articlesFound} статей
          </div>
          <div className='scrape-progress__bar'>
            <div
              className='scrape-progress__fill'
              style={{ width: `${progressPercent}%` }}
            />
          </div>
          <div className='scrape-progress__percent'>{progressPercent}%</div>
        </div>
      )}

      {isScraping && !scrapeProgress && (
        <div className='scrape-progress'>
          <div className='scrape-progress__text'>Подключение к серверу...</div>
        </div>
      )}
    </div>
  );
}
