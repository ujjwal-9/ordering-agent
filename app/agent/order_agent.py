from openai import AsyncOpenAI
import os
import json
import logging
from munch import Munch
from typing import List, Tuple, Optional, Dict
from ..custom_types import (
    ResponseRequiredRequest,
    ResponseResponse,
    Utterance,
)
from ..db_operations.database import Database
from .memory import ConversationBufferMemory
from .prompts import BEGIN_SENTENCE, AGENT_PROMPT
from .handler import ToolHandler
from .tools import prepare_tools

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("agent.log"), logging.StreamHandler()],
)
logger = logging.getLogger("conversation_agent")


class OrderAgent:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=os.environ["OPENAI_API_KEY"],
        )
        self.db = Database()
        self.from_number = None  # Store the caller's phone number from the request
        self.memory = ConversationBufferMemory()  # Initialize conversation memory
        self.tool_handler = ToolHandler(self.db, self.memory)

    def set_from_number(self, from_number):
        """Set the caller's phone number from the call request"""
        self.from_number = from_number
        self.memory.update_customer_info(phone=from_number)
        logger.info(f"Set from_number: {self.from_number}")

    def draft_begin_message(self):
        self.memory.add_message("assistant", BEGIN_SENTENCE)

        response = ResponseResponse(
            response_id=0,
            content=BEGIN_SENTENCE,
            content_complete=True,
            end_call=False,
        )
        return response

    def convert_transcript_to_openai_messages(self, transcript: List[Utterance]):
        messages = []
        print("********************* TRANSCRIPT *********************")
        print(transcript)
        print("***************************************************************")
        for utterance in transcript:
            if utterance.role == "agent":
                messages.append({"role": "assistant", "content": utterance.content})
                self.memory.add_message("assistant", utterance.content)
            else:
                messages.append({"role": "user", "content": utterance.content})
                self.memory.add_message("user", utterance.content)
        return messages

    def remove_tool_calls(self):
        sanitized_memory = []
        for message in self.memory.get_conversation_history():
            if message.get("tool_calls"):
                continue
            elif message.get("tool_call_id"):
                sanitized_memory.append(
                    {
                        "role": "assistant",
                        "content": message["content"],
                    }
                )
            else:
                sanitized_memory.append(message)
        return sanitized_memory

    def prepare_prompt(self, request: ResponseRequiredRequest):
        # Add from_number information to the prompt if we have it
        current_prompt = self.base_prompt(request)
        return current_prompt

    def base_prompt(self, request: ResponseRequiredRequest):
        prompt = [
            {
                "role": "system",
                "content": AGENT_PROMPT,
            }
        ]

        if self.memory.get_conversation_history():
            sanitized_memory = self.remove_tool_calls()
            prompt.extend(sanitized_memory)

        transcript_messages = self.convert_transcript_to_openai_messages(
            request.transcript
        )
        prompt.extend(transcript_messages)

        if request.interaction_type == "reminder_required":
            prompt.append(
                {
                    "role": "user",
                    "content": "(Now the user has not responded in a while, you would say:)",
                }
            )
        return prompt

    def prepare_tools(self):
        """Prepare the function definitions for the OpenAI API, filtering out verify_order_item after an item is confirmed."""
        tools = prepare_tools()
        # If the customer has already confirmed an item, no need to re-verify it
        if getattr(self.memory, "item_confirmed", False):
            tools = [
                fn for fn in tools if fn["function"]["name"] != "verify_order_item"
            ]
        return tools

    async def draft_response(self, request: ResponseRequiredRequest):
        prompt = self.prepare_prompt(request)
        func_call = {}

        # Continue with normal OpenAI flow
        print("********************* MAIN PROMPT *********************")
        print(prompt)
        print("***************************************************************")
        response = await self.client.chat.completions.create(
            model=os.environ["OPENAI_MODEL"],
            messages=prompt,
            tools=self.prepare_tools(),
        )

        tool_calls = response.choices[0].message.tool_calls
        if tool_calls:
            tool_call = tool_calls[0]
            if tool_call.id:
                func_call = {
                    "id": tool_call.id,
                    "func_name": tool_call.function.name or "",
                    "arguments": tool_call.function.arguments or {},
                }
            logger.info(f"OpenAI tool call: {func_call['func_name']}")
            logger.info(f"OpenAI tool call arguments: {func_call['arguments']}")
        else:
            response_content = response.choices[0].message.content
            logger.info(f"OpenAI response: {response_content}")
            # Add the complete response to memory
            if response_content:
                self.memory.add_message("assistant", response_content)

            yield ResponseResponse(
                response_id=request.response_id,
                content=response_content or "",
                content_complete=True,
                end_call=False,
            )

        logger.info(f"Memory: {self.memory.get_conversation_history()}")

        if func_call:
            tool_call_message = Munch(
                response.choices[0].message.tool_calls[0]
            ).toDict()
            tool_call_message["function"] = Munch(
                tool_call_message["function"]
            ).toDict()
            logger.info(f"Function call: {tool_call_message}")
            self.memory.add_message(
                "assistant",
                response.choices[0].message.content,
                [tool_call_message],
            )

            # Process function calls
            func_call["arguments"] = json.loads(func_call["arguments"])
            logger.info(
                f"Processing function call: {func_call['func_name']} with arguments: {func_call['arguments']}"
            )

            # Use the handler class to process function calls
            async for response in self.tool_handler.process_function_call(
                tool_call=func_call,
                response_id=request.response_id,
                from_number=self.from_number,
                memory=self.memory,
            ):
                # Update memory if there's content
                if response.content:
                    logger.info(
                        f"Function response added to memory: {response.content}"
                    )

                # Update verified_customer if this was a verify_customer call
                if (
                    func_call["func_name"] == "verify_customer"
                    and "exists" in response.content
                ) or (func_call["func_name"] == "create_customer"):
                    self.memory.verified_customer = True
                    logger.info(f"Customer verified: {self.memory.verified_customer}")

                yield response
        else:
            yield ResponseResponse(
                response_id=request.response_id,
                content="",
                content_complete=True,
                end_call=False,
            )
