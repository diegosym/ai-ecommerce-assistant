import type { AttributeValue, Money } from "@/lib/api";

export function formatPrice(price: Money | null): string {
  if (price === null) {
    return "Price unavailable";
  }
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: price.currency,
  }).format(price.amountMinor / 100);
}

export function formatAttribute(value: AttributeValue | undefined): string {
  if (value === null || value === undefined) {
    return "Unavailable";
  }
  if (typeof value === "boolean") {
    return value ? "Yes" : "No";
  }
  return String(value);
}
