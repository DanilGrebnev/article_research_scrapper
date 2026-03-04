"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import SearchForm from "./components/SearchForm";
import ResultsTable from "./components/ResultsTable";

interface Article {
  title: string;
  description: string;
  authors: string;
}

interface ScrapeResult {
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

  const debouncedQuery = useDebounce(query, 500);

  const pageCountQuery = useQuery({
    queryKey: ["pageCount", debouncedQuery],
    queryFn: async () => {
      const res = await fetch(
        `/api/springer/page-count?query=${encodeURIComponent(debouncedQuery)}`
      );
      if (!res.ok) throw new Error("Failed to fetch page count");
      return res.json() as Promise<{ total_pages: number }>;
    },
    enabled: debouncedQuery.length > 2,
  });

  const scrapeMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch("/api/springer/scrape", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query,
          page_from: pageFrom,
          page_to: pageTo,
          only_full_access: onlyFullAccess,
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
        totalPages={pageCountQuery.data?.total_pages}
        isLoadingPages={pageCountQuery.isFetching}
        onScrape={() => scrapeMutation.mutate()}
        isScraping={scrapeMutation.isPending}
      />
      {scrapeMutation.data && (
        <ResultsTable
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
