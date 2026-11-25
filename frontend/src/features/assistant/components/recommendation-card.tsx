import type { ProductPresentation } from "@/lib/api";

function formatPrice(product: ProductPresentation["product"]): string {
  if (product.price === null) {
    return "Price unavailable";
  }
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: product.price.currency,
  }).format(product.price.amountMinor / 100);
}

function formatAttribute(key: string, value: string | number | boolean | null): string {
  if (value === null) {
    return "Unavailable";
  }
  if (typeof value === "boolean") {
    return value ? "Yes" : "No";
  }
  return String(value);
}

export function RecommendationCard({ presentation }: { presentation: ProductPresentation }) {
  const { product } = presentation;
  return (
    <article className="product-card" data-testid="product-card">
      <div className="product-card__heading">
        <div>
          <p className="product-card__reference">Option {presentation.reference.ordinal}</p>
          <h3>{product.name}</h3>
        </div>
        <p className="product-card__price">{formatPrice(product)}</p>
      </div>
      <p className="product-card__category">{product.categoryId}</p>
      <p className="product-card__description">{product.description}</p>
      {presentation.matchedAttributes.length > 0 ? (
        <p className="product-card__matched">
          Matched: {presentation.matchedAttributes.join(", ")}
        </p>
      ) : null}
      <dl className="product-card__attributes">
        {Object.entries(product.attributes).map(([key, value]) => (
          <div key={key}>
            <dt>{key.replaceAll("-", " ")}</dt>
            <dd>{formatAttribute(key, value)}</dd>
          </div>
        ))}
      </dl>
      {presentation.unavailableFields.length > 0 ? (
        <p className="product-card__unavailable">
          Unavailable: {presentation.unavailableFields.join(", ")}
        </p>
      ) : null}
    </article>
  );
}
