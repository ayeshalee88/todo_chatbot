"""
OpenAI Agent Configuration for Todo AI Chatbot
Configures the agent with MCP tools and proper system instructions
"""
import os
from typing import Dict, Any, List
from openai import OpenAI
import json
import requests
from models.conversation_models import MessageCreate, Message


class TodoAgent:
    def __init__(self):
        # Initialize OpenAI client
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # Define system instructions
        self.system_instructions = """
        You are a helpful todo list assistant. You can help users manage their tasks using the provided tools.
        When a user wants to:
        - Add a task: Use the add_task tool with title and description
        - See their tasks: Use the list_tasks tool
        - Update a task: Use the update_task tool with task_id and new details
        - Mark a task complete: Use the complete_task tool with task_id
        - Delete a task: Use the delete_task tool with task_id

        Always provide clear, natural language responses to the user and confirm when actions have been taken.
        """

        # Define available tools for the agent
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "add_task",
                    "description": "Add a new task to the user's list",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Task title"},
                            "description": {"type": "string", "description": "Task description"},
                            "user_id": {"type": "string", "description": "User ID"}
                        },
                        "required": ["title", "user_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_tasks",
                    "description": "Get all tasks for the user",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user_id": {"type": "string", "description": "User ID"}
                        },
                        "required": ["user_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "update_task",
                    "description": "Update an existing task",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task_id": {"type": "string", "description": "ID of the task to update"},
                            "user_id": {"type": "string", "description": "User ID"},
                            "title": {"type": "string", "description": "New task title"},
                            "description": {"type": "string", "description": "New task description"}
                        },
                        "required": ["task_id", "user_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "complete_task",
                    "description": "Mark a task as complete or incomplete",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task_id": {"type": "string", "description": "ID of the task to update"},
                            "user_id": {"type": "string", "description": "User ID"},
                            "completed": {"type": "boolean", "description": "Whether the task is completed"}
                        },
                        "required": ["task_id", "user_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_task",
                    "description": "Delete a task",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task_id": {"type": "string", "description": "ID of the task to delete"},
                            "user_id": {"type": "string", "description": "User ID"}
                        },
                        "required": ["task_id", "user_id"]
                    }
                }
            }
        ]

        # Base URL for MCP server
        self.mcp_base_url = os.getenv("MCP_SERVER_URL", "http://localhost:8001")

    def call_mcp_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call an MCP tool via HTTP request"""
        url = f"{self.mcp_base_url}/tools/{tool_name}"

        # Prepare the query parameters
        query_params = []
        for key, value in params.items():
            if isinstance(value, bool):
                query_params.append(f"{key}={str(value).lower()}")
            else:
                query_params.append(f"{key}={value}")

        full_url = f"{url}?{'&'.join(query_params)}"

        try:
            response = requests.post(full_url)
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    def process_message(self, user_message: str, user_id: str, conversation_history: List[Dict[str, str]]) -> str:
        """Process a user message and return agent response"""
        # Prepare the messages for the OpenAI API
        messages = [{"role": "system", "content": self.system_instructions}]

        # Add conversation history
        for msg in conversation_history:
            messages.append({"role": msg["role"], "content": msg["content"]})

        # Add the current user message
        messages.append({"role": "user", "content": user_message})

        # Call OpenAI with tools
        response = self.client.chat.completions.create(
            model="gpt-4-turbo",  # or gpt-3.5-turbo
            messages=messages,
            tools=self.tools,
            tool_choice="auto"
        )

        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls

        # If the model wants to call tools
        if tool_calls:
            # Send the info for each function call and function response to the model
            messages.append(response_message)  # Add original response

            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)

                # Add user_id to function arguments if not present
                if "user_id" not in function_args:
                    function_args["user_id"] = user_id

                # Call the MCP tool
                tool_response = self.call_mcp_tool(function_name, function_args)

                # Add tool response to messages
                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": json.dumps(tool_response),
                })

            # Get final response from the model with tool results
            final_response = self.client.chat.completions.create(
                model="gpt-4-turbo",
                messages=messages,
            )
            return final_response.choices[0].message.content
        else:
            # If no tools were called, return the model's response directly
            return response_message.content


# Example usage
if __name__ == "__main__":
    # Example - won't run without API key
    pass