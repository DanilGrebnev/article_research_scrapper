"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import SearchForm from "./components/SearchForm";
import ResultsTable from "./components/ResultsTable";

interface Article {
  id: number;
  title: string;
  url: string;
  published_date: string;
  description: string;
  authors: string;
  abstract: string | null;
}

interface ScrapeResult {
  session_id: number;
  articles: Article[];
  total: number;
  skipped: number;
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

  const [appliedFilters, setAppliedFilters] = useState({
    onlyFullAccess: true,
    dateFrom: "",
    dateTo: "",
  });

  const applyFilters = () => {
    setAppliedFilters({ onlyFullAccess, dateFrom, dateTo });
  };

  const filtersChanged =
    onlyFullAccess !== appliedFilters.onlyFullAccess ||
    dateFrom !== appliedFilters.dateFrom ||
    dateTo !== appliedFilters.dateTo;

  const debouncedQuery = useDebounce(query, 500);

  const pageCountQuery = useQuery({
    queryKey: ["pageCount", debouncedQuery, appliedFilters],
    queryFn: async () => {
      const params = new URLSearchParams({
        query: debouncedQuery,
        only_full_access: String(appliedFilters.onlyFullAccess),
        date_from: appliedFilters.dateFrom,
        date_to: appliedFilters.dateTo,
      });
      const res = await fetch(`/api/springer/page-count?${params}`);
      if (!res.ok) throw new Error("Failed to fetch page count");
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

  const scrapeMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch("/api/springer/scrape", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query,
          page_from: pageFrom,
          page_to: pageTo,
          only_full_access: appliedFilters.onlyFullAccess,
          date_from: appliedFilters.dateFrom,
          date_to: appliedFilters.dateTo,
        }),
      });
      if (!res.ok) throw new Error("Scraping failed");
      return res.json() as Promise<ScrapeResult>;
    },
  });

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
        onApplyFilters={applyFilters}
        filtersChanged={filtersChanged}
        onScrape={() => scrapeMutation.mutate()}
        isScraping={scrapeMutation.isPending}
      />
      {scrapeMutation.data && (
        <ResultsTable
          query={query}
          articles={scrapeMutation.data.articles}
          total={scrapeMutation.data.total}
          skipped={scrapeMutation.data.skipped}
        />
      )}
      {scrapeMutation.error && (
        <div className="error">
          Ошибка: {scrapeMutation.error.message}
        </div>
      )}
    </main>
  );
}
