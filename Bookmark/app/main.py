from __future__ import annotations

import sys

from dotenv import load_dotenv
from fastmcp.client.transports import StdioTransport
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPToolset

from tools.bookmark_reader import list_chrome_bookmark_folders, list_chrome_bookmarks
from tools.bookmark_writer import create_chrome_bookmark


load_dotenv()

fetch_server = MCPToolset(
    StdioTransport(command=sys.executable, args=["-m", "mcp_server_fetch"])
)

agent = Agent(
    "google:gemini-2.5-flash",
    instructions=(
        "You are a terminal assistant for bookmarks and web search. "
        "Use MCP fetch tools when the user asks for web search or web page content. "
        "Use list_chrome_bookmarks when the user asks to view/search bookmarks. "
        "Use list_chrome_bookmark_folders when user asks to see available bookmark folder structure. "
        "Before creating a bookmark, ask user which destination folder path should be used. "
        "If folder is missing or invalid, suggest using list_chrome_bookmark_folders and ask the user to pick one. "
        "Before creating a bookmark, ask for explicit confirmation in chat. "
        "Use create_chrome_bookmark only after user confirms. "
        "Do not require users to close Chrome before creating bookmarks; proceed and report any write warning. "
        "Summarize tool results clearly and briefly."
    ),
    toolsets=[fetch_server],
)

agent.tool_plain(list_chrome_bookmarks)
agent.tool_plain(list_chrome_bookmark_folders)
agent.tool_plain(create_chrome_bookmark)


async def main() -> None:
    print("Bookmark agent is ready. Type 'exit' or 'quit' to stop.")
    result = await agent.run(
        "Say hello and explain you can list bookmarks, list bookmark folders, create bookmarks (with required folder path), and do web search."
    )

    while True:
        print(f"\n{result.output}")
        user_input = input("\n> ").strip()

        if user_input.lower() in {"exit", "quit"}:
            print("Goodbye.")
            break

        result = await agent.run(
            user_input,
            message_history=result.new_messages(),
        )


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
