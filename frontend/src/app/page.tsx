"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import SearchForm from "./components/SearchForm";
import ResultsTable from "./components/ResultsTable";
import type { Article } from "./components/ArticleCard";
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ScrapeProgress {
  currentPage: number;
  totalPages: number;
  articlesFound: number;
  skipped: number;
}

interface SessionDetail {
  id: number;
  query: string;
  created_at: string;
  articles: Article[];
}

function useDebounce(value: string, delay: number): string {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}

export default function Home() {
  const [query, setQuery] = useState("");
  const [pageFrom, setPageFrom] = useState(1);
  const [pageTo, setPageTo] = useState(1);
  const [onlyFullAccess, setOnlyFullAccess] = useState(true);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const debouncedQuery = useDebounce(query, 500);
  const debouncedDateFrom = useDebounce(dateFrom, 500);
  const debouncedDateTo = useDebounce(dateTo, 500);

  const pageCountQuery = useQuery({
    queryKey: ["pageCount", debouncedQuery, onlyFullAccess, debouncedDateFrom, debouncedDateTo],
    queryFn: async () => {
      const params = new URLSearchParams({
        query: debouncedQuery,
        only_full_access: String(onlyFullAccess),
        date_from: debouncedDateFrom,
        date_to: debouncedDateTo,
      });
      const res = await fetch(`${API_URL}/api/springer/page-count?${params}`);
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail || `Ошибка сервера (${res.status})`);
      }
      return res.json() as Promise<{ total_pages: number }>;
    },
    enabled: debouncedQuery.length > 2,
    staleTime: 5 * 60 * 1000,
  });

  const totalPages = pageCountQuery.data?.total_pages;

  useEffect(() => {
    if (totalPages !== undefined && totalPages > 0) {
      setPageFrom(1);
      setPageTo(totalPages);
    }
  }, [totalPages]);

  const [isScraping, setIsScraping] = useState(false);
  const [scrapeProgress, setScrapeProgress] = useState<ScrapeProgress | null>(
    null,
  );
  const [scrapeSessionId, setScrapeSessionId] = useState<number | null>(null);
  const [scrapeResult, setScrapeResult] = useState<{
    articles: Article[];
    total: number;
    skipped: number;
  } | null>(null);
  const [scrapeError, setScrapeError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    return () => {
      eventSourceRef.current?.close();
    };
  }, []);

  const startScraping = useCallback(() => {
    setScrapeError(null);
    setScrapeResult(null);
    setScrapeProgress(null);
    setScrapeSessionId(null);
    setIsScraping(true);

    const params = new URLSearchParams({
      query,
      page_from: String(pageFrom),
      page_to: String(pageTo),
      only_full_access: String(onlyFullAccess),
      date_from: dateFrom,
      date_to: dateTo,
    });

    const es = new EventSource(`${API_URL}/api/springer/scrape?${params}`);
    eventSourceRef.current = es;

    es.onmessage = (event) => {
      const data = JSON.parse(event.data);
      switch (data.type) {
        case "started":
          setScrapeSessionId(data.session_id);
          break;
        case "progress":
          setScrapeProgress({
            currentPage: data.current_page,
            totalPages: data.total_pages,
            articlesFound: data.articles_found,
            skipped: data.skipped,
          });
          break;
        case "complete":
        case "stopped":
          es.close();
          eventSourceRef.current = null;
          setIsScraping(false);
          setScrapeProgress(null);
          fetchSessionResult(data.session_id);
          break;
        case "error":
          es.close();
          eventSourceRef.current = null;
          setIsScraping(false);
          setScrapeProgress(null);
          setScrapeError(data.message);
          break;
      }
    };

    es.onerror = () => {
      es.close();
      eventSourceRef.current = null;
      setIsScraping(false);
      setScrapeProgress(null);
      setScrapeError("Соединение с сервером потеряно");
    };
  }, [query, pageFrom, pageTo, onlyFullAccess, dateFrom, dateTo]);

  const stopScraping = useCallback(async () => {
    if (scrapeSessionId) {
      await fetch(`${API_URL}/api/springer/scrape/${scrapeSessionId}/stop`, {
        method: "POST",
      });
    }
  }, [scrapeSessionId]);

  const fetchSessionResult = async (sessionId: number) => {
    try {
      const res = await fetch(`${API_URL}/api/sessions/${sessionId}`);
      if (!res.ok) throw new Error("Failed to fetch results");
      const data: SessionDetail = await res.json();
      setScrapeResult({
        articles: data.articles,
        total: data.articles.length,
        skipped: 0,
      });
    } catch {
      setScrapeError("Не удалось загрузить результаты");
    }
  };

  return (
    <main>
      <h1>Springer Scrapper</h1>
      <SearchForm
        query={query}
        onQueryChange={setQuery}
        pageFrom={pageFrom}
        onPageFromChange={setPageFrom}
        pageTo={pageTo}
        onPageToChange={setPageTo}
        onlyFullAccess={onlyFullAccess}
        onOnlyFullAccessChange={setOnlyFullAccess}
        dateFrom={dateFrom}
        onDateFromChange={setDateFrom}
        dateTo={dateTo}
        onDateToChange={setDateTo}
        totalPages={totalPages}
        isLoadingPages={pageCountQuery.isLoading}
        isFetchingPages={pageCountQuery.isFetching}
        pageCountError={pageCountQuery.error?.message ?? null}
        onScrape={startScraping}
        onStopScrape={stopScraping}
        isScraping={isScraping}
        scrapeProgress={scrapeProgress}
      />
      {scrapeResult && (
        <ResultsTable
          query={query}
          articles={scrapeResult.articles}
          total={scrapeResult.total}
          skipped={scrapeResult.skipped}
        />
      )}
      {scrapeError && <div className='error'>Ошибка: {scrapeError}</div>}
    </main>
  );
}
