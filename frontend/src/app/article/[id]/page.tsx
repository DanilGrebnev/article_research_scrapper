"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import Link from "next/link";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Section {
  id: number;
  title: string;
  content: string;
  heading_level: number;
  order_index: number;
}

interface Reference {
  id: number;
  ref_number: number;
  text: string;
  doi: string;
}

interface ArticleFull {
  id: number;
  title: string;
  url: string;
  published_date: string;
  authors: string;
  abstract: string | null;
  sections: Section[];
  references: Reference[];
}

export default function ArticlePage() {
  const params = useParams();
  const articleId = params.id as string;

  const { data, isLoading, error } = useQuery({
    queryKey: ["article-full", articleId],
    queryFn: async () => {
      const res = await fetch(`${API_URL}/api/article/${articleId}/full`);
      if (!res.ok) throw new Error("Не удалось загрузить статью");
      return res.json() as Promise<ArticleFull>;
    },
  });

  if (isLoading) {
    return (
      <main>
        <div className="article-page">
          <p>Загрузка статьи...</p>
        </div>
      </main>
    );
  }

  if (error || !data) {
    return (
      <main>
        <div className="article-page">
          <div className="error">
            Ошибка: {error instanceof Error ? error.message : "Не удалось загрузить"}
          </div>
          <Link href="/history" className="article-page__back">
            ← Назад к истории
          </Link>
        </div>
      </main>
    );
  }

  const hasContent = data.sections.length > 0 || data.abstract;

  return (
    <main>
      <div className="article-page">
        <Link href="/history" className="article-page__back">
          ← Назад
        </Link>

        <header className="article-page__header">
          <h1 className="article-page__title">{data.title}</h1>
          <div className="article-page__meta">
            {data.authors && data.authors !== "—" && (
              <p className="article-page__authors">{data.authors}</p>
            )}
            {data.published_date && (
              <span className="article-page__date">{data.published_date}</span>
            )}
            {data.url && (
              <a
                href={data.url}
                target="_blank"
                rel="noopener noreferrer"
                className="article-page__original-link"
              >
                Оригинал на SpringerLink ↗
              </a>
            )}
          </div>
        </header>

        {!hasContent && (
          <p className="article-page__empty">
            Полный текст статьи ещё не загружен. Нажмите &quot;Глубокий анализ&quot; в карточке статьи.
          </p>
        )}

        {data.abstract && (
          <section className="article-page__section">
            <h2>Abstract</h2>
            <p className="article-page__text">{data.abstract}</p>
          </section>
        )}

        {data.sections.map((section) =>
          section.heading_level === 2 ? (
            <section key={section.id} className="article-page__section">
              <h2>{section.title}</h2>
              {section.content.split("\n\n").map((para, i) => (
                <p key={i} className="article-page__text">
                  {para}
                </p>
              ))}
            </section>
          ) : (
            <section key={section.id} className="article-page__subsection">
              <h3>{section.title}</h3>
              {section.content.split("\n\n").map((para, i) => (
                <p key={i} className="article-page__text">
                  {para}
                </p>
              ))}
            </section>
          )
        )}

        {data.references.length > 0 && (
          <section className="article-page__section article-page__references">
            <h2>References</h2>
            <ol className="article-page__ref-list">
              {data.references.map((ref) => (
                <li key={ref.id} value={ref.ref_number}>
                  <span>{ref.text}</span>
                  {ref.doi && (
                    <a
                      href={`https://doi.org/${ref.doi}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="article-page__doi"
                    >
                      DOI
                    </a>
                  )}
                </li>
              ))}
            </ol>
          </section>
        )}
      </div>
    </main>
  );
}
