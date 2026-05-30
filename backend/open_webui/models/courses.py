import logging
import time
from typing import Optional
import uuid

from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from open_webui.internal.db import Base, get_async_db_context

from open_webui.models.files import FileMetadataResponse
from open_webui.models.users import UserResponse

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, Text, JSON

log = logging.getLogger(__name__)

####################
# Course DB Schema
####################


class Course(Base):
    __tablename__ = 'course'

    id = Column(Text, unique=True, primary_key=True)
    user_id = Column(Text)

    name = Column(Text)

    # Backing knowledge collection holding the course materials (RAG).
    knowledge_id = Column(Text)

    meta = Column(JSON, nullable=True)

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class CourseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str

    name: str

    knowledge_id: Optional[str] = None

    meta: Optional[dict] = None

    created_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch


####################
# Forms
####################


class CourseForm(BaseModel):
    name: str


class CourseUserModel(CourseModel):
    user: Optional[UserResponse] = None


class CourseResponse(CourseModel):
    files: Optional[list[FileMetadataResponse | dict]] = None


class CourseListResponse(BaseModel):
    items: list[CourseUserModel]
    total: int


class CourseTable:
    async def insert_new_course(
        self,
        user_id: str,
        form_data: CourseForm,
        knowledge_id: str,
        db: Optional[AsyncSession] = None,
    ) -> Optional[CourseModel]:
        async with get_async_db_context(db) as db:
            course = CourseModel(
                **{
                    **form_data.model_dump(),
                    'id': str(uuid.uuid4()),
                    'user_id': user_id,
                    'knowledge_id': knowledge_id,
                    'meta': None,
                    'created_at': int(time.time()),
                    'updated_at': int(time.time()),
                }
            )

            try:
                result = Course(**course.model_dump())
                db.add(result)
                await db.commit()
                await db.refresh(result)
                return CourseModel.model_validate(result) if result else None
            except Exception as e:
                log.exception(e)
                return None

    async def get_courses(self, db: Optional[AsyncSession] = None) -> list[CourseModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(select(Course).order_by(Course.updated_at.desc()))
            return [CourseModel.model_validate(course) for course in result.scalars().all()]

    async def get_course_by_id(self, id: str, db: Optional[AsyncSession] = None) -> Optional[CourseModel]:
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(select(Course).filter_by(id=id))
                course = result.scalars().first()
                return CourseModel.model_validate(course) if course else None
        except Exception:
            return None

    async def update_course_by_id(
        self, id: str, form_data: CourseForm, db: Optional[AsyncSession] = None
    ) -> Optional[CourseModel]:
        try:
            async with get_async_db_context(db) as db:
                await db.execute(
                    update(Course)
                    .filter_by(id=id)
                    .values(**form_data.model_dump(), updated_at=int(time.time()))
                )
                await db.commit()
                return await self.get_course_by_id(id=id, db=db)
        except Exception as e:
            log.exception(e)
            return None

    async def delete_course_by_id(self, id: str, db: Optional[AsyncSession] = None) -> bool:
        try:
            async with get_async_db_context(db) as db:
                await db.execute(delete(Course).filter_by(id=id))
                await db.commit()
                return True
        except Exception:
            return False


Courses = CourseTable()
