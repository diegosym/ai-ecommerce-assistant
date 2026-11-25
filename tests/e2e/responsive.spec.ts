import { expect, test, type Page } from "@playwright/test";

import type { AssistantInteractionResponse } from "../../frontend/src/lib/api";

const viewports = [
  { name: "phone", width: 390, height: 844 },
  { name: "tablet", width: 768, height: 1024 },
  { name: "desktop", width: 1440, height: 1000 },
];

async function sendMessage(page: Page, message: string): Promise<AssistantInteractionResponse> {
  await page.getByLabel("Describe what you need").fill(message);
  const pending = page.waitForResponse(
    (response) =>
      response.url().includes("/api/v1/assistant/interactions") &&
      response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Find products" }).click();
  const response = await pending;
  expect(response.ok()).toBe(true);
  return (await response.json()) as AssistantInteractionResponse;
}

for (const viewport of viewports) {
  test(`grounded cards and stable ordinals are responsive on ${viewport.name}`, async ({
    page,
  }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto("/");
    const discovery = await sendMessage(
      page,
      "Wireless headphones with noise cancellation under $150",
    );

    const first = discovery.presentations[0];
    const second = discovery.presentations[1];
    expect(first.reference.ordinal).toBe(1);
    expect(second.reference.ordinal).toBe(2);
    const firstCard = page.getByTestId("product-card").filter({ hasText: first.product.name });
    await expect(firstCard).toContainText("Option 1");
    await expect(firstCard).toContainText("$94.00");
    await expect(firstCard).toContainText("Matched: connectivity, noise-cancellation");

    const later = await sendMessage(page, "What is the battery life of the second product?");
    expect(later.presentations[0].product.id).toBe(second.product.id);
    expect(later.presentations[0].reference).toEqual(second.reference);

    const firstAgain = await sendMessage(page, "What is the price of the first product?");
    expect(firstAgain.presentations[0].product.id).toBe(first.product.id);
    expect(firstAgain.presentations[0].reference).toEqual(first.reference);
    await expect(page.getByTestId("product-card")).toContainText("Option 1");

    const missingPrice = await sendMessage(page, "What is the price of headphones-013?");
    expect(missingPrice.presentations[0].unavailableFields).toContain("price");
    await expect(page.getByTestId("product-card")).toContainText("Price unavailable");

    const missingAttribute = await sendMessage(
      page,
      "Does headphones-015 have noise cancellation?",
    );
    expect(missingAttribute.presentations[0].unavailableFields).toContain("noise-cancellation");
    const unavailableCard = page.getByTestId("product-card");
    await expect(unavailableCard).toContainText("noise cancellation");
    await expect(unavailableCard).toContainText("Unavailable");

    const hasOverflow = await page.evaluate(
      () => document.documentElement.scrollWidth > window.innerWidth + 1,
    );
    expect(hasOverflow).toBe(false);
  });
}
