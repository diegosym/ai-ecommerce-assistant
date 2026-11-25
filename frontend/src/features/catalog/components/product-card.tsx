import Link from "next/link";

import { formatAttribute, formatPrice } from "@/features/catalog/format";
import type { Product } from "@/lib/api";

export function CatalogProductCard({ product }: { product: Product }) {
  return (
    <article data-testid="catalog-product-card">
      <p>{product.categoryId}</p>
      <h2>
        <Link href={`/catalog/${product.id}`}>{product.name}</Link>
      </h2>
      <strong>{formatPrice(product.price)}</strong>
      <p>{product.description}</p>
      <dl aria-label={`${product.name} key attributes`}>
        {Object.entries(product.attributes)
          .slice(0, 3)
          .map(([key, value]) => (
            <div key={key}>
              <dt>{key.replaceAll("-", " ")}</dt>
              <dd>{formatAttribute(value)}</dd>
            </div>
          ))}
      </dl>
    </article>
  );
}
