# Demo evidence

Real local captures from the completed application using PostgreSQL on 55434, FastAPI on 18000, Next.js on 3000, `AI_PROVIDER=fake`, and `AI_RETRIEVAL=lexical`. No images were generated or edited.

## Screenshots

- [Chat discovery](chat-discovery.png) — the quickstart request “I need wireless headphones with noise cancellation for $150.” with two grounded recommendations and catalog prices.
- [Headphones catalog](catalog-headphones.png) — conventional category navigation and product listing.
- [Product detail](catalog-product-detail.png) — catalog-hydrated price and specifications for Auralis Core 01.

## Captured transcript

[transcript.json](transcript.json) records actual HTTP responses and screenshot filenames:

- `GET /api/v1/catalog/categories` → 200, five category IDs.
- `GET /api/v1/catalog/products?categoryId=headphones&maxPriceMinor=15000&currency=USD` → 200, five matching products.
- Assistant discovery → `kind: recommendations`; `headphones-002` at 9400 USD minor units and `headphones-004` at 12400 USD minor units, with grounding references.

The chat capture was refreshed after the quickstart parser regression test confirmed that `for $150` applies the budget without a missing-budget assumption. The transcript contains the corrected response text and product values.
