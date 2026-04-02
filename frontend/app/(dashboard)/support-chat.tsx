"use client";

import { useState, useRef, useEffect } from "react";

interface Message {
  id: string;
  role: "user" | "bot" | "thinking";
  text: string;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function SupportChat() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    { id: "1", role: "bot", text: "Hey! I can help with tasks, projects, content, billing, or GitHub integration. Ask away." },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const send = async () => {
    if (!input.trim() || loading) return;
    const text = input.trim();
    setMessages((prev) => [...prev, { id: Date.now().toString(), role: "user", text }]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch(`${API_URL}/support/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });
      const data = await res.json();
      setMessages((prev) => [...prev, { id: (Date.now() + 1).toString(), role: "bot", text: data.reply || "I'll look into that." }]);
    } catch {
      setMessages((prev) => [...prev, { id: (Date.now() + 1).toString(), role: "bot", text: "Connection error. Try again." }]);
    }
    setLoading(false);
  };

  return (
    <>
      {/* Floating bubble */}
      <button
        onClick={() => setOpen(!open)}
        className="fixed bottom-6 right-6 z-[9999] w-12 h-12 rounded-full bg-cyan-500 text-black flex items-center justify-center text-xl shadow-lg shadow-cyan-500/20 hover:scale-105 transition-transform"
        title="Need help?"
      >
        ?
      </button>

      {/* Chat panel */}
      {open && (
        <div className="fixed bottom-20 right-6 z-[9999] w-[340px] max-h-[480px] bg-card border border-border rounded-xl shadow-2xl flex flex-col overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-border">
            <span className="text-sm font-semibold">Operator Support</span>
            <button onClick={() => setOpen(false)} className="text-muted-foreground hover:text-foreground text-lg">&times;</button>
          </div>

          {/* Messages */}
          <div ref={scrollRef} className="flex-1 overflow-y-auto px-3 py-3 space-y-2 min-h-[200px] max-h-[340px]">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`text-sm rounded-lg px-3 py-2 max-w-[85%] animate-in fade-in slide-in-from-bottom-1 duration-200 ${
                  msg.role === "user"
                    ? "ml-auto bg-cyan-500 text-black rounded-br-sm"
                    : msg.role === "thinking"
                    ? "mr-auto bg-cyan-500/5 border-l-2 border-cyan-500/40 rounded-bl-sm"
                    : "mr-auto bg-muted rounded-bl-sm"
                }`}
              >
                {msg.text}
              </div>
            ))}
            {loading && <div className="text-xs text-muted-foreground italic animate-pulse">Thinking...</div>}
          </div>

          {/* Input */}
          <div className="flex gap-2 px-3 py-3 border-t border-border">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && send()}
              placeholder="Ask a question..."
              className="flex-1 bg-background border border-border rounded-lg px-3 py-2 text-sm outline-none focus:border-cyan-500"
            />
            <button
              onClick={send}
              disabled={!input.trim() || loading}
              className="bg-cyan-500 text-black rounded-lg px-3 py-2 text-sm font-semibold disabled:opacity-50"
            >
              ↑
            </button>
          </div>
        </div>
      )}
    </>
  );
}
