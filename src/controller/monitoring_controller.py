from src.model import order_model, production_model, sample_model


class MonitoringController:
    """모니터링 (PRD §3.5)."""

    def __init__(self, conn, clock, view) -> None:
        self._conn = conn
        self._clock = clock
        self._view = view

    def run(self) -> None:
        while True:
            production_model.sync_queue(self._conn, self._clock)
            self._view.show_header(
                "[4] 모니터링", self._clock.now().isoformat(sep=" ", timespec="seconds")
            )
            self._view.show_menu([("1", "주문량 확인"), ("2", "재고량 확인"), ("0", "뒤로")])
            choice = self._view.prompt()
            if choice == "1":
                self._show_order_counts()
            elif choice == "2":
                self._show_stock_status()
            elif choice == "0":
                return
            else:
                self._view.show_error("올바른 메뉴 번호를 입력하세요.")

    def _show_order_counts(self) -> None:
        counts = order_model.count_orders_by_status(self._conn)
        columns = ["상태", "건수"]
        rows = [[status, count] for status, count in counts.items()]
        self._view.show_table(columns, rows, status_columns=frozenset({0}))

    def _show_stock_status(self) -> None:
        samples = sample_model.list_samples(self._conn)
        columns = ["시료명", "재고", "상태"]
        rows = []
        for sample in samples:
            status = sample_model.classify_stock_status(self._conn, sample["sample_id"])
            rows.append([sample["name"], sample["current_stock"], status])
        self._view.show_table(columns, rows, status_columns=frozenset({2}))
