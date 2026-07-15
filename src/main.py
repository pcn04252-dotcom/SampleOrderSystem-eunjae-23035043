import sys

from src.controller.main_controller import MainController
from src.model.clock import ScaledSystemClock
from src.model.db import get_connection
from src.view.console_view import ConsoleView


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdin.reconfigure(encoding="utf-8")

    with get_connection() as conn:
        controller = MainController(conn, ScaledSystemClock(), ConsoleView())
        controller.run()


if __name__ == "__main__":
    main()
