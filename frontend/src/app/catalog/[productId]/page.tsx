import Link from "next/link";

import { formatAttribute, formatPrice } from "@/features/catalog/format";
import { getCatalogProduct, listCatalogCategories } from "@/lib/api";
import styles from "../catalog.module.css";

interface ProductDetailPageProps {
  params: Promise<{ productId: string }>;
}

export default async function ProductDetailPage({ params }: ProductDetailPageProps) {
  const { productId } = await params;
  const [{ product, catalogVersion }, categories] = await Promise.all([
    getCatalogProduct(productId),
    listCatalogCategories(),
  ]);
  const category = categories.items.find((item) => item.id === product.categoryId);
  const attributeDefinitions = category?.attributeDefinitions ?? [];

  return (
    <main className={styles.catalog}>
      <Link href={`/catalog?categoryId=${product.categoryId}`}>← Back to catalog</Link>
      <article className={styles.detail}>
        <p>{category?.name ?? product.categoryId}</p>
        <h1>{product.name}</h1>
        <strong className={styles.detailPrice}>{formatPrice(product.price)}</strong>
        <p>{product.description}</p>
        <p>Catalog version {catalogVersion}</p>
        <h2>Specifications</h2>
        <dl className={styles.attributes} aria-label="Product attributes">
          {attributeDefinitions.map((definition) => (
            <div key={definition.key}>
              <dt>
                {definition.label}
                {definition.unit ? ` (${definition.unit})` : ""}
              </dt>
              <dd>{formatAttribute(product.attributes[definition.key])}</dd>
            </div>
          ))}
        </dl>
      </article>
    </main>
  );
}
