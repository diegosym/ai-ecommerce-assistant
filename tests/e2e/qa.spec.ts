import { expect, test, type Page } from "@playwright/test";

import type { AssistantInteractionResponse } from "../../frontend/src/lib/api";

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

async function startWithHeadphones(page: Page): Promise<AssistantInteractionResponse> {
  await page.goto("/");
  return sendMessage(page, "Wireless headphones with noise cancellation under $150");
}

test("acceptance 1: a presented product question is answered from catalog evidence", async ({
  page,
}) => {
  await startWithHeadphones(page);

  const answer = await sendMessage(page, "Does the first one have noise cancellation?");

  expect(answer.reply.kind).toBe("answer");
  expect(answer.presentations[0].product.attributes["noise-cancellation"]).toBe(true);
  await expect(
    page.getByRole("list", { name: "Conversation" }).getByText(/Auralis Air 02.*noise cancellation/i),
  ).toBeVisible();
});

test("acceptance 2: missing catalog evidence is stated as unavailable", async ({ page }) => {
  await startWithHeadphones(page);

  const answer = await sendMessage(page, "Is there a warranty on the first product?");

  expect(answer.reply.kind).toBe("unavailable");
  expect(answer.presentations[0].unavailableFields).toContain("warranty");
  await expect(page.getByText(/warranty information is not available/i)).toBeVisible();
});

test("acceptance 3: a customer price belief is distinguished from the verified catalog price", async ({
  page,
}) => {
  await startWithHeadphones(page);

  const answer = await sendMessage(
    page,
    "I thought the first one was $99. What is its actual price?",
  );

  expect(answer.reply.kind).toBe("answer");
  expect(answer.presentations[0].product.price?.amountMinor).toBe(9400);
  await expect(page.getByText(/stated belief was \$99\.00/i)).toBeVisible();
  await expect(page.getByText(/verified catalog price.*\$94\.00/i)).toBeVisible();
});
