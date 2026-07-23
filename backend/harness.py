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

    def get_history(self,limit: int = 5,) -> str:
        if self.head is None:
            return "No previous actions."

        actions = []
        current = self.head

        while current is not None:
            actions.append(current.data)
            current = current.next

        recent_actions = actions[-limit:]

        lines = []

        for index, action in enumerate(
            recent_actions,
            start=1,
        ):
            result = action.result.replace(
                "\n",
                " ",
            )[:300]

            lines.append(
                f"{index}. {action.prev_action} "
                f"{action.prev_target} -> {result}"
            )

        return "\n".join(lines)