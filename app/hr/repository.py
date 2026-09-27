import json
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4


@dataclass(frozen=True)
class Employee:
    user_id: str
    name: str
    department: str
    vacation_balance: int


@dataclass(frozen=True)
class HrRequest:
    request_id: str
    user_id: str
    request_type: str
    details: str
    status: str


class EmployeeNotFoundError(KeyError):
    pass


class HrRepository:
    def __init__(self, employees: list[Employee]) -> None:
        self._employees = {item.user_id: item for item in employees}
        self._requests: list[HrRequest] = []

    @classmethod
    def from_json(cls, path: Path) -> "HrRepository":
        raw = json.loads(path.read_text(encoding="utf-8"))
        employees = [Employee(**row) for row in raw]
        return cls(employees)

    def get_employee(self, user_id: str) -> Employee:
        try:
            return self._employees[user_id]
        except KeyError as exc:
            raise EmployeeNotFoundError(user_id) from exc

    def get_vacation_balance(self, user_id: str) -> int:
        return self.get_employee(user_id).vacation_balance

    def create_request(self, user_id: str, request_type: str, details: str) -> HrRequest:
        self.get_employee(user_id)
        record = HrRequest(
            request_id=str(uuid4()),
            user_id=user_id,
            request_type=request_type,
            details=details,
            status="submitted",
        )
        self._requests.append(record)
        return record
