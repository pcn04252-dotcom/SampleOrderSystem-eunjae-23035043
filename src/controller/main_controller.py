from src.controller.monitoring_controller import MonitoringController
from src.controller.order_controller import OrderApprovalController, OrderController
from src.controller.production_controller import ProductionController
from src.controller.sample_controller import SampleController
from src.controller.shipping_controller import ShippingController
from src.model import order_model, production_model, sample_model


class MainController:
    """메인 메뉴 (PRD §3.1)."""

    def __init__(self, conn, clock, view) -> None:
        self._conn = conn
        self._clock = clock
        self._view = view

    def run(self) -> None:
        while True:
            production_model.sync_queue(self._conn, self._clock)
            self._show_summary()
            self._view.show_menu(
                [
                    ("1", "시료 관리"),
                    ("2", "시료 주문"),
                    ("3", "주문 승인/거절"),
                    ("4", "모니터링"),
                    ("5", "생산라인 조회"),
                    ("6", "출고 처리"),
                    ("0", "종료"),
                ]
            )
            choice = self._view.prompt()
            if choice == "1":
                SampleController(self._conn, self._clock, self._view).run()
            elif choice == "2":
                OrderController(self._conn, self._clock, self._view).run()
            elif choice == "3":
                OrderApprovalController(self._conn, self._clock, self._view).run()
            elif choice == "4":
                MonitoringController(self._conn, self._clock, self._view).run()
            elif choice == "5":
                ProductionController(self._conn, self._clock, self._view).run()
            elif choice == "6":
                ShippingController(self._conn, self._clock, self._view).run()
            elif choice == "0":
                return
            else:
                self._view.show_error("올바른 메뉴 번호를 입력하세요.")

    def _show_summary(self) -> None:
        samples = sample_model.list_samples(self._conn)
        orders = order_model.list_orders(self._conn)
        waiting = production_model.count_waiting(self._conn)
        total_stock = sum(s["current_stock"] for s in samples)
        self._view.show_header(
            "반도체 시료 생산주문관리 시스템",
            self._clock.now().isoformat(sep=" ", timespec="seconds"),
        )
        self._view.show_message(
            f"등록 시료 {len(samples)}종   총 재고 {total_stock} ea"
            f"   전체 주문 {len(orders)}건   생산라인 {waiting}건 대기"
        )
