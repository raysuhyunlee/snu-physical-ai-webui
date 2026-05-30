import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from open_webui.internal.db import get_async_session
from open_webui.models.courses import (
    Courses,
    CourseForm,
    CourseModel,
    CourseUserModel,
    CourseResponse,
    CourseListResponse,
)
from open_webui.models.knowledge import Knowledges, KnowledgeForm
from open_webui.models.files import Files
from open_webui.models.users import Users, UserResponse
from open_webui.retrieval.vector.async_client import ASYNC_VECTOR_DB_CLIENT
from open_webui.routers.retrieval import process_file, ProcessFileForm

from open_webui.constants import ERROR_MESSAGES
from open_webui.utils.auth import get_verified_user, get_admin_user

log = logging.getLogger(__name__)

router = APIRouter()


############################
# GetCourses (all users)
############################


@router.get('/', response_model=CourseListResponse)
async def get_courses(
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    courses = await Courses.get_courses(db=db)

    user_ids = list({course.user_id for course in courses})
    users = await Users.get_users_by_user_ids(user_ids, db=db) if user_ids else []
    users_dict = {u.id: u for u in users}

    return CourseListResponse(
        items=[
            CourseUserModel(
                **course.model_dump(),
                user=(
                    UserResponse(**users_dict[course.user_id].model_dump())
                    if course.user_id in users_dict
                    else None
                ),
            )
            for course in courses
        ],
        total=len(courses),
    )


############################
# GetCourseById
############################


async def _course_response(course: CourseModel, db: AsyncSession) -> CourseResponse:
    files = []
    if course.knowledge_id:
        files = await Knowledges.get_file_metadatas_by_id(course.knowledge_id, db=db)
    return CourseResponse(**course.model_dump(), files=files)


@router.get('/{id}', response_model=Optional[CourseResponse])
async def get_course_by_id(
    id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    course = await Courses.get_course_by_id(id=id, db=db)
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)
    return await _course_response(course, db)


############################
# CreateNewCourse (admin)
############################


@router.post('/create', response_model=Optional[CourseResponse])
async def create_new_course(
    request: Request,
    form_data: CourseForm,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    # Create the backing knowledge collection that holds course materials.
    knowledge = await Knowledges.insert_new_knowledge(
        user.id,
        KnowledgeForm(
            name=f'course:{form_data.name}',
            description='',
        ),
        db=db,
    )
    if not knowledge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT('Failed to create course knowledge collection'),
        )

    course = await Courses.insert_new_course(user.id, form_data, knowledge_id=knowledge.id, db=db)
    if not course:
        # Roll back the orphaned knowledge collection.
        await Knowledges.delete_knowledge_by_id(knowledge.id, db=db)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT('Failed to create course'),
        )

    return await _course_response(course, db)


############################
# UpdateCourse (admin)
############################


@router.post('/{id}/update', response_model=Optional[CourseResponse])
async def update_course_by_id(
    id: str,
    form_data: CourseForm,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    course = await Courses.get_course_by_id(id=id, db=db)
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    course = await Courses.update_course_by_id(id, form_data, db=db)
    return await _course_response(course, db)


############################
# AddFileToCourse (admin)
############################


class CourseFileIdForm(BaseModel):
    file_id: str


@router.post('/{id}/file/add', response_model=Optional[CourseResponse])
async def add_file_to_course_by_id(
    request: Request,
    id: str,
    form_data: CourseFileIdForm,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    course = await Courses.get_course_by_id(id=id, db=db)
    if not course or not course.knowledge_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    file = await Files.get_file_by_id(form_data.file_id, db=db)
    if not file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)
    if not file.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.FILE_NOT_PROCESSED,
        )

    try:
        # Embed the file into the course's knowledge collection.
        await process_file(
            request,
            ProcessFileForm(file_id=form_data.file_id, collection_name=course.knowledge_id),
            user=user,
            db=db,
        )
        await Knowledges.add_file_to_knowledge_by_id(
            knowledge_id=course.knowledge_id, file_id=form_data.file_id, user_id=user.id, db=db
        )
    except Exception as e:
        log.debug(e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return await _course_response(course, db)


############################
# RemoveFileFromCourse (admin)
############################


@router.post('/{id}/file/remove', response_model=Optional[CourseResponse])
async def remove_file_from_course_by_id(
    id: str,
    form_data: CourseFileIdForm,
    delete_file: bool = Query(True),
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    course = await Courses.get_course_by_id(id=id, db=db)
    if not course or not course.knowledge_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    if not await Knowledges.has_file(knowledge_id=course.knowledge_id, file_id=form_data.file_id, db=db):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    # Remove the chunks from the course collection and unlink the file.
    try:
        await ASYNC_VECTOR_DB_CLIENT.delete(
            collection_name=course.knowledge_id, filter={'file_id': form_data.file_id}
        )
    except Exception as e:
        log.debug(e)
    await Knowledges.remove_file_from_knowledge_by_id(course.knowledge_id, form_data.file_id, db=db)

    if delete_file:
        try:
            file_collection = f'file-{form_data.file_id}'
            if await ASYNC_VECTOR_DB_CLIENT.has_collection(collection_name=file_collection):
                await ASYNC_VECTOR_DB_CLIENT.delete_collection(collection_name=file_collection)
        except Exception as e:
            log.debug(e)
        await Files.delete_file_by_id(form_data.file_id, db=db)

    return await _course_response(course, db)


############################
# DeleteCourse (admin)
############################


@router.delete('/{id}/delete', response_model=bool)
async def delete_course_by_id(
    id: str,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    course = await Courses.get_course_by_id(id=id, db=db)
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    # Drop the backing vector collection and knowledge base, then the course.
    if course.knowledge_id:
        try:
            if await ASYNC_VECTOR_DB_CLIENT.has_collection(collection_name=course.knowledge_id):
                await ASYNC_VECTOR_DB_CLIENT.delete_collection(collection_name=course.knowledge_id)
        except Exception as e:
            log.debug(e)
        await Knowledges.delete_knowledge_by_id(course.knowledge_id, db=db)

    return await Courses.delete_course_by_id(id, db=db)
