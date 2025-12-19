from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordRequestForm
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.vectorstores import VectorStore
from sqlalchemy.ext.asyncio import AsyncSession

from iaEditais.core.database import get_session
from iaEditais.core.llm import get_model
from iaEditais.core.security import get_current_user
from iaEditais.core.vectorstore import get_vectorstore
from iaEditais.models import User

Session = Annotated[AsyncSession, Depends(get_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]
OAuth2Form = Annotated[OAuth2PasswordRequestForm, Depends()]
VStore = Annotated[VectorStore, Depends(get_vectorstore)]
Model = Annotated[BaseChatModel, Depends(get_model)]
