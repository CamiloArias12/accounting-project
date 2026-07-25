from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.modules.auth.dependencies import CurrentUser, ServiceDep
from app.modules.auth.models import User
from app.modules.auth.schemas import RegisterRequest, TokenResponse, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, service: ServiceDep) -> User:
    return await service.register(payload)


@router.post("/login", response_model=TokenResponse)
async def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()], service: ServiceDep
) -> TokenResponse:
    """Form-encoded because that is what the OAuth2 password flow expects, and
    what makes the Swagger "Authorize" button work."""
    token = await service.log_in(form.username, form.password)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserRead)
async def me(user: CurrentUser) -> User:
    return user
