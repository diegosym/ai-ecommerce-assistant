import type { ConversationTurn } from "@/lib/api";

export function MessageList({ turns }: { turns: ConversationTurn[] }) {
  if (turns.length === 0) {
    return (
      <div className="conversation__empty">
        <p>Start with a product, a feature, and an optional budget.</p>
        <p>For example: “Wireless headphones with noise cancellation under $150.”</p>
      </div>
    );
  }

  return (
    <ol className="conversation__list" aria-label="Conversation">
      {turns.map((turn) => (
        <li key={turn.turnId} className={`message message--${turn.role}`}>
          <span className="message__role">{turn.role === "customer" ? "You" : "Assistant"}</span>
          <p>{turn.text}</p>
        </li>
      ))}
    </ol>
  );
}
