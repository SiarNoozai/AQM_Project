import { useMemo, useState } from "react";
import type { ApiAnalysis, LlmPreference, RecommendationResult } from "../lib/api";
import type { ChatMessage } from "../lib/chatClient";
import { askQuestion } from "../lib/chatClient";

export type AskConversationMessage = ChatMessage & { usedMetrics?: string[]; source?: "ollama" | "cloud" | "rules" };

type AskPanelProps = {
  analysis: ApiAnalysis;
  recommendation: RecommendationResult | null;
  messages: AskConversationMessage[];
  onMessagesChange: (messages: AskConversationMessage[]) => void;
  llmPreference: LlmPreference;
};

export function AskPanel({ analysis, recommendation, messages, onMessagesChange, llmPreference }: AskPanelProps) {
  const [draft, setDraft] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const examples = useMemo(() => {
    const topAsset = [...analysis.assets].sort((left, right) => right.weight - left.weight)[0];
    return [
      `Warum ist meine Volatilität bei ${(analysis.metrics.volatility * 100).toFixed(1).replace(".", ",")} %?`,
      `Was bedeutet der Diversifikationswert von ${analysis.metrics.diversificationScore.toFixed(0)}?`,
      `Warum soll ${topAsset?.ticker ?? "eine Position"} anders gewichtet werden?`,
    ];
  }, [analysis]);

  async function submit(question = draft) {
    const content = question.trim();
    if (!content || isSending) {
      return;
    }
    setDraft("");
    setError(null);
    setIsSending(true);
    const history: ChatMessage[] = messages.map(({ role, content: messageContent }) => ({ role, content: messageContent }));
    onMessagesChange([...messages, { role: "user" as const, content }].slice(-20));
    try {
      const response = await askQuestion({ question: content, history, analysis, recommendation: recommendation ?? undefined, llmPreference });
      onMessagesChange([...messages, { role: "user" as const, content }, { role: "assistant" as const, content: response.answer, usedMetrics: response.usedMetrics, source: response.source }].slice(-20));
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Rückfrage konnte nicht geladen werden.");
    } finally {
      setIsSending(false);
    }
  }

  return (
    <section className="chat-panel ask-panel" aria-labelledby="ask-panel-title">
      <div className="chat-panel-heading">
        <div>
          <span className="section-kicker">Nach dem Report</span>
          <h2 id="ask-panel-title">Rückfragen zur Auswertung</h2>
          <p>Frage nach den Kennzahlen, Risiken und der historischen Vergleichsvariante.</p>
        </div>
        <span className="chat-count">{messages.length}/20</span>
      </div>
      {messages.length === 0 ? (
        <div className="ask-example-list">
          {examples.map((example) => <button type="button" key={example} onClick={() => void submit(example)}>{example}</button>)}
        </div>
      ) : null}
      <div className="chat-message-list" aria-live="polite" aria-label="Verlauf der Rückfragen">
        {messages.map((message, index) => (
          <div className={`chat-message ${message.role}`} key={`${message.role}-${index}-${message.content}`}>
            <span>{message.role === "user" ? "Du" : "Antwort"}</span>
            <p>{message.content}</p>
            {message.role === "assistant" ? <small>Quelle: {message.source === "cloud" ? "Cloud-API" : message.source === "ollama" ? "Ollama (lokal)" : "Regelmodus"} · Basis: {message.usedMetrics?.join(", ") || "Analyse-Digest"}</small> : null}
          </div>
        ))}
        {isSending ? <div className="chat-loading" role="status">Auswertung wird geprüft …</div> : null}
      </div>
      {messages.some((message) => message.role === "assistant" && message.source === "rules") ? (
        <div className="chat-mode-note" role="status">Regelmodus: Die Antwort wurde ausschließlich aus deinen Analysewerten gebildet.</div>
      ) : messages.some((message) => message.role === "assistant" && message.source === "cloud") ? (
        <div className="chat-mode-note" role="status">KI-Antwort verwendet: Cloud-API.</div>
      ) : null}
      {error ? <div className="notice error">{error}</div> : null}
      <div className="chat-compose">
        <label htmlFor="ask-chat-input">Deine Frage</label>
        <textarea
          id="ask-chat-input"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              void submit();
            }
          }}
          placeholder="Zum Beispiel: Was bedeutet mein Value at Risk?"
          maxLength={600}
          rows={2}
        />
        <button type="button" className="toolbar-button primary" onClick={() => void submit()} disabled={isSending || !draft.trim() || messages.length >= 20}>Senden</button>
      </div>
      <p className="chat-disclaimer">{analysis.disclaimer}</p>
    </section>
  );
}
