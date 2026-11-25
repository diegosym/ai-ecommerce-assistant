import { expect, test, type Page } from "@playwright/test";

import type { AssistantInteractionResponse } from "../../frontend/src/lib/api";

async function sendMessage(page: Page, message: string): Promise<AssistantInteractionResponse> {
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

async function expectNoPersistentStorage(page: Page): Promise<void> {
  expect(await page.context().cookies()).toEqual([]);
  expect(await page.evaluate(() => window.localStorage.length)).toBe(0);
}

function expectFreshFollowUp(
  first: AssistantInteractionResponse,
  second: AssistantInteractionResponse,
): void {
  expect(second.conversation.conversationId).not.toBe(first.conversation.conversationId);
  expect(second.conversation.turns).toHaveLength(2);
  expect(second.conversation.turns[0].text).toBe("Show me laptops under $1000");
  expect(second.conversation.presentedProducts.length).toBeGreaterThan(0);
  expect(second.conversation.presentedProducts[0].ordinal).toBe(1);
  expect(
    second.conversation.preferences.some(
      (preference) => {
        const value = preference.value as { id?: string; amountMinor?: number };
        return (
          preference.slot === "characteristic" ||
          value.id === "headphones" ||
          value.amountMinor === 15000
        );
      },
    ),
  ).toBe(false);
  expect(second.conversation.preferences).toHaveLength(2);
}

test("New conversation replaces the ID and clears all context without persistence", async ({
  page,
}) => {
  await page.goto("/");
  const first = await sendMessage(page, "Wireless headphones under $150");
  expect(first.conversation.preferences.length).toBeGreaterThan(0);
  await expectNoPersistentStorage(page);

  await page.getByRole("button", { name: "New conversation" }).click();

  await expect(page.getByText("Start with a product, a feature, and an optional budget.")).toBeVisible();
  await expect(page.getByText("Wireless headphones under $150")).toHaveCount(0);
  await expect(page.getByTestId("product-card")).toHaveCount(0);
  await expectNoPersistentStorage(page);

  const second = await sendMessage(page, "Show me laptops under $1000");
  expectFreshFollowUp(first, second);
  await expectNoPersistentStorage(page);
});

test("full reload starts a fresh conversation with no cookie or localStorage restoration", async ({
  page,
}) => {
  await page.goto("/");
  const first = await sendMessage(page, "Wireless headphones under $150");
  await expectNoPersistentStorage(page);

  await page.reload();

  await expect(page.getByText("Start with a product, a feature, and an optional budget.")).toBeVisible();
  await expect(page.getByText("Wireless headphones under $150")).toHaveCount(0);
  await expect(page.getByTestId("product-card")).toHaveCount(0);
  await expectNoPersistentStorage(page);

  const second = await sendMessage(page, "Show me laptops under $1000");
  expectFreshFollowUp(first, second);
  await expectNoPersistentStorage(page);
});
