from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Message:
    role: str  # 'user' or 'assistant'
    content: str
    tool_calls: Optional[Dict[str, Any]] = None
    tool_call_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


class ConversationBufferMemory:
    def __init__(self):
        self.messages: List[Message] = []
        self.customer_info: Dict[str, str] = {
            "name": None,
            "phone": None,
            "email": None,
        }
        self.current_order: Dict[str, any] = {"items": [], "total": 0.0, "status": None}
        self.verified_customer: bool = False
        self.order_confirmed: bool = False
        self.last_interaction_time: datetime = datetime.now()
        self.tool_chain: List[str] = []

    def add_message(
        self,
        role: str,
        content: str,
        tool_calls: Optional[Dict[str, Any]] = None,
        tool_call_id: Optional[str] = None,
    ) -> None:
        """Add a new message to the conversation history."""
        self.messages.append(
            Message(
                role=role,
                content=content,
                tool_calls=tool_calls,
                tool_call_id=tool_call_id,
            )
        )
        self.last_interaction_time = datetime.now()

    def get_conversation_history(self, k: Optional[int] = None) -> List[Dict[str, str]]:
        """Get the last k messages from conversation history."""
        history = [
            {
                "role": msg.role,
                "content": msg.content,
                "tool_calls": msg.tool_calls,
                "tool_call_id": msg.tool_call_id,
            }
            for msg in self.messages
        ]
        if k is not None:
            history = history[-k:]
        return history

    def clear(self) -> None:
        """Clear the conversation history."""
        self.messages = []
        self.current_order = {"items": [], "total": 0.0, "status": None}
        self.last_interaction_time = datetime.now()

    def update_customer_info(self, **kwargs) -> None:
        """Update customer information."""
        for key, value in kwargs.items():
            if key in self.customer_info:
                self.customer_info[key] = value

    def add_order_item(self, item: Dict[str, any]) -> None:
        """Add an item to the current order."""
        self.current_order["items"].append(item)

    def update_order_total(self, total: float) -> None:
        """Update the current order total."""
        self.current_order["total"] = total

    def update_order_status(self, status: str) -> None:
        """Update the current order status."""
        self.current_order["status"] = status

    def get_last_user_message(self) -> Optional[str]:
        """Get the last message from the user."""
        for msg in reversed(self.messages):
            if msg.role == "user":
                return msg.content
        return None

    def get_last_assistant_message(self) -> Optional[str]:
        """Get the last message from the assistant."""
        for msg in reversed(self.messages):
            if msg.role == "assistant":
                return msg.content
        return None

    def get_time_since_last_interaction(self) -> float:
        """Get the time elapsed since the last interaction in seconds."""
        return (datetime.now() - self.last_interaction_time).total_seconds()

    def get_context_summary(self) -> Dict[str, any]:
        """Get a summary of the current conversation context."""
        return {
            "customer_info": self.customer_info,
            "current_order": self.current_order,
            "verified_customer": self.verified_customer,
            "order_confirmed": self.order_confirmed,
            "message_count": len(self.messages),
        }

    def set_verified_customer(self, verified: bool):
        """Set whether the customer has been verified."""
        self.verified_customer = verified

    def set_order_confirmed(self, confirmed: bool):
        """Set whether the order has been confirmed."""
        self.order_confirmed = confirmed

    def get_last_n_messages(self, n: int) -> List[Dict[str, str]]:
        """Get the last n messages from the conversation history."""
        return self.messages[-n:] if n > 0 else []

    def get_nth_messages(self, n: int):
        """Get the nth message from the conversation history."""
        return self.messages[n]

    def get_memory_size(self) -> int:
        """Get the size of the memory."""
        return len(self.messages)
