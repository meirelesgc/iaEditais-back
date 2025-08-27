from datetime import datetime, timedelta
from http import HTTPStatus
from typing import List, Optional
from zoneinfo import ZoneInfo

from fastapi import Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from jwt import DecodeError, ExpiredSignatureError, decode, encode
from pwdlib import PasswordHash

from iaEditais.core.connection import Connection
from iaEditais.core.database import get_conn
from iaEditais.models import user_model

SECRET_KEY = 'your-secret-key'
ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 30
pwd_context = PasswordHash.recommended()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/auth/login')


async def get_token_from_cookie(request: Request) -> Optional[str]:
    return request.cookies.get('access_token')


async def get_current_user(
    request: Request, conn: Connection = Depends(get_conn)
):
    token = await get_token_from_cookie(request) if request else None

    if not token:
        raise HTTPException(
            status_code=HTTPStatus.UNAUTHORIZED,
            detail='Not authenticated',
            headers={'WWW-Authenticate': 'Bearer'},
        )

    credentials_exception = HTTPException(
        status_code=HTTPStatus.UNAUTHORIZED,
        detail='Could not validate credentials',
        headers={'WWW-Authenticate': 'Bearer'},
    )

    try:
        payload = decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        subject_email = payload.get('sub')
        if not subject_email:
            raise credentials_exception
    except (DecodeError, ExpiredSignatureError):
        raise credentials_exception

    SCRIPT_SQL = """
        SELECT id, username, email, phone_number, unit_id, access_level,
            password, created_at, updated_at
        FROM public.users
        WHERE email = %(email)s;
    """

    user = await conn.select(SCRIPT_SQL, {'email': subject_email}, True)

    if not user:
        raise credentials_exception

    return user_model.User(**user)


def authorize_user(allowed_access: List[str]):
    async def access_checker(current_user: dict = Depends(get_current_user)):
        access_level = current_user.get('access_level')
        if access_level not in allowed_access:
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN,
                detail='Not enough permissions',
            )
        return current_user

    return access_checker


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(tz=ZoneInfo('UTC')) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({'exp': expire})
    encoded_jwt = encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_password_hash(password: str):
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)
