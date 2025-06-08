from typing import List, Dict, Any, cast
from langchain_openai import ChatOpenAI
from systemd import get_unit_status, get_journal_logs, list_failed_units
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage

llm = ChatOpenAI(model="gpt-4.1-mini")
tools = [get_unit_status, get_journal_logs, list_failed_units]
llm_with_tools = llm.bind_tools(tools)
tool_map: Dict[str, Any] = {tool.name: tool for tool in tools}

async def process_chat(messages: List[BaseMessage]) -> BaseMessage:
    """
    Processes a list of messages, handles tool calls, and returns the final LLM response.
    """
    # First invocation to see if the model wants to call a tool
    ai_response = cast(AIMessage, await llm_with_tools.ainvoke(messages))

    # If the model response contains tool calls, execute them
    if ai_response.tool_calls:
        print("\nTool Calls:")
        for tool_call in ai_response.tool_calls:
            print(f"  - {tool_call['name']}({tool_call['args']})")
        tool_messages: List[ToolMessage] = []
        for tool_call in ai_response.tool_calls:
            tool_to_call = tool_map.get(tool_call["name"])
            if tool_to_call:
                # The tool is async, so we await its invocation
                tool_output = await tool_to_call.ainvoke(tool_call["args"])
                # Append the result as a ToolMessage
                tool_messages.append(
                    ToolMessage(
                        content=str(tool_output),
                        tool_call_id=tool_call["id"]
                    )
                )
        # Second invocation with the tool results
        # We add the original AI response and the new tool messages to the history
        final_response = cast(AIMessage, await llm_with_tools.ainvoke(messages + [ai_response] + tool_messages))
    else:
        # If there are no tool calls, the first response is the final one
        final_response = ai_response

    return final_response