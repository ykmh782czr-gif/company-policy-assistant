# Slack bot

Use a separate workspace named **Sara Cairati — Company Policy Assistant** and a channel named **sara-cairati-policy-testing**.

1. Create an app at https://api.slack.com/apps using `slack_app_manifest.json` in that workspace.
2. Generate an app-level token with `connections:write` under Basic Information.
3. Install the app in the workspace and obtain its Bot User OAuth Token.
4. Keep the tokens only in your local `.env` alongside the existing Gemini key:

```text
GEMINI_API_KEY=your-existing-key
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token
```

5. Install and run locally:

```bash
python -m pip install -r requirements-slack.txt
python slack_bot.py
```

6. Add Sara Policy Assistant to the testing channel. Call it with `@Sara Policy Assistant What should I wear to work?` and expand its thread to see the policy title and answer. Also test an unsupported question, such as overnight sleeping at the office.
7. Invite the instructor to the workspace/channel and capture a screenshot showing the channel name, question, and bot answer. Keep this process running while testing; permanent hosting is unnecessary.

The bot uses the same full-policy LLM function as the comparison. It handles generation failures without inventing an answer, verifies returned policy titles, and uses Slack Socket Mode so no public local server is needed. It reads only direct app mentions in channels it belongs to and posts replies in threads.

Never upload `.env` or tokens to GitHub or Streamlit. The Streamlit website uses saved results and does not need Slack credentials.
