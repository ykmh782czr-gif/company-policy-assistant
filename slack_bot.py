"""Answer @mentions in Slack using the full company policy database."""
import logging
import os
import re
import threading

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

import compare_methods as methods

LOCK = threading.Lock()


def answer_question(question):
    # Serialize requests because the generation helper tracks exhausted models.
    with LOCK:
        result = methods.llm_no_vector(question)
    if result["status"] != "ok":
        return "The policy service is temporarily unavailable. Please try again later."
    title = result["relevant_policy"]
    if title and title not in {p["title"] for p in methods.policies}:
        return "I could not verify the policy named in this response. Please try again."
    return f"Relevant policy: {title or 'None'}\nAnswer: {result['answer']}"


def build_app(token):
    app = App(token=token)

    @app.event("app_mention")
    def on_mention(event, say, logger):
        if event.get("bot_id") or event.get("subtype"):
            return
        question = re.sub(r"<@[A-Z0-9]+>", "", event.get("text", "")).strip()
        thread = event.get("thread_ts") or event["ts"]
        if not question:
            text = "Ask me a company policy question, for example: What should I wear to work?"
        elif len(question) > 2000:
            text = "Please shorten your policy question to 2,000 characters or fewer."
        else:
            try:
                text = answer_question(question)
            except Exception as error:
                logger.error("Policy request failed (%s).", type(error).__name__)
                text = "The policy service is temporarily unavailable. Please try again later."
        # Plain-text blocks prevent model output from creating Slack mentions or links.
        say(text=text, thread_ts=thread,
            blocks=[{"type": "section", "text": {"type": "plain_text", "text": text[:3000]}}],
            unfurl_links=False, unfurl_media=False)

    return app


def main():
    methods.initialize()
    bot_token = os.getenv("SLACK_BOT_TOKEN")
    app_token = os.getenv("SLACK_APP_TOKEN")
    if not bot_token or not app_token:
        raise ValueError("Set SLACK_BOT_TOKEN and SLACK_APP_TOKEN in your local .env file.")
    logging.basicConfig(level=logging.INFO)
    SocketModeHandler(build_app(bot_token), app_token).start()


if __name__ == "__main__":
    main()
