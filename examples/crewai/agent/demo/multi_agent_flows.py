"""
A demo of predictive state updates.
"""

import json
import os
from typing import Optional
from litellm import completion
from crewai.flow.flow import Flow, start, router, listen
from tavily import TavilyClient
from copilotkit.crewai import (
  copilotkit_stream, 
  copilotkit_predict_state,
  CopilotKitState
)

WRITE_DOCUMENT_TOOL = {
    "type": "function",
    "function": {
        "name": "write_document",
        "description": " ".join("""Write a document. Always write the full document, 
                                even when changing only a few words.""".split()),
        "parameters": {
            "type": "object",
            "properties": {
                "document": {
                    "type": "string",
                    "description": "The document to write"
                },
            },
        }
    }
}

SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "search_web",
        "description": "Search the web for information relevant to the document.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query",
                },
            },
            "required": ["query"],
        },
    },
}


class AgentState(CopilotKitState):
    """
    The state of the agent.
    """
    document: Optional[str] = None

class MultiAgentWriterFlow(Flow[AgentState]):
    """
    This is a sample flow that writes documents in a multi-agent workflow.
    """

    @start()
    @listen("route_follow_up")
    async def start_flow(self):
        """
        This is the entry point for the flow.
        """

    @router(start_flow)
    async def chat(self):
        """
        Standard chat node.
        """
        system_prompt = f"You are a helpful assistant for writing documents. This is the current state of the document: ----\n {self.state.document}\n-----"

        await copilotkit_predict_state({
            "document": {
                "tool": "write_document",
                "tool_argument": "document"
            }
        })

        response = await copilotkit_stream(
            completion(
                model="openai/gpt-4o",
                messages=[
                    {
                        "role": "system", 
                        "content": system_prompt
                    },
                    *self.state.messages
                ],
                tools=[
                    *self.state.copilotkit.actions,
                    WRITE_DOCUMENT_TOOL
                ],
                parallel_tool_calls=False,
                stream=True
            )
        )

        message = response.choices[0].message

        self.state.messages.append(message)

        if message.get("tool_calls"):
            tool_call = message["tool_calls"][0]
            tool_call_id = tool_call["id"]
            tool_call_name = tool_call["function"]["name"]
            tool_call_args = json.loads(tool_call["function"]["arguments"])

            if tool_call_name == "write_document":
                self.state.document = tool_call_args["document"]

                self.state.messages.append({
                    "role": "tool",
                    "content": "Document written.",
                    "tool_call_id": tool_call_id
                })
                return "route_follow_up"

        return "route_end"

    @listen("route_end")
    async def end(self):
        """
        End the flow.
        """

class MultiAgentCriticFlow(Flow[AgentState]):
    """
    This is a sample flow that criticizes documents in a multi-agent workflow.
    """

    @start()
    @listen("route_follow_up")
    async def start_flow(self):
        """
        This is the entry point for the flow.
        """

    @router(start_flow)
    async def chat(self):
        """
        Standard chat node.
        """
        system_prompt = f"You are a helpful assistant for criticizing documents. You can provide feedback on the document, and suggest improvements. You can also update the document. This is the current state of the document: ----\n {self.state.document}\n-----"

        await copilotkit_predict_state({
            "document": {
                "tool": "write_document",
                "tool_argument": "document"
            }
        })

        response = await copilotkit_stream(
            completion(
                model="openai/gpt-4o",
                messages=[
                    {
                        "role": "system", 
                        "content": system_prompt
                    },
                    *self.state.messages
                ],
                tools=[
                    *self.state.copilotkit.actions,
                    WRITE_DOCUMENT_TOOL
                ],
                parallel_tool_calls=False,
                stream=True
            )
        )

        message = response.choices[0].message

        self.state.messages.append(message)

        if message.get("tool_calls"):
            tool_call = message["tool_calls"][0]
            tool_call_id = tool_call["id"]
            tool_call_name = tool_call["function"]["name"]
            tool_call_args = json.loads(tool_call["function"]["arguments"])

            if tool_call_name == "write_document":
                self.state.document = tool_call_args["document"]

                self.state.messages.append({
                    "role": "tool",
                    "content": "Document written.",
                    "tool_call_id": tool_call_id
                })
                return "route_follow_up"

        return "route_end"

    @listen("route_end")
    async def end(self):
        """
        End the flow.
        """

class MultiAgentResearcherFlow(Flow[AgentState]):
    """
    This is a sample flow that researches content for documents in a multi-agent workflow.
    """

    @start()
    @listen("route_follow_up")
    async def start_flow(self):
        """
        This is the entry point for the flow.
        """

    @router(start_flow)
    async def chat(self):
        """
        Standard chat node.
        """
        system_prompt = f"You are a helpful assistant for researching content for documents. You can find new sources by searching the web, and suggest how to incorporate them into the document. You can also update the document. This is the current state of the document: ----\n {self.state.document}\n-----"

        await copilotkit_predict_state({
            "document": {
                "tool": "write_document",
                "tool_argument": "document"
            }
        })

        response = await copilotkit_stream(
            completion(
                model="openai/gpt-4o",
                messages=[
                    {
                        "role": "system", 
                        "content": system_prompt
                    },
                    *self.state.messages
                ],
                tools=[
                    *self.state.copilotkit.actions,
                    WRITE_DOCUMENT_TOOL,
                    SEARCH_TOOL
                ],
                parallel_tool_calls=False,
                stream=True
            )
        )

        message = response.choices[0].message

        self.state.messages.append(message)

        if message.get("tool_calls"):
            tool_call = message["tool_calls"][0]
            tool_call_id = tool_call["id"]
            tool_call_name = tool_call["function"]["name"]
            tool_call_args = json.loads(tool_call["function"]["arguments"])

            if tool_call_name == "write_document":
                self.state.document = tool_call_args["document"]

                self.state.messages.append({
                    "role": "tool",
                    "content": "Document written.",
                    "tool_call_id": tool_call_id
                })
                return "route_follow_up"
            elif tool_call_name == "search_web":
                if not os.getenv("TAVILY_API_KEY"):
                    self.state.messages.append({
                        "role": "tool",
                        "content": "No API key found for Tavily.",
                        "tool_call_id": tool_call_id
                    })
                    return "route_follow_up"
                tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
                response = tavily_client.search(tool_call_args["query"])
                self.state.messages.append({
                    "role": "tool",
                    "content": f"Web search completed. Here are the results: {response}",
                    "tool_call_id": tool_call_id
                })
                return "route_follow_up"

        return "route_end"

    @listen("route_end")
    async def end(self):
        """
        End the flow.
        """
