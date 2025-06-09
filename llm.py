from typing import List, Dict, Any, cast
from langchain_openai import ChatOpenAI
from systemd import get_unit_status, get_journal_logs, list_failed_units, get_unit_dependencies
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage

llm = ChatOpenAI(model="gpt-4.1-mini")
tools = [get_unit_status, get_journal_logs, list_failed_units, get_unit_dependencies]
llm_with_tools = llm.bind_tools(tools)
tool_map: Dict[str, Any] = {tool.name: tool for tool in tools}

async def process_chat(messages: List[BaseMessage]) -> BaseMessage:
    """
    Processes a list of messages, handles tool calls iteratively, and returns the final LLM response.
    Continues calling tools until the LLM response contains no more tool calls (reaches fixpoint).
    """
    current_messages = messages[:]
    max_iterations = 10  # Prevent infinite loops
    iteration = 0
    ai_response = None

    while iteration < max_iterations:
        # Invoke the LLM with current messages
        ai_response = cast(AIMessage, await llm_with_tools.ainvoke(current_messages))

        # If no tool calls, we've reached the fixpoint
        if not ai_response.tool_calls:
            return ai_response

        # Process tool calls
        print(f"\nTool Calls (iteration {iteration + 1}):")
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
            else:
                # Handle the case where the tool is not found
                error_message = f"Tool '{tool_call['name']}' not found in available tools"
                tool_messages.append(
                    ToolMessage(
                        content=error_message,
                        tool_call_id=tool_call["id"]
                    )
                )

        # Add the AI response and tool messages to the conversation history
        current_messages.extend([ai_response] + tool_messages)
        iteration += 1

    # If we reach max iterations, return the last AI response (which might still have tool calls)
    print(f"\nWarning: Reached maximum iterations ({max_iterations}). Final response may contain unexecuted tool calls.")
    # ai_response should always be defined here since we enter the loop at least once
    assert ai_response is not None, "ai_response should be defined after at least one iteration"
    return ai_response