import Link from "next/link";

import { CatalogFilterForm } from "@/features/catalog/components/catalog-filter-form";
import { CatalogProductCard } from "@/features/catalog/components/product-card";
import {
  listCatalogCategories,
  listCatalogProducts,
  type CatalogProductFilters,
} from "@/lib/api";
import styles from "./catalog.module.css";

interface CatalogPageProps {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}

export default async function CatalogPage({ searchParams }: CatalogPageProps) {
  const parameters = await searchParams;
  const filters: CatalogProductFilters = {
    categoryId: stringParameter(parameters.categoryId),
    minPriceMinor: nonNegativeInteger(parameters.minPriceMinor),
    maxPriceMinor: nonNegativeInteger(parameters.maxPriceMinor),
    currency: "USD",
    page: 1,
    pageSize: 20,
  };
  const [categories, products] = await Promise.all([
    listCatalogCategories(),
    listCatalogProducts(filters),
  ]);

  return (
    <main className={styles.catalog}>
      <header className={styles.header}>
        <div>
          <p>Conventional product browsing</p>
          <h1>Browse the catalog</h1>
          <p>
            Explore categories, deterministic price filters, and catalog-backed specifications.
          </p>
        </div>
        <Link href="/">Conversational assistant</Link>
      </header>

      <nav className={styles.categories} aria-label="Product categories">
        <Link href="/catalog" aria-current={!filters.categoryId ? "page" : undefined}>
          All products
        </Link>
        {categories.items.map((category) => (
          <Link
            key={category.id}
            href={`/catalog?categoryId=${category.id}`}
            aria-current={filters.categoryId === category.id ? "page" : undefined}
          >
            {category.name}
          </Link>
        ))}
      </nav>

      <CatalogFilterForm
        key={JSON.stringify(filters)}
        categories={categories.items}
        initialFilters={filters}
        resultCount={products.total}
      />

      <section className={styles.listing} aria-label="Product listing">
        <div className={styles.listingHeading}>
          <h2>{filters.categoryId ?? "All products"}</h2>
          <p>
            {products.total} products · catalog {products.catalogVersion}
          </p>
        </div>
        <div className={styles.grid}>
          {products.items.map((product) => (
            <CatalogProductCard key={product.id} product={product} />
          ))}
        </div>
      </section>
    </main>
  );
}

function stringParameter(value: string | string[] | undefined): string | undefined {
  return typeof value === "string" && value ? value : undefined;
}

function nonNegativeInteger(value: string | string[] | undefined): number | undefined {
  const text = stringParameter(value);
  if (text === undefined || !/^\d+$/.test(text)) {
    return undefined;
  }
  return Number(text);
}
