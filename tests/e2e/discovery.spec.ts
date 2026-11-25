import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { expect, test, type Page } from "@playwright/test";

import type { AssistantInteractionResponse } from "../../frontend/src/lib/api";

interface CatalogProduct {
  id: string;
  name: string;
  categoryId: string;
  description: string;
  price: { amountMinor: number; currency: string } | null;
  attributes: Record<string, string | number | boolean | null>;
}

const catalog = JSON.parse(
  readFileSync(resolve(__dirname, "../../data/catalog/catalog.json"), "utf8"),
) as { products: CatalogProduct[] };
const productsById = new Map(catalog.products.map((product) => [product.id, product]));

async function submitDiscovery(
  page: Page,
  message: string,
): Promise<AssistantInteractionResponse> {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Find the right tech, in your own words." })).toBeVisible();
  await page.getByLabel("Describe what you need").fill(message);
  const responsePromise = page.waitForResponse(
    (response) =>
      response.url().includes("/api/v1/assistant/interactions") &&
      response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Find products" }).click();
  const response = await responsePromise;
  expect(response.ok()).toBe(true);
  return (await response.json()) as AssistantInteractionResponse;
}

test("acceptance 1: category, characteristics and budget produce matching recommendations", async ({
  page,
}) => {
  const result = await submitDiscovery(
    page,
    "I need wireless headphones for working, with noise cancellation and a budget of $150.",
  );

  expect(result.reply.kind).toBe("recommendations");
  await expect(page.getByRole("heading", { name: "Matched to your request" })).toBeVisible();
  await expect(page.getByTestId("product-card")).toHaveCount(2);
  const air = page.getByTestId("product-card").filter({ hasText: "Auralis Air 02" });
  const pro = page.getByTestId("product-card").filter({ hasText: "Auralis Pro 04" });
  await expect(air).toContainText("$94.00");
  await expect(pro).toContainText("$124.00");
  await expect(air).toContainText("noise cancellation");
});

test("acceptance 2: contradictory constraints return no-match and computed relaxations", async ({
  page,
}) => {
  const result = await submitDiscovery(
    page,
    "I need wireless headphones with noise cancellation under $50.",
  );

  expect(result.reply.kind).toBe("no_match");
  expect(result.presentations).toEqual([]);
  expect(result.relaxations.length).toBeGreaterThan(0);
  await expect(page.getByText("No catalog products match all of your stated requirements.")).toBeVisible();
  await expect(page.getByRole("region", { name: "Suggested relaxations" })).toContainText(
    "Increase the $50.00 budget",
  );
  await expect(page.getByTestId("product-card")).toHaveCount(0);
});

test("acceptance 3: every displayed product and price is traceable to the catalog", async ({
  page,
}) => {
  const result = await submitDiscovery(
    page,
    "Wireless headphones with noise cancellation under $150",
  );

  expect(result.presentations.length).toBeGreaterThan(0);
  for (const presentation of result.presentations) {
    const catalogProduct = productsById.get(presentation.product.id);
    expect(catalogProduct).toBeDefined();
    expect(presentation.product).toEqual(catalogProduct);
    expect(presentation.grounding[0].fields).toEqual(
      expect.arrayContaining(["name", "price", "attributes.noise-cancellation"]),
    );
    if (catalogProduct?.price) {
      const formattedPrice = new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: catalogProduct.price.currency,
      }).format(catalogProduct.price.amountMinor / 100);
      await expect(
        page.getByTestId("product-card").filter({ hasText: catalogProduct.name }),
      ).toContainText(formattedPrice);
    }
  }
});

test("acceptance 4: missing budget proceeds with an explicitly stated assumption", async ({
  page,
}) => {
  const result = await submitDiscovery(page, "Show me noise-cancelling headphones");

  expect(result.reply.kind).toBe("recommendations");
  expect(result.reply.text).toContain("No budget was stated");
  await expect(page.getByText(/No budget was stated, so matching products are shown at any price/)).toBeVisible();
  await expect(page.getByTestId("product-card").first()).toBeVisible();
});
