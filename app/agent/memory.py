from typing import List, Dict, Optional, Any, Union
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
        # State for sequential add-on selection flow
        # addon_flow: { options: Dict[type, List[addon]], types: List[type], current_index: int }
        self.addon_flow: Optional[Dict[str, Any]] = None

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
    
    def record_addon_selection(self, addon_type: str, selection: Union[str, List[str]]) -> None:
        """Record the customer's selection for a given add-on type."""
        if not self.addon_flow:
            return
        # Normalize to list of strings
        selections_list = []
        if isinstance(selection, str):
            # Split on commas in case of multiple selections
            selections_list = [s.strip() for s in selection.split(",") if s.strip()]
        else:
            selections_list = list(selection)
        self.addon_flow["selections"][addon_type] = selections_list
    
    # Methods to manage sequential add-on selection
    def init_addon_flow(self, addon_options: Dict[str, list]) -> None:
        """Initialize the add-on selection flow with available options."""
        type_order = ["size", "sauce", "topping", "other"]
        # Only include types that have available options
        types = [t for t in type_order if t in addon_options and addon_options[t]]
        self.addon_flow = {
            "options": addon_options,
            "types": types,
            "current_index": 0,
            "selections": {},
        }

    def get_current_addon_type(self) -> Optional[str]:
        """Get the current add-on type to present next, or None if done."""
        if not self.addon_flow:
            return None
        idx = self.addon_flow.get("current_index", 0)
        types = self.addon_flow.get("types", [])
        if idx is None or idx < 0 or idx >= len(types):
            return None
        return types[idx]

    def advance_addon_flow(self) -> None:
        """Advance to the next add-on type in the flow."""
        if not self.addon_flow:
            return
        self.addon_flow["current_index"] = self.addon_flow.get("current_index", 0) + 1

    def is_addon_flow_complete(self) -> bool:
        """Return True if all add-on types have been presented."""
        if not self.addon_flow:
            return True
        idx = self.addon_flow.get("current_index", 0)
        types = self.addon_flow.get("types", [])
        return idx >= len(types)

    def get_addon_selections(self) -> Dict[str, list]:
        """Return the selections made during the add-on flow."""
        if not self.addon_flow:
            return {}
        return self.addon_flow.get("selections", {})
