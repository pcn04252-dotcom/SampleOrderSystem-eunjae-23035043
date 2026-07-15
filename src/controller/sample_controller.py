import sqlite3

from src.model import sample_model


class SampleController:
    def __init__(self, conn, clock, view) -> None:
        self._conn = conn
        self._clock = clock
        self._view = view

    def run(self) -> None:
        while True:
            self._view.show_header("[1] 시료 관리")
            self._view.show_menu(
                [("1", "시료 등록"), ("2", "시료 목록"), ("3", "시료 검색"), ("0", "뒤로")]
            )
            choice = self._view.prompt()
            if choice == "1":
                self._register()
            elif choice == "2":
                self._list()
            elif choice == "3":
                self._search()
            elif choice == "0":
                return
            else:
                self._view.show_error("올바른 메뉴 번호를 입력하세요.")

    def _register(self) -> None:
        sample_id = self._view.prompt("시료 ID")
        name = self._view.prompt("이름")
        try:
            avg_time = float(self._view.prompt("평균 생산시간(분)"))
            yield_rate = float(self._view.prompt("수율(0~1)"))
            sample_model.create_sample(self._conn, sample_id, name, avg_time, yield_rate)
            self._view.show_message(f"시료 {sample_id} 등록 완료.")
        except (ValueError, sqlite3.IntegrityError) as exc:
            self._view.show_error(str(exc))

    def _list(self) -> None:
        self._render(sample_model.list_samples(self._conn))

    def _search(self) -> None:
        keyword = self._view.prompt("검색어")
        self._render(sample_model.search_samples(self._conn, keyword))

    def _render(self, rows) -> None:
        columns = ["ID", "이름", "평균 생산시간", "수율", "현재 재고"]
        table_rows = [
            [r["sample_id"], r["name"], r["avg_production_time"], r["yield_rate"], r["current_stock"]]
            for r in rows
        ]
        self._view.show_table(columns, table_rows)
