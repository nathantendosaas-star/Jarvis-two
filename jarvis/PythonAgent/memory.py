"""
Rolling conversation memory. Once the message count crosses a threshold,
the older messages get compressed into a summary and dropped, keeping the
last few messages verbatim. This is what lets the agent run long sessions
without blowing the context window or the API bill.
"""

from llm import chat


class ConversationMemory:
    def __init__(self, system_prompt, summarize_after=24, keep_last=8):
        self.system_prompt = system_prompt
        self.summarize_after = summarize_after
        self.keep_last = keep_last
        self.messages = [{"role": "system", "content": system_prompt}]

    def add(self, role, content):
        self.messages.append({"role": role, "content": content})
        if len(self.messages) > self.summarize_after:
            self._summarize()

    def _summarize(self):
        to_summarize = self.messages[1:-self.keep_last]
        if not to_summarize:
            return

        summary_request = [
            {
                "role": "system",
                "content": (
                    "Summarize the conversation so far for future memory. "
                    "Keep concrete facts: file names, paths, decisions made, "
                    "objectives, and anything explicitly asked to be "
                    "remembered. Be dense and factual, not chatty."
                ),
            }
        ]
        summary_request.extend(to_summarize)

        try:
            result = chat(summary_request)
            summary_text = (result.get("content") or "").strip()
        except Exception:
            return  # if summarization fails, just skip it this round -- don't crash the session

        if not summary_text:
            return

        recent = self.messages[-self.keep_last:]
        self.messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "system", "content": "Earlier conversation memory:\n" + summary_text},
        ] + recent
