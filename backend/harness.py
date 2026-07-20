from dataclasses import dataclass
from typing import Optional


@dataclass
class ActionResult:
    prev_action: str
    prev_target: str
    result: str


@dataclass
class ActionNode:
    data: ActionResult
    next: Optional["ActionNode"] = None


class Harness:
    def __init__(self):
        self.head: Optional[ActionNode] = None
        self.tail: Optional[ActionNode] = None
        self.size = 0

    def add_action_result(self, action_result: ActionResult) -> None:
        new_node = ActionNode(data=action_result)

        if self.head is None:
            self.head = new_node
            self.tail = new_node
        else:
            self.tail.next = new_node
            self.tail = new_node

        self.size += 1

    def action_to_text(self, action_node: ActionNode) -> str:
        return (
            f"Previous Action: {action_node.data.prev_action}\n"
            f"Previous Target: {action_node.data.prev_target}\n"
            f"Result: {action_node.data.result}\n"
        )

    def get_history(self) -> str:
        if self.head is None:
            return "No action taken yet."

        history = ""
        current = self.head
        index = 1

        while current is not None:
            history += (
                f"\nAction {index}:\n"
                f"{self.action_to_text(current)}"
            )

            current = current.next
            index += 1

        return history