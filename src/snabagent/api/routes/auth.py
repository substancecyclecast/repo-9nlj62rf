"""Auth-роуты: логин (JWT), регистрация, refresh token, password policy."""

import re
from datetime import UTC, datetime, timedelta
from typing import Union

from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.models import Customer, UserRole
from ...db.repositories import UserRepo
from ...db.session import get_session
from ..auth import Principal, get_principal
from ..schemas.auth import (
    LoginIn,
    RefreshIn,
    RefreshOut,
    RegisterIn,
    RegisterOut,
    TokenOut,
    UserCreateIn,
    UserOut,
    UserRoleEnum,
)
from ..security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    verify_refresh_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])

limiter = Limiter(key_func=get_remote_address)

# Password policy constants
_MIN_PW_LEN = 8
_PW_DIGIT_RE = re.compile(r"\d")
_PW_SPECIAL_RE = re.compile(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?~`]")


def _validate_password(password: str) -> None:
    """Enforce password policy: min 8 chars, 1 digit, 1 special char."""
    errors: list[str] = []
    if len(password) < _MIN_PW_LEN:
        errors.append(f"minimum {_MIN_PW_LEN} characters")
    if not _PW_DIGIT_RE.search(password):
        errors.append("at least 1 digit")
    if not _PW_SPECIAL_RE.search(password):
        errors.append("at least 1 special character")
    if errors:
        raise HTTPException(
            422,
            detail=f"Password too weak: {', '.join(errors)}",
        )


@router.post("/register", response_model=RegisterOut)
@limiter.limit("3/minute")
async def register(
    request: Request,
    payload: RegisterIn,
    session: AsyncSession = Depends(get_session),
):
    """Public self-service registration. No API key required."""
    _validate_password(payload.password)

    existing = await UserRepo(session).by_email(payload.email)
    if existing:
        raise HTTPException(409, "Пользователь с таким email уже существует")

    customer = Customer(
        name=payload.company_name,
        inn=payload.inn,
        trial_until=datetime.now(UTC) + timedelta(days=14),
    )
    session.add(customer)
    await session.flush()

    from ...db.models import User

    user = User(
        email=payload.email.lower(),
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        customer_id=customer.id,
        role=UserRole.buyer,
        is_active=True,  # MVP: auto-activate without email verification
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    await session.refresh(customer)

    return RegisterOut(
        user_id=user.id,
        customer_id=customer.id,
        email=user.email,
        message="Регистрация успешна. Добро пожаловать в SnabAgent!",
    )


@router.post("/login", response_model=TokenOut)
@limiter.limit("10/minute")
async def login(
    request: Request,
    payload: LoginIn,
    session: AsyncSession = Depends(get_session),
):
    from ...settings import settings as app_settings

    # Demo mode: auto-create demo user if doesn't exist
    if app_settings.demo_mode and payload.email == "demo@snabagent.ru":
        user = await UserRepo(session).by_email("demo@snabagent.ru")
        if not user:
            from datetime import datetime as dt

            now_naive = dt.utcnow()
            customer = Customer(
                name="Demo Company",
                inn="7700000001",
                trial_until=now_naive + timedelta(days=365),
            )
            session.add(customer)
            await session.flush()

            from ...db.models import User

            user = User(
                email="demo@snabagent.ru",
                hashed_password=hash_password("Demo123!@#"),
                full_name="Демо Пользователь",
                customer_id=customer.id,
                role=UserRole.admin,
                is_active=True,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

            # Seed demo lots
            await _seed_demo_lots(session, user)

        if not verify_password(payload.password, user.hashed_password):
            raise HTTPException(401, "Invalid credentials")

        access_token = create_access_token({
            "sub": str(user.id),
            "customer_id": str(user.customer_id) if user.customer_id else None,
            "role": user.role.value,
            "email": user.email,
        })
        refresh_token = create_refresh_token(str(user.id))

        return TokenOut(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=15 * 60,
            user_id=user.id,
            customer_id=user.customer_id,
            role=UserRoleEnum(user.role.value),
            email=user.email,
        )

    user = await UserRepo(session).by_email(payload.email)
    if not user or not user.is_active:
        raise HTTPException(401, "Invalid credentials")
    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(401, "Invalid credentials")

    await UserRepo(session).touch_last_login(user.id)

    access_token = create_access_token({
        "sub": str(user.id),
        "customer_id": str(user.customer_id) if user.customer_id else None,
        "role": user.role.value,
        "email": user.email,
    })
    refresh_token = create_refresh_token(str(user.id))

    return TokenOut(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=15 * 60,
        user_id=user.id,
        customer_id=user.customer_id,
        role=UserRoleEnum(user.role.value),
        email=user.email,
    )


async def _seed_demo_lots(session: AsyncSession, user) -> None:
    """Create sample demo lots for showcase."""
    from ...db.models import Lot, LotStatus

    demo_lots = [
        {
            "raw_request": (
                "Закупка подшипников SKF 6205-2Z для ремонта конвейерной линии. "
                "Требуется 500 шт. Бюджет до 2 000 000 руб. Срок поставки — 14 дней."
            ),
            "status": LotStatus.report_ready,
            "category": "mro",
            "total_estimated_rub": 2000000,
            "parsed_items": [
                {"name": "Подшипник SKF 6205-2Z", "qty": 500, "unit": "шт", "est_price_rub": 3500}
            ],
            "final_report": {
                "top_suppliers": [
                    {"name": "ООО БиарингСнаб", "price_rub": 1650000, "delivery_days": 10, "score": 92},
                    {"name": "ЗАО ПромПодшипник", "price_rub": 1720000, "delivery_days": 12, "score": 87},
                    {"name": "ООО ИндустриалМаркет", "price_rub": 1800000, "delivery_days": 8, "score": 85},
                ],
                "savings_pct": 17.5,
                "savings_rub": 350000,
                "nmck_justification": "НМЦК рассчитана методом сопоставимых рыночных цен на основе 3 КП.",
            },
        },
        {
            "raw_request": "Нужен кабель ВВГнг-LS 3x2.5 для электромонтажных работ. 10 000 метров. Срочно, до 7 дней.",
            "status": LotStatus.negotiating,
            "category": "mro",
            "total_estimated_rub": 500000,
            "parsed_items": [
                {"name": "Кабель ВВГнг-LS 3x2.5", "qty": 10000, "unit": "м", "est_price_rub": 45}
            ],
            "final_report": {},
        },
        {
            "raw_request": (
                "Закупка серверного оборудования: 5 серверов Dell PowerEdge R750xs "
                "для обновления ЦОД. Бюджет 15 млн руб."
            ),
            "status": LotStatus.sourcing,
            "category": "it",
            "total_estimated_rub": 15000000,
            "parsed_items": [
                {"name": "Dell PowerEdge R750xs", "qty": 5, "unit": "шт", "est_price_rub": 2500000}
            ],
            "final_report": {},
        },
        {
            "raw_request": "Моющие средства для промышленной уборки: 200 л концентрата, 500 кг порошка, 1000 пар перчаток.",
            "status": LotStatus.approved,
            "category": "consumables",
            "total_estimated_rub": 800000,
            "parsed_items": [
                {"name": "Концентрат моющий промышленный", "qty": 200, "unit": "л", "est_price_rub": 1500},
                {"name": "Порошок моющий", "qty": 500, "unit": "кг", "est_price_rub": 800},
                {"name": "Перчатки рабочие", "qty": 1000, "unit": "пар", "est_price_rub": 150},
            ],
            "final_report": {
                "top_suppliers": [
                    {"name": "ООО КлинПром", "price_rub": 680000, "delivery_days": 5, "score": 95},
                    {"name": "ЗАО ХимСнаб", "price_rub": 710000, "delivery_days": 7, "score": 88},
                    {"name": "ООО ПромГигиена", "price_rub": 740000, "delivery_days": 4, "score": 84},
                ],
                "savings_pct": 15.0,
                "savings_rub": 120000,
                "nmck_justification": "НМЦК рассчитана на основании 3 КП от аккредитованных поставщиков.",
            },
        },
        {
            "raw_request": "Стальная труба 159x6 мм, ГОСТ 8732-78, 50 тонн. Поставка на площадку в Тюменской области.",
            "status": LotStatus.verified,
            "category": "metals",
            "total_estimated_rub": 5000000,
            "parsed_items": [
                {"name": "Труба 159x6 ГОСТ 8732-78", "qty": 50, "unit": "т", "est_price_rub": 85000}
            ],
            "final_report": {
                "top_suppliers": [
                    {"name": "ООО МеталлТрейд", "price_rub": 4100000, "delivery_days": 14, "score": 91},
                    {"name": "ПАО ТМК", "price_rub": 4250000, "delivery_days": 10, "score": 89},
                    {"name": "ООО СтальПром", "price_rub": 4350000, "delivery_days": 12, "score": 86},
                ],
                "savings_pct": 18.0,
                "savings_rub": 900000,
                "nmck_justification": "Расчёт по 3 КП. Экономия 18% от начального бюджета.",
            },
        },
    ]

    for lot_data in demo_lots:
        lot = Lot(
            customer_id=user.customer_id,
            raw_request=lot_data["raw_request"],
            status=lot_data["status"],
            category=lot_data["category"],
            total_estimated_rub=lot_data.get("total_estimated_rub"),
            parsed_items=lot_data["parsed_items"],
            final_report=lot_data["final_report"],
        )
        session.add(lot)

    await session.commit()


@router.post("/refresh", response_model=RefreshOut)
async def refresh(
    payload: RefreshIn,
    session: AsyncSession = Depends(get_session),
):
    """Exchange a valid refresh token for a new access+refresh pair."""
    claims = verify_refresh_token(payload.refresh_token)
    if claims is None:
        raise HTTPException(401, "Invalid or expired refresh token")
    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(401, "Invalid refresh token")

    user = await UserRepo(session).get(user_id)
    if not user or not user.is_active:
        raise HTTPException(401, "User not found or inactive")

    access_token = create_access_token({
        "sub": str(user.id),
        "customer_id": str(user.customer_id) if user.customer_id else None,
        "role": user.role.value,
        "email": user.email,
    })
    new_refresh = create_refresh_token(str(user.id))

    return RefreshOut(
        access_token=access_token,
        refresh_token=new_refresh,
        expires_in=15 * 60,
    )


@router.get("/me", response_model=Union[UserOut, dict])  # noqa: UP007
async def me(principal: Principal = Depends(get_principal), session: AsyncSession = Depends(get_session)):
    if principal.is_system:
        return {
            "id": "system",
            "role": "admin",
            "kind": "system",
            "email": None,
            "customer_id": None,
        }
    user = await UserRepo(session).get(principal.user_id) if principal.user_id else None
    if not user:
        raise HTTPException(404, "User not found")
    return UserOut(
        id=user.id,
        customer_id=user.customer_id,
        email=user.email,
        full_name=user.full_name,
        role=UserRoleEnum(user.role.value),
        approval_limit_rub=float(user.approval_limit_rub) if user.approval_limit_rub else None,
        is_active=user.is_active,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
    )


@router.post("/users", response_model=UserOut)
async def create_user(
    payload: UserCreateIn,
    principal: Principal = Depends(get_principal),
    session: AsyncSession = Depends(get_session),
):
    """Создание пользователя. Доступно только admin/system."""
    if not (principal.is_admin or principal.is_system):
        raise HTTPException(403, "Only admin can create users")
    _validate_password(payload.password)
    existing = await UserRepo(session).by_email(payload.email)
    if existing:
        raise HTTPException(409, "User with this email already exists")
    user = await UserRepo(session).create(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        customer_id=payload.customer_id,
        role=UserRole(payload.role.value),
        approval_limit_rub=payload.approval_limit_rub,
    )
    return UserOut(
        id=user.id,
        customer_id=user.customer_id,
        email=user.email,
        full_name=user.full_name,
        role=UserRoleEnum(user.role.value),
        approval_limit_rub=float(user.approval_limit_rub) if user.approval_limit_rub else None,
        is_active=user.is_active,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
    )


@router.post("/verify-email/send")
@limiter.limit("2/minute")
async def send_verify_email(
    request: Request,
    principal: Principal = Depends(get_principal),
    session: AsyncSession = Depends(get_session),
):
    """Send email verification link to the authenticated user."""
    if principal.is_system:
        raise HTTPException(400, "System user cannot verify email")
    user = await UserRepo(session).get(principal.user_id) if principal.user_id else None
    if not user:
        raise HTTPException(404, "User not found")
    if getattr(user, "email_verified", False):
        return {"status": "already_verified"}

    import secrets as _secrets

    token = _secrets.token_urlsafe(32)
    # Store token in user model (we use a simple approach: store in a field)
    user.email_verify_token = token
    await session.commit()

    from ...email_service.sender import send_verification_email

    await send_verification_email(user.email, token)
    return {"status": "sent", "email": user.email}


@router.get("/verify-email")
async def verify_email(
    token: str,
    session: AsyncSession = Depends(get_session),
):
    """Verify user email via token from email link."""
    if not token:
        raise HTTPException(400, "Token required")
    user = await UserRepo(session).by_verify_token(token)
    if not user:
        raise HTTPException(400, "Invalid or expired verification token")
    user.email_verified = True
    user.email_verify_token = None
    await session.commit()
    return {"status": "verified", "email": user.email}


@router.get("/users", response_model=list[UserOut])
async def list_users(
    principal: Principal = Depends(get_principal),
    session: AsyncSession = Depends(get_session),
):
    if not (principal.is_admin or principal.is_system):
        raise HTTPException(403, "Only admin can list users")
    cust_filter = principal.filter_customer_id()
    users = await UserRepo(session).list(customer_id=cust_filter)
    return [
        UserOut(
            id=u.id,
            customer_id=u.customer_id,
            email=u.email,
            full_name=u.full_name,
            role=UserRoleEnum(u.role.value),
            approval_limit_rub=float(u.approval_limit_rub) if u.approval_limit_rub else None,
            is_active=u.is_active,
            last_login_at=u.last_login_at,
            created_at=u.created_at,
        )
        for u in users
    ]
