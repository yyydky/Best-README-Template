from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import uuid


@dataclass
class Workbook:
    workbook_id: str
    name: str
    portfolio: Optional[Dict[str, Any]] = None
    sections: List[Dict[str, Any]] = field(default_factory=list)
    charts: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workbook_id": self.workbook_id,
            "name": self.name,
            "portfolio": self.portfolio,
            "sections": list(self.sections),
            "charts": list(self.charts),
        }


@dataclass
class WorkbookState:
    workbooks: Dict[str, Workbook] = field(default_factory=dict)
    current_workbook_id: Optional[str] = None

    def create_workbook(self, name: str) -> Workbook:
        workbook_id = str(uuid.uuid4())
        workbook = Workbook(workbook_id=workbook_id, name=name)
        self.workbooks[workbook_id] = workbook
        self.current_workbook_id = workbook_id
        return workbook

    def open_workbook(self, workbook_id: str) -> Optional[Workbook]:
        if workbook_id in self.workbooks:
            self.current_workbook_id = workbook_id
            return self.workbooks[workbook_id]
        return None

    def get_current(self) -> Optional[Workbook]:
        if not self.current_workbook_id:
            return None
        return self.workbooks.get(self.current_workbook_id)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_workbook_id": self.current_workbook_id,
            "workbooks": {
                workbook_id: workbook.to_dict()
                for workbook_id, workbook in self.workbooks.items()
            },
        }


STATE = WorkbookState()
