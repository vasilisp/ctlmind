import asyncio
from typing import List
from llm import process_chat
from langchain_core.messages import BaseMessage, HumanMessage

async def main() -> None:
    print("Welcome to the systemd-enabled LLM chat. Type 'exit' or 'quit' to end.")
    chat_history: List[BaseMessage] = []
    while True:
        try:
            prompt = input("> ")
            if prompt.lower() in ["exit", "quit"]:
                print("Exiting chat. Goodbye!")
                break

            chat_history.append(HumanMessage(content=prompt))

            ai_response = await process_chat(chat_history)

            chat_history.append(ai_response)

            print(f"LLM: {ai_response.content}\n")

        except (KeyboardInterrupt, EOFError):
            print("\nExiting chat. Goodbye!")
            break

if __name__ == "__main__":
    asyncio.run(main())
