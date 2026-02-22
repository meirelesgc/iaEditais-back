from datetime import datetime, timedelta
from http import HTTPStatus
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import OAuth2PasswordBearer
from jwt import DecodeError, ExpiredSignatureError, decode, encode
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from iaEditais.core.database import get_session
from iaEditais.core.settings import Settings
from iaEditais.models import User

SETTINGS = Settings()
pwd_context = PasswordHash.recommended()


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl='/auth/sign-in', auto_error=False
)


def create_access_token(data: dict):
    to_encode = data.copy()
    now = datetime.now(tz=ZoneInfo('UTC'))
    expire = now + timedelta(minutes=SETTINGS.ACCESS_TOKEN_EXPIRE_MINUTES)

    sub = str(to_encode['sub'])
    jti = str(uuid4())

    to_encode.update({'exp': expire, 'iat': now, 'jti': jti, 'sub': sub})
    encoded_jwt = encode(
        to_encode, SETTINGS.SECRET_KEY, algorithm=SETTINGS.ALGORITHM
    )
    return encoded_jwt


def get_password_hash(password: str):
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)


async def get_current_user(
    request: Request,
    token: str | None = Security(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
):
    credentials_exception = HTTPException(
        status_code=HTTPStatus.UNAUTHORIZED,
        detail='Could not validate credentials',
        headers={'WWW-Authenticate': 'Bearer'},
    )

    token = token or request.cookies.get(SETTINGS.ACCESS_TOKEN_COOKIE_NAME)

    if not token:
        raise credentials_exception

    try:
        payload = decode(
            token, SETTINGS.SECRET_KEY, algorithms=[SETTINGS.ALGORITHM]
        )
        subject_id = payload.get('sub')
        if not subject_id:
            raise credentials_exception
    except (DecodeError, ExpiredSignatureError):
        raise credentials_exception

    user = await session.scalar(select(User).where(User.id == subject_id))
    if not user:
        raise credentials_exception

    return user
