from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.modules.auth.application.use_cases.authenticate import (
    Credentials,
    Registration,
)
from app.modules.auth.infrastructure.http.dependencies import (
    CurrentUserDep,
    LogInDep,
    RegisterUserDep,
)
from app.modules.auth.infrastructure.http.schemas import (
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def register(payload: RegisterRequest, use_case: RegisterUserDep) -> UserResponse:
    user = await use_case(
        Registration(
            email=payload.email,
            password=payload.password,
            full_name=payload.full_name,
        )
    )
    return UserResponse.of(user)


@router.post("/login", response_model=TokenResponse)
async def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    use_case: LogInDep,
) -> TokenResponse:
    """Form-encoded because that is what the OAuth2 password flow expects, and
    what makes the Swagger "Authorize" button work."""
    token = await use_case(Credentials(email=form.username, password=form.password))
    return TokenResponse(access_token=token.access_token, token_type=token.token_type)


@router.get("/me", response_model=UserResponse)
async def me(user: CurrentUserDep) -> UserResponse:
    return UserResponse.of(user)
