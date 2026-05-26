import asyncio
import io
import logging
import mimetypes
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from pydantic import BaseModel

from open_webui.config import CACHE_DIR
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import AIOHTTP_CLIENT_SESSION_SSL
from open_webui.utils.session_pool import get_session

from open_webui.models.chats import Chats
from open_webui.routers.files import upload_file_handler
from open_webui.utils.auth import get_admin_user, get_verified_user

log = logging.getLogger(__name__)

MUSIC_CACHE_DIR = CACHE_DIR / 'music' / 'generations'
MUSIC_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Mureka task states. The first set means "keep waiting", the rest are terminal.
MUREKA_PENDING_STATES = {'preparing', 'queued', 'running', 'streaming'}
MUREKA_SUCCESS_STATE = 'succeeded'

# Poll budget: avg generation ~45s, allow margin for queue + longer songs.
MUREKA_POLL_INTERVAL = 3  # seconds between status checks
MUREKA_POLL_TIMEOUT = 300  # max seconds to wait before giving up

router = APIRouter()


def get_music_model(request: Request) -> str:
    return request.app.state.config.MUSIC_GENERATION_MODEL or 'auto'


class MusicConfig(BaseModel):
    ENABLE_MUSIC_GENERATION: bool
    MUSIC_GENERATION_ENGINE: str
    MUSIC_GENERATION_MODEL: str
    MUREKA_API_BASE_URL: str
    MUREKA_API_KEY: str


@router.get('/config', response_model=MusicConfig)
async def get_config(request: Request, user=Depends(get_admin_user)):
    return {
        'ENABLE_MUSIC_GENERATION': request.app.state.config.ENABLE_MUSIC_GENERATION,
        'MUSIC_GENERATION_ENGINE': request.app.state.config.MUSIC_GENERATION_ENGINE,
        'MUSIC_GENERATION_MODEL': request.app.state.config.MUSIC_GENERATION_MODEL,
        'MUREKA_API_BASE_URL': request.app.state.config.MUREKA_API_BASE_URL,
        'MUREKA_API_KEY': request.app.state.config.MUREKA_API_KEY,
    }


@router.post('/config/update')
async def update_config(request: Request, form_data: MusicConfig, user=Depends(get_admin_user)):
    request.app.state.config.ENABLE_MUSIC_GENERATION = form_data.ENABLE_MUSIC_GENERATION
    request.app.state.config.MUSIC_GENERATION_ENGINE = form_data.MUSIC_GENERATION_ENGINE
    request.app.state.config.MUSIC_GENERATION_MODEL = form_data.MUSIC_GENERATION_MODEL
    request.app.state.config.MUREKA_API_BASE_URL = form_data.MUREKA_API_BASE_URL
    request.app.state.config.MUREKA_API_KEY = form_data.MUREKA_API_KEY

    return await get_config(request, user)


@router.get('/config/url/verify')
async def verify_url(request: Request, user=Depends(get_admin_user)):
    if request.app.state.config.MUSIC_GENERATION_ENGINE == 'mureka':
        headers = {'Authorization': f'Bearer {request.app.state.config.MUREKA_API_KEY}'}
        try:
            session = await get_session()
            # Billing is a cheap authenticated GET — confirms key + reachability.
            async with session.get(
                url=f'{request.app.state.config.MUREKA_API_BASE_URL}/account/billing',
                headers=headers,
                ssl=AIOHTTP_CLIENT_SESSION_SSL,
            ) as r:
                r.raise_for_status()
            return True
        except Exception as e:
            log.exception(e)
            raise HTTPException(status_code=400, detail=ERROR_MESSAGES.DEFAULT('Failed to connect to Mureka.'))
    return True


@router.get('/models')
async def get_models(request: Request, user=Depends(get_verified_user)):
    if request.app.state.config.MUSIC_GENERATION_ENGINE == 'mureka':
        return [
            {'id': 'auto', 'name': 'Auto'},
            {'id': 'mureka-6', 'name': 'Mureka V6'},
            {'id': 'mureka-7', 'name': 'Mureka V7'},
        ]
    return []


class MusicForm(BaseModel):
    prompt: str  # genre/mood/instrument description, e.g. "r&b, slow, male vocal"
    lyrics: Optional[str] = None  # song lyrics; if omitted, Mureka writes its own
    model: Optional[str] = None


async def upload_audio(request, audio_data, content_type, metadata, user):
    extension = mimetypes.guess_extension(content_type) or '.mp3'
    file = UploadFile(
        file=io.BytesIO(audio_data),
        filename=f'generated-music{extension}',  # converted to a unique ID on upload
        headers={'content-type': content_type},
    )
    file_item = await upload_file_handler(
        request,
        file=file,
        metadata=metadata,
        process=False,
        user=user,
    )

    if file_item and file_item.id:
        chat_id = metadata.get('chat_id')
        message_id = metadata.get('message_id')
        if chat_id and message_id:
            await Chats.insert_chat_files(
                chat_id=chat_id,
                message_id=message_id,
                file_ids=[file_item.id],
                user_id=user.id,
            )

    url = request.app.url_path_for('get_file_content_by_id', id=file_item.id)
    return file_item, url


async def _mureka_request(request, method: str, path: str, json=None):
    headers = {
        'Authorization': f'Bearer {request.app.state.config.MUREKA_API_KEY}',
        'Content-Type': 'application/json',
    }
    url = f'{request.app.state.config.MUREKA_API_BASE_URL}{path}'
    session = await get_session()
    async with session.request(
        method,
        url=url,
        json=json,
        headers=headers,
        ssl=AIOHTTP_CLIENT_SESSION_SSL,
    ) as r:
        r.raise_for_status()
        return await r.json()


async def music_generations(
    request: Request,
    form_data: MusicForm,
    metadata: Optional[dict] = None,
    user=None,
):
    metadata = metadata or {}
    model = form_data.model or get_music_model(request)

    if request.app.state.config.MUSIC_GENERATION_ENGINE != 'mureka':
        raise HTTPException(status_code=400, detail='Unsupported music generation engine.')

    if not request.app.state.config.MUREKA_API_KEY:
        raise HTTPException(status_code=400, detail='Mureka API key is not configured.')

    payload = {'model': model, 'prompt': form_data.prompt}
    if form_data.lyrics:
        payload['lyrics'] = form_data.lyrics
    else:
        # song/generate requires lyrics; let Mureka auto-write them from the prompt.
        payload['lyrics'] = '[auto]'

    try:
        task = await _mureka_request(request, 'POST', '/song/generate', json=payload)
    except Exception as e:
        log.exception(e)
        raise HTTPException(status_code=400, detail=ERROR_MESSAGES.DEFAULT('Mureka generation request failed.'))

    task_id = task.get('id')
    if not task_id:
        raise HTTPException(status_code=400, detail='Mureka did not return a task id.')

    # Poll until the async task reaches a terminal state.
    waited = 0
    result = task
    while result.get('status') in MUREKA_PENDING_STATES and waited < MUREKA_POLL_TIMEOUT:
        await asyncio.sleep(MUREKA_POLL_INTERVAL)
        waited += MUREKA_POLL_INTERVAL
        try:
            result = await _mureka_request(request, 'GET', f'/song/query/{task_id}')
        except Exception as e:
            log.exception(e)
            raise HTTPException(status_code=400, detail=ERROR_MESSAGES.DEFAULT('Mureka status query failed.'))

    status = result.get('status')
    if status != MUREKA_SUCCESS_STATE:
        if status in MUREKA_PENDING_STATES:
            raise HTTPException(status_code=504, detail='Mureka generation timed out.')
        detail = result.get('failed_reason') or f'Mureka generation {status}.'
        raise HTTPException(status_code=400, detail=detail)

    choices = result.get('choices') or []
    if not choices:
        raise HTTPException(status_code=400, detail='Mureka returned no audio.')

    session = await get_session()
    tracks = []
    for choice in choices:
        audio_url = choice.get('url') or choice.get('flac_url') or choice.get('wav_url')
        if not audio_url:
            continue
        async with session.get(audio_url, ssl=AIOHTTP_CLIENT_SESSION_SSL) as r:
            r.raise_for_status()
            audio_data = await r.read()
            content_type = r.headers.get('content-type', 'audio/mpeg')

        _, url = await upload_audio(
            request,
            audio_data,
            content_type,
            {**payload, **metadata, 'duration': choice.get('duration')},
            user,
        )
        tracks.append({'url': url, 'duration': choice.get('duration')})

    if not tracks:
        raise HTTPException(status_code=400, detail='Mureka returned no downloadable audio.')

    return tracks


@router.post('/generations')
async def generate_music(request: Request, form_data: MusicForm, user=Depends(get_verified_user)):
    if not request.app.state.config.ENABLE_MUSIC_GENERATION:
        raise HTTPException(status_code=403, detail=ERROR_MESSAGES.ACCESS_PROHIBITED)

    return await music_generations(request, form_data, user=user)
