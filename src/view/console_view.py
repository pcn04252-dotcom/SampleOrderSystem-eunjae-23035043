from typing import Iterable, Optional

from rich.console import Console
from rich.table import Table
from rich.text import Text

# PLAN.md 6장 색상 매핑 (주문 상태 + 재고 상태)
STATUS_COLORS = {
    "RESERVED": "cyan",
    "CONFIRMED": "green",
    "PRODUCING": "yellow",
    "REJECTED": "red",
    "RELEASE": "magenta",
    "여유": "green",
    "부족": "yellow",
    "고갈": "red",
}


class ConsoleView:
    def __init__(self) -> None:
        self.console = Console()

    def badge(self, status: str) -> Text:
        color = STATUS_COLORS.get(status, "white")
        return Text(f" {status} ", style=f"bold white on {color}")

    def show_header(self, title: str, timestamp: Optional[str] = None) -> None:
        self.console.rule(f"[bold]{title}[/bold]")
        if timestamp:
            self.console.print(timestamp, style="dim")

    def show_menu(self, options: Iterable[tuple[str, str]]) -> None:
        line = "  ".join(f"[{key}] {label}" for key, label in options)
        self.console.print(line)

    def prompt(self, label: str = "선택") -> str:
        return self.console.input(f"{label} > ").strip()

    def show_table(
        self,
        columns: list[str],
        rows: list[list],
        status_columns: frozenset = frozenset(),
    ) -> None:
        table = Table(show_header=True, header_style="bold")
        for col in columns:
            table.add_column(col)
        for row in rows:
            cells = []
            for i, value in enumerate(row):
                if i in status_columns:
                    cells.append(self.badge(str(value)))
                else:
                    cells.append(str(value))
            table.add_row(*cells)
        self.console.print(table)

    def show_message(self, message: str) -> None:
        self.console.print(message, style="bold green")

    def show_error(self, message: str) -> None:
        self.console.print(f"오류: {message}", style="bold red")

    def show_transition(self, order_id: str, before: str, after: str) -> None:
        self.console.print(
            f"상태 변경  {order_id}  ", self.badge(before), " → ", self.badge(after)
        )

    def show_progress_bar(self, percent: float, width: int = 20) -> None:
        filled = int(width * percent / 100)
        bar = "=" * filled + " " * (width - filled)
        self.console.print(f"[{bar}] {percent:.0f}%")
