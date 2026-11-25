export type AttributeValue = string | number | boolean | null;

export interface Money {
  amountMinor: number;
  currency: string;
}

export interface Product {
  id: string;
  name: string;
  categoryId: string;
  description: string;
  price: Money | null;
  attributes: Record<string, AttributeValue>;
}

export interface AttributeDefinition {
  key: string;
  label: string;
  valueType: "string" | "number" | "boolean";
  unit?: string;
  filterable: boolean;
}

export interface Category {
  id: string;
  name: string;
  description: string;
  attributeDefinitions: AttributeDefinition[];
}

export interface CategoryListResponse {
  catalogVersion: string;
  items: Category[];
}

export interface ProductListResponse {
  catalogVersion: string;
  items: Product[];
  page: number;
  pageSize: number;
  total: number;
}

export interface ProductResponse {
  catalogVersion: string;
  product: Product;
}

export interface CatalogProductFilters {
  categoryId?: string;
  minPriceMinor?: number;
  maxPriceMinor?: number;
  currency?: string;
  page?: number;
  pageSize?: number;
}

export interface ConversationTurn {
  turnId: string;
  role: "customer" | "assistant";
  text: string;
  createdAt: string;
  interactionId?: string | null;
}

export interface CustomerPreference {
  preferenceId: string;
  slot: "category" | "characteristic" | "budget" | "other";
  key?: string | null;
  nature: "requirement" | "belief";
  value: unknown;
  sourceTurnId: string;
  status: "active" | "replaced";
}

export interface PresentedProductReference {
  ordinal: number;
  productId: string;
  firstPresentedTurnId: string;
}

export interface ConversationState {
  conversationId: string;
  createdAt: string;
  turns: ConversationTurn[];
  preferences: CustomerPreference[];
  presentedProducts: PresentedProductReference[];
}

export interface GroundingReference {
  productId: string;
  fields: string[];
}

export interface ProductPresentation {
  reference: PresentedProductReference;
  product: Product;
  matchedAttributes: string[];
  unavailableFields: string[];
  grounding: GroundingReference[];
}

export interface RelaxationSuggestion {
  preferenceId: string;
  label: string;
  resultCount: number;
}

export interface AssistantInteractionResponse {
  conversation: ConversationState;
  reply: {
    kind:
      | "recommendations"
      | "answer"
      | "clarification"
      | "no_match"
      | "out_of_scope"
      | "unavailable";
    text: string;
  };
  presentations: ProductPresentation[];
  relaxations: RelaxationSuggestion[];
  measurements: {
    interactionId: string;
    latencyMs: number;
    inputTokens: number | null;
    outputTokens: number | null;
    estimatedCostMinor: number | null;
    currency: string | null;
    pricingVersion: string | null;
  };
  catalogVersion: string | null;
}

export interface AssistantInteractionRequest {
  conversation: ConversationState;
  message: string;
}

interface ErrorResponse {
  error: { code: string; message: string; retryable: boolean };
  interactionId: string | null;
}

const API_BASE_URL =
  process.env.NEXT_PUBLIC_ASSISTANT_API_URL ??
  (typeof window === "undefined"
    ? (process.env.ASSISTANT_API_URL ?? "http://127.0.0.1:18000/api/v1")
    : "/api/v1");

export function createEmptyConversation(): ConversationState {
  return {
    conversationId: crypto.randomUUID(),
    createdAt: new Date().toISOString(),
    turns: [],
    preferences: [],
    presentedProducts: [],
  };
}

export async function listCatalogCategories(): Promise<CategoryListResponse> {
  return catalogRequest<CategoryListResponse>("/catalog/categories");
}

export async function listCatalogProducts(
  filters: CatalogProductFilters = {},
): Promise<ProductListResponse> {
  const parameters = new URLSearchParams();
  for (const [name, value] of Object.entries(filters)) {
    if (value !== undefined) {
      parameters.set(name, String(value));
    }
  }
  const query = parameters.toString();
  return catalogRequest<ProductListResponse>(`/catalog/products${query ? `?${query}` : ""}`);
}

export async function getCatalogProduct(productId: string): Promise<ProductResponse> {
  return catalogRequest<ProductResponse>(`/catalog/products/${productId}`);
}

async function catalogRequest<Response>(path: string): Promise<Response> {
  const response = await fetch(`${API_BASE_URL}${path}`, { cache: "no-store" });
  const body = (await response.json()) as Response | ErrorResponse;
  if (!response.ok) {
    const error = body as ErrorResponse;
    throw new Error(error.error?.message ?? "The catalog could not process this request.");
  }
  return body as Response;
}

export async function createAssistantInteraction(
  request: AssistantInteractionRequest,
): Promise<AssistantInteractionResponse> {
  const response = await fetch(`${API_BASE_URL}/assistant/interactions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  const body = (await response.json()) as AssistantInteractionResponse | ErrorResponse;
  if (!response.ok) {
    const error = body as ErrorResponse;
    throw new Error(error.error?.message ?? "The assistant could not process this request.");
  }
  return body as AssistantInteractionResponse;
}
