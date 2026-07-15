from src.model import order_model, production_model, sample_model


class OrderController:
    """시료 주문 접수 (PRD §3.3)."""

    def __init__(self, conn, clock, view) -> None:
        self._conn = conn
        self._clock = clock
        self._view = view

    def run(self) -> None:
        while True:
            self._view.show_header("[2] 시료 주문")
            self._view.show_menu([("1", "주문 접수"), ("0", "뒤로")])
            choice = self._view.prompt()
            if choice == "1":
                self._reserve()
            elif choice == "0":
                return
            else:
                self._view.show_error("올바른 메뉴 번호를 입력하세요.")

    def _reserve(self) -> None:
        sample_id = self._view.prompt("시료 ID")
        if sample_model.get_sample(self._conn, sample_id) is None:
            self._view.show_error("존재하지 않는 시료입니다.")
            return
        customer_name = self._view.prompt("고객명")
        try:
            quantity = int(self._view.prompt("주문 수량"))
            order_id = order_model.create_order(
                self._conn, self._clock, sample_id, customer_name, quantity
            )
            self._view.show_message(f"예약 접수 완료. 주문번호 {order_id}")
        except ValueError as exc:
            self._view.show_error(str(exc))


class OrderApprovalController:
    """주문 승인/거절 (PRD §3.4)."""

    def __init__(self, conn, clock, view) -> None:
        self._conn = conn
        self._clock = clock
        self._view = view

    def run(self) -> None:
        while True:
            production_model.sync_queue(self._conn, self._clock)
            rows = order_model.list_orders_by_status(self._conn, "RESERVED")
            self._view.show_header("[3] 주문 승인/거절")
            if not rows:
                self._view.show_message("승인 대기 중인 주문이 없습니다.")
            else:
                self._render(rows)
            self._view.show_menu([("1", "승인"), ("2", "거절"), ("0", "뒤로")])
            choice = self._view.prompt()
            if choice == "1":
                self._approve()
            elif choice == "2":
                self._reject()
            elif choice == "0":
                return
            else:
                self._view.show_error("올바른 메뉴 번호를 입력하세요.")

    def _render(self, rows) -> None:
        columns = ["주문번호", "고객", "시료", "수량", "상태"]
        table_rows = [
            [r["order_id"], r["customer_name"], r["sample_id"], r["quantity"], r["status"]]
            for r in rows
        ]
        self._view.show_table(columns, table_rows, status_columns=frozenset({4}))

    def _approve(self) -> None:
        order_id = self._view.prompt("승인할 주문번호")
        try:
            new_status = order_model.approve_order(self._conn, self._clock, order_id)
            self._view.show_transition(order_id, "RESERVED", new_status)
            self._view.show_message("승인 완료.")
        except (KeyError, ValueError) as exc:
            self._view.show_error(str(exc))

    def _reject(self) -> None:
        order_id = self._view.prompt("거절할 주문번호")
        try:
            order_model.reject_order(self._conn, self._clock, order_id)
            self._view.show_transition(order_id, "RESERVED", "REJECTED")
        except (KeyError, ValueError) as exc:
            self._view.show_error(str(exc))
