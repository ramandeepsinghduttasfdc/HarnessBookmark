# Bookmark Agent

This folder contains a standalone terminal-based PydanticAI agent that uses:
- Model: `google:gemini-2.5-flash`
- Native tools (functions):
  - `list_chrome_bookmarks`
  - `list_chrome_bookmark_folders`
  - `create_chrome_bookmark`
- MCP tools via `mcp_server_fetch` for web search and page fetching

It reads and writes the configured Chrome profile bookmarks file.

## Folder Structure

- `app/main.py`: terminal chat entrypoint and agent wiring
- `core/chrome_bookmarks.py`: Chrome bookmark JSON helpers and safe write helpers
- `tools/bookmark_reader.py`: list/search bookmark tool
- `tools/bookmark_writer.py`: create bookmark tool
- `requirements.txt`: isolated dependencies for this folder
- `env.example`: required env var template

## Setup

1. Create and activate a Python virtual environment from this Repo folder
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Create `.env` from `env.example` and set `GOOGLE_API_KEY` & `CHROME_PROFILE_NAME`
4. Optional profile/path overrides:
  - `CHROME_PROFILE_NAME` (example: `Default`, `Profile 1`, `Profile 2`)
  - `CHROME_USER_DATA_DIR` (absolute path to Chrome user data directory)

## Run

```bash
python -m app.main
```

## Usage Examples

- "List my Chrome bookmarks"
- "List my bookmark folders"
- "Find bookmarks about AI"
- "Create a bookmark for https://example.com named Example in Bookmarks Bar / Work"
- "Search the web for latest Gemini API pricing"
- "Fetch and summarize https://pydantic.dev"

The agent is instructed to ask for confirmation before calling the create-bookmark tool.

## Safety Notes

- main.py contains clear list of Agent instructions or skills which define its actions. This provides a clear Guardrail for the Agent remain in its limits, and hence protect system exploitation. This acts a major security net for Agent behaviour.
- Writes continue even if Google Chrome is running. The tool returns a warning instead of blocking the operation.
- Why this was done: to avoid requiring users to close the browser during normal bookmark workflows.
- Risk: Chrome may overwrite or reorder bookmark changes while still running, so immediate consistency is not guaranteed.
- Bookmark creation requires a valid destination folder path. If folder is missing or invalid, the tool returns guidance and suggests listing available folder structures.
- On write, a timestamped backup is created before atomically replacing the bookmarks file.
- If `CHROME_PROFILE_NAME` is not specified in .env file, then "Default" will be automatically used
- Path resolution is OS-aware (macOS, Linux, Windows). Use `CHROME_USER_DATA_DIR` if your Chrome data is in a custom location.
- Another security net could be added using Pydantic AI's logfire feature. This helps to record each converation and technical to/fro, hence Agents behaviour and its scrutiny can be done. This is, however not done in this exercise but could be a useful feature.
Environment secrets are handled in .env file (environment file) which by design cannot get commited in git (.gitignore)
