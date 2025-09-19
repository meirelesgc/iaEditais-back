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
from iaEditais.models import User
from iaEditais.settings import Settings

settings = Settings()
pwd_context = PasswordHash.recommended()

ACCESS_TOKEN_COOKIE_NAME = 'access_token'

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl='/auth/sign-in', auto_error=False
)


def create_access_token(data: dict):
    to_encode = data.copy()
    now = datetime.now(tz=ZoneInfo('UTC'))
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({'exp': expire, 'iat': now, 'jti': str(uuid4())})
    encoded_jwt = encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
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

    token = token or request.cookies.get(ACCESS_TOKEN_COOKIE_NAME)

    if not token:
        raise credentials_exception

    try:
        payload = decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        subject_email = payload.get('sub')
        if not subject_email:
            raise credentials_exception
    except (DecodeError, ExpiredSignatureError):
        raise credentials_exception

    user = await session.scalar(
        select(User).where(User.email == subject_email)
    )
    if not user:
        raise credentials_exception

    return user
