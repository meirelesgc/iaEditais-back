from typing import Literal

from pydantic import BaseModel


class PasswordResetRequest(BaseModel):
    type: Literal['sms', 'email', 'message'] = 'message'
