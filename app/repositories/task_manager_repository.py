from sqlalchemy.orm import Session
from sqlalchemy import select
from ..models import TaskManagerModel
from .repository import Repository

class TaskManagerRepository(Repository):
    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def add(self, instance: TaskManagerModel) -> TaskManagerModel:
        self.session.add(instance)
        self.session.commit()
        self.session.refresh(instance)
        return instance
    
    def add_many(self, instances: list[TaskManagerModel]) -> list[TaskManagerModel]:
        self.session.add_all(instances)
        self.session.commit()
        return instances

    def get_by_id(self, id: str) -> TaskManagerModel | None:
        result = self.session.execute(
            select(TaskManagerModel).where(TaskManagerModel.id == id)
        )
        return result.scalar_one_or_none()

    def get_all(self) -> list[TaskManagerModel]:
        result = self.session.execute(select(TaskManagerModel))
        return result.scalars().all()

    def delete(self, id: str) -> None:
        instance = self.get_by_id(id)
        if instance:
            self.session.delete(instance)
            self.session.commit()

    def update(self, instance: TaskManagerModel) -> TaskManagerModel:
        self.session.add(instance)
        self.session.commit()
        self.session.refresh(instance)
        return instance
