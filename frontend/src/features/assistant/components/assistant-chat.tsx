"use client";

import { useState, type FormEvent } from "react";

import {
  createAssistantInteraction,
  createEmptyConversation,
  type AssistantInteractionResponse,
  type ConversationState,
} from "@/lib/api";
import { MessageList } from "./message-list";
import { RecommendationCard } from "./recommendation-card";

export function AssistantChat() {
  const [conversation, setConversation] = useState<ConversationState>(() =>
    createEmptyConversation(),
  );
  const [message, setMessage] = useState("");
  const [latestResult, setLatestResult] = useState<AssistantInteractionResponse | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function startNewConversation() {
    if (isSubmitting) {
      return;
    }
    setConversation(createEmptyConversation());
    setLatestResult(null);
    setMessage("");
    setError(null);
  }

  async function submitRequest(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const requestMessage = message.trim();
    if (!requestMessage || isSubmitting) {
      return;
    }

    setIsSubmitting(true);
    setError(null);
    try {
      const result = await createAssistantInteraction({ conversation, message: requestMessage });
      setConversation(result.conversation);
      setLatestResult(result);
      setMessage("");
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "The assistant could not process this request.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="shopping-assistant">
      <header className="hero">
        <p className="hero__eyebrow">Catalog-grounded discovery</p>
        <h1>Find the right tech, in your own words.</h1>
        <p className="hero__intro">
          Describe what you need. Recommendations, prices, and specifications come directly from
          the demonstration catalog—never from invented product facts.
        </p>
      </header>

      <section className="chat-panel" aria-label="Shopping assistant">
        <div className="chat-panel__status">
          <span className="status-dot" aria-hidden="true" />
          <span>Synthetic catalog · deterministic assistant</span>
          <button type="button" onClick={startNewConversation} disabled={isSubmitting}>
            New conversation
          </button>
        </div>
        <MessageList turns={conversation.turns} />

        {latestResult?.presentations.length ? (
          <section className="recommendations" aria-label="Recommended products">
            <div className="recommendations__heading">
              <h2>Matched to your request</h2>
              <span>{latestResult.presentations.length} catalog products</span>
            </div>
            <div className="recommendations__grid">
              {latestResult.presentations.map((presentation) => (
                <RecommendationCard
                  key={presentation.product.id}
                  presentation={presentation}
                />
              ))}
            </div>
          </section>
        ) : null}

        {latestResult?.relaxations.length ? (
          <section className="relaxations" aria-label="Suggested relaxations">
            <h2>Try relaxing one requirement</h2>
            <ul>
              {latestResult.relaxations.map((relaxation) => (
                <li key={relaxation.preferenceId}>
                  <strong>{relaxation.label}</strong>
                  <span>
                    {relaxation.resultCount} {relaxation.resultCount === 1 ? "match" : "matches"}
                  </span>
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        {error ? (
          <p className="request-error" role="alert">
            {error}
          </p>
        ) : null}

        <form className="request-form" onSubmit={submitRequest}>
          <label htmlFor="assistant-message">Describe what you need</label>
          <div className="request-form__controls">
            <textarea
              id="assistant-message"
              value={message}
              onChange={(event) => setMessage(event.target.value)}
              placeholder="e.g. Noise-cancelling wireless headphones under $150"
              maxLength={4000}
              rows={3}
              required
            />
            <button type="submit" disabled={isSubmitting || !message.trim()}>
              {isSubmitting ? "Finding products…" : "Find products"}
            </button>
          </div>
          <p>Your conversation stays in this page and resets when you reload.</p>
        </form>
      </section>
    </main>
  );
}
