"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import type { CatalogProductFilters, Category } from "@/lib/api";

interface CatalogFilterFormProps {
  categories: Category[];
  initialFilters: CatalogProductFilters;
  resultCount: number;
}

export function CatalogFilterForm({
  categories,
  initialFilters,
  resultCount,
}: CatalogFilterFormProps) {
  const router = useRouter();
  const [categoryId, setCategoryId] = useState(initialFilters.categoryId ?? "");
  const [minimum, setMinimum] = useState(toDollars(initialFilters.minPriceMinor));
  const [maximum, setMaximum] = useState(toDollars(initialFilters.maxPriceMinor));

  function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const parameters = new URLSearchParams();
    if (categoryId) {
      parameters.set("categoryId", categoryId);
    }
    if (minimum) {
      parameters.set("minPriceMinor", String(Math.round(Number(minimum) * 100)));
    }
    if (maximum) {
      parameters.set("maxPriceMinor", String(Math.round(Number(maximum) * 100)));
    }
    const query = parameters.toString();
    router.push(`/catalog${query ? `?${query}` : ""}`);
  }

  function clearFilters() {
    setCategoryId("");
    setMinimum("");
    setMaximum("");
    router.push("/catalog");
  }

  return (
    <div>
      <form aria-label="Catalog filters" onSubmit={applyFilters}>
        <label>
          Category
          <select value={categoryId} onChange={(event) => setCategoryId(event.target.value)}>
            <option value="">All categories</option>
            {categories.map((category) => (
              <option key={category.id} value={category.id}>
                {category.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Minimum price (USD)
          <input
            type="number"
            min="0"
            step="0.01"
            inputMode="decimal"
            value={minimum}
            onChange={(event) => setMinimum(event.target.value)}
          />
        </label>
        <label>
          Maximum price (USD)
          <input
            type="number"
            min="0"
            step="0.01"
            inputMode="decimal"
            value={maximum}
            onChange={(event) => setMaximum(event.target.value)}
          />
        </label>
        <button type="submit">Apply filters</button>
      </form>
      {resultCount === 0 ? (
        <div role="status">
          <h2>No products match these filters.</h2>
          <p>Try a different category or price range, or clear all filters.</p>
          <button type="button" onClick={clearFilters}>
            Clear filters
          </button>
        </div>
      ) : null}
    </div>
  );
}

function toDollars(amountMinor: number | undefined): string {
  return amountMinor === undefined ? "" : String(amountMinor / 100);
}
