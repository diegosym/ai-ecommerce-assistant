import { expect, test } from "@playwright/test";

test("acceptance 1: anonymous category navigation lists catalog names and prices", async ({
  page,
}) => {
  await page.goto("/catalog");

  await expect(page.getByRole("heading", { name: "Browse the catalog" })).toBeVisible();
  const categories = page.getByRole("navigation", { name: "Product categories" });
  await expect(categories.getByRole("link")).toHaveCount(6);
  await categories.getByRole("link", { name: "Headphones", exact: true }).click();

  await expect(page).toHaveURL(/categoryId=headphones/);
  await expect(page.getByTestId("catalog-product-card")).toHaveCount(20);
  const firstProduct = page.getByTestId("catalog-product-card").first();
  await expect(firstProduct).toContainText("Auralis Core 01");
  await expect(firstProduct).toContainText("$79.00");
  await expect(page.getByText(/sign in/i)).toHaveCount(0);
});

test("acceptance 2: product detail shows catalog attributes and explicit unavailable values", async ({
  page,
}) => {
  await page.goto("/catalog?categoryId=headphones");
  await page.getByRole("link", { name: "Auralis Core 01", exact: true }).click();

  await expect(page).toHaveURL(/\/catalog\/headphones-001$/);
  await expect(page.getByRole("heading", { name: "Auralis Core 01" })).toBeVisible();
  await expect(page.getByText("$79.00")).toBeVisible();
  await expect(page.getByLabel("Product attributes")).toContainText("Bluetooth 5.3");

  await page.goto("/catalog/headphones-013");
  await expect(page.getByText("Price unavailable")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Auralis Core 13" })).toBeVisible();
});

test("acceptance 3: category and price filters narrow the listing deterministically", async ({
  page,
}) => {
  await page.goto("/catalog");
  await page.getByRole("combobox", { name: "Category", exact: true }).selectOption("headphones");
  await page.getByLabel("Minimum price (USD)").fill("100");
  await page.getByLabel("Maximum price (USD)").fill("150");
  await page.getByRole("button", { name: "Apply filters" }).click();

  await expect(page).toHaveURL(/categoryId=headphones/);
  await expect(page).toHaveURL(/minPriceMinor=10000/);
  await expect(page).toHaveURL(/maxPriceMinor=15000/);
  await expect(page.getByTestId("catalog-product-card")).toHaveCount(3);
  await expect(page.getByTestId("catalog-product-card")).toContainText([
    "Auralis Plus 03",
    "Auralis Pro 04",
    "Auralis Core 05",
  ]);
});

test("acceptance 4: catalog offers no standalone text or semantic search", async ({ page }) => {
  await page.goto("/catalog");

  await expect(page.getByRole("searchbox")).toHaveCount(0);
  await expect(page.getByRole("textbox")).toHaveCount(0);
  await expect(page.getByLabel(/search/i)).toHaveCount(0);
  const assistantLink = page.getByRole("link", { name: "Conversational assistant" });
  await expect(assistantLink).toBeVisible();
  await assistantLink.click();
  await expect(page.getByRole("heading", { name: "Find the right tech, in your own words." })).toBeVisible();
});

test("acceptance 5: empty filters show an explicit state and clear action", async ({ page }) => {
  await page.goto("/catalog");
  await page.getByRole("combobox", { name: "Category", exact: true }).selectOption("headphones");
  await page.getByLabel("Minimum price (USD)").fill("1");
  await page.getByLabel("Maximum price (USD)").fill("0");
  await page.getByRole("button", { name: "Apply filters" }).click();

  await expect(page.getByRole("status")).toContainText("No products match these filters.");
  await expect(page.getByTestId("catalog-product-card")).toHaveCount(0);
  await page.getByRole("button", { name: "Clear filters" }).click();

  await expect(page).toHaveURL(/\/catalog$/);
  await expect(page.getByTestId("catalog-product-card")).toHaveCount(20);
  await expect(page.getByLabel("Minimum price (USD)")).toHaveValue("");
  await expect(page.getByLabel("Maximum price (USD)")).toHaveValue("");
});
