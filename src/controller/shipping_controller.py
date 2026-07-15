from src.model import order_model


class ShippingController:
    """출고 처리 (PRD §3.7)."""

    def __init__(self, conn, clock, view) -> None:
        self._conn = conn
        self._clock = clock
        self._view = view

    def run(self) -> None:
        while True:
            rows = order_model.list_orders_by_status(self._conn, "CONFIRMED")
            self._view.show_header("[6] 출고 처리")
            if not rows:
                self._view.show_message("출고 가능한 주문이 없습니다.")
            else:
                self._render(rows)
            self._view.show_menu([("1", "출고 처리"), ("0", "뒤로")])
            choice = self._view.prompt()
            if choice == "1":
                self._release()
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

    def _release(self) -> None:
        order_id = self._view.prompt("출고할 주문번호")
        try:
            order_model.release_order(self._conn, self._clock, order_id)
            order = order_model.get_order(self._conn, order_id)
            self._view.show_transition(order_id, "CONFIRMED", "RELEASE")
            self._view.show_message(
                f"출고 처리 완료.  출고수량 {order['quantity']} ea  처리일시 {order['released_at']}"
            )
        except (KeyError, ValueError) as exc:
            self._view.show_error(str(exc))
