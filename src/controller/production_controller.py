from src.model import production_model


class ProductionController:
    """생산 라인 조회 (PRD §3.6)."""

    def __init__(self, conn, clock, view) -> None:
        self._conn = conn
        self._clock = clock
        self._view = view

    def run(self) -> None:
        production_model.sync_queue(self._conn, self._clock)
        self._view.show_header("[5] 생산 라인")

        running = production_model.get_running_job(self._conn)
        if running is None:
            self._view.show_message("현재 생산 중인 작업이 없습니다.")
        else:
            self._render_running(running)

        waiting = production_model.list_waiting_jobs(self._conn)
        if waiting:
            self._render_waiting(waiting)

        self._view.show_menu([("0", "뒤로")])
        self._view.prompt()

    def _render_running(self, job) -> None:
        percent = production_model.progress_percent(job, self._clock)
        self._view.show_message(
            f"주문번호 {job['order_id']}  시료 {job['sample_id']}"
            f"  실생산량 {job['actual_production_quantity']} ea"
        )
        self._view.show_progress_bar(percent)

    def _render_waiting(self, rows) -> None:
        columns = ["순서", "주문번호", "시료", "부족분", "실생산량"]
        table_rows = [
            [
                i + 1,
                r["order_id"],
                r["sample_id"],
                r["shortfall_quantity"],
                r["actual_production_quantity"],
            ]
            for i, r in enumerate(rows)
        ]
        self._view.show_table(columns, table_rows)
