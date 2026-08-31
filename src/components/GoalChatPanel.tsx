import { useState } from "react";
import type { ChatMessage, GoalChatResponse, GoalChatPayload, WizardProposal } from "../lib/chatClient";
import { sendGoalChatMessage } from "../lib/chatClient";

type GoalChatPanelProps = {
  messages: ChatMessage[];
  onMessagesChange: (messages: ChatMessage[]) => void;
  proposal: WizardProposal | null;
  onProposalChange: (proposal: WizardProposal | null) => void;
  portfolioPreview: GoalChatPayload["portfolioPreview"];
  currentSelection?: WizardProposal;
  onApply: (proposal: WizardProposal) => void;
};

export function GoalChatPanel({
  messages,
  onMessagesChange,
  proposal,
  onProposalChange,
  portfolioPreview,
  currentSelection,
  onApply,
}: GoalChatPanelProps) {
  const [draft, setDraft] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastResponse, setLastResponse] = useState<GoalChatResponse | null>(null);

  async function submit() {
    const content = draft.trim();
    if (!content || isSending) {
      return;
    }
    if (messages.length >= 20) {
      setError("Das Gespräch ist auf 20 Nachrichten begrenzt. Bitte nutze den Reset-Button, um neu zu starten.");
      return;
    }

    const nextMessages = [...messages, { role: "user" as const, content }];
    setDraft("");
    setError(null);
    setIsSending(true);
    onMessagesChange(nextMessages);
    try {
      const response = await sendGoalChatMessage({
        messages: nextMessages,
        portfolioPreview,
        currentSelection,
      });
      const assistantMessage = { role: "assistant" as const, content: response.reply };
      onMessagesChange([...nextMessages, assistantMessage].slice(-20));
      onProposalChange(response.proposal);
      setLastResponse(response);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Zielgespräch konnte nicht geladen werden.");
    } finally {
      setIsSending(false);
    }
  }

  return (
    <section className="chat-panel goal-chat-panel" aria-labelledby="goal-chat-title">
      <div className="chat-panel-heading">
        <div>
          <span className="section-kicker">Optional</span>
          <h2 id="goal-chat-title">Ziel im Gespräch klären</h2>
          <p>Beschreibe in eigenen Worten, was du mit diesem Portfolio erreichen willst und was dir die Analyse beantworten soll.</p>
        </div>
        <span className="chat-count">{messages.length}/20</span>
      </div>
      {lastResponse?.source === "rules" ? (
        <div className="chat-mode-note" role="status">Regelmodus: Die Antwort nutzt feste Zuordnungen, weil kein Ollama-Modell erreichbar war.</div>
      ) : null}
      <div className="chat-message-list" aria-live="polite" aria-label="Verlauf des Zielgesprächs">
        {messages.length === 0 ? <p className="chat-empty">Noch keine Nachricht. Ein Satz zu deinem Ziel reicht als Einstieg.</p> : null}
        {messages.map((message, index) => (
          <div className={`chat-message ${message.role}`} key={`${message.role}-${index}-${message.content}`}>
            <span>{message.role === "user" ? "Du" : "Assistent"}</span>
            <p>{message.content}</p>
          </div>
        ))}
        {isSending ? <div className="chat-loading" role="status">Antwort wird vorbereitet …</div> : null}
      </div>
      {proposal ? (
        <div className="proposal-card">
          <div className="proposal-heading"><strong>Vorschlag für den Wizard</strong><span>{lastResponse?.confidence ?? "medium"}</span></div>
          <div className="proposal-chips">
            <span>Fokus: {proposal.focusAreas.join(", ")}</span>
            <span>Zeithorizont: {proposal.timeHorizon}</span>
            <span>Risiko: {proposal.riskStyle}</span>
            <span>Ziel: {proposal.goalPreset}</span>
          </div>
          <p>{proposal.reasoning}</p>
          <div className="proposal-actions">
            <button type="button" className="toolbar-button primary-outline" onClick={() => onApply(proposal)}>Übernehmen</button>
            <button type="button" className="ghost-button" onClick={() => onProposalChange(null)}>Verwerfen</button>
          </div>
        </div>
      ) : null}
      {error ? <div className="notice error">{error}</div> : null}
      <div className="chat-compose">
        <label htmlFor="goal-chat-input">Deine Nachricht</label>
        <textarea
          id="goal-chat-input"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              void submit();
            }
          }}
          placeholder="Zum Beispiel: Ich spare für die Rente und möchte wenig Risiko."
          maxLength={2000}
          rows={3}
        />
        <button type="button" className="toolbar-button primary" onClick={() => void submit()} disabled={isSending || !draft.trim() || messages.length >= 20}>
          {isSending ? "Wird gesendet …" : "Senden"}
        </button>
      </div>
    </section>
  );
}
