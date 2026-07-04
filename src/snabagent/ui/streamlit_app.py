"""Streamlit-дашборд SnabAgent.

Страницы:
  🏠 Лоты — список + фильтры
  ➕ Новый лот — форма создания
  📋 Детали лота — Top-3 + audit tree
  🔍 Audit Log — глобальный поиск
  ⚙️ Админ — LLM-переключатели, переиндексация
"""
from __future__ import annotations

import os
from typing import Any

import httpx
import pandas as pd
import plotly.express as px
import streamlit as st

API_BASE = os.environ.get("STREAMLIT_API_BASE", "http://localhost:8000")
API_KEY = os.environ.get("STREAMLIT_API_KEY", "dev-only-key-change-in-prod")

st.set_page_config(page_title="SnabAgent", layout="wide", page_icon="🏗️")

# Dark mode state
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

_LIGHT_CSS = """
<style>
  .stApp { background-color: #f8fafc; }
  h1, h2, h3 { color: #0f172a; }
  .stButton>button[kind="primary"] { background: #16a34a; color: white; border: 0; }
  .stButton>button[kind="primary"]:hover { background: #15803d; }
  .stMetric { background: white; border-radius: 8px; padding: 8px;
              box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
  .lot-badge {
    display: inline-block; padding: 2px 8px; border-radius: 4px;
    font-size: 0.85em; font-weight: 600;
  }
  .lot-badge.report_ready { background: #dcfce7; color: #166534; }
  .lot-badge.escalated { background: #fee2e2; color: #991b1b; }
  .lot-badge.failed { background: #fee2e2; color: #991b1b; }
  .lot-badge.planned { background: #dbeafe; color: #1e40af; }
  .lot-badge.draft { background: #f3f4f6; color: #374151; }
  footer { visibility: hidden; }
  #MainMenu { visibility: hidden; }
</style>
"""

_DARK_CSS = """
<style>
  .stApp { background-color: #0f172a; color: #e2e8f0; }
  h1, h2, h3 { color: #f1f5f9; }
  .stButton>button[kind="primary"] { background: #16a34a; color: white; border: 0; }
  .stButton>button[kind="primary"]:hover { background: #15803d; }
  .stMetric { background: #1e293b; border-radius: 8px; padding: 8px;
              box-shadow: 0 1px 3px rgba(0,0,0,0.3); color: #e2e8f0; }
  .lot-badge {
    display: inline-block; padding: 2px 8px; border-radius: 4px;
    font-size: 0.85em; font-weight: 600;
  }
  .lot-badge.report_ready { background: #166534; color: #dcfce7; }
  .lot-badge.escalated { background: #991b1b; color: #fee2e2; }
  .lot-badge.failed { background: #991b1b; color: #fee2e2; }
  .lot-badge.planned { background: #1e40af; color: #dbeafe; }
  .lot-badge.draft { background: #374151; color: #f3f4f6; }
  .stMarkdown, .stText, p, span, label { color: #e2e8f0; }
  .stDataFrame { color: #e2e8f0; }
  footer { visibility: hidden; }
  #MainMenu { visibility: hidden; }
</style>
"""

st.markdown(_DARK_CSS if st.session_state.dark_mode else _LIGHT_CSS, unsafe_allow_html=True)


# === Авторизация (JWT поверх REST) =================================
# Backward-compat:
#  - если задан STREAMLIT_ADMIN_PASSWORD (legacy demo) и нет email-логина —
#    используем тот же путь + X-API-Key для дев-режима.
LEGACY_ADMIN_PASS = os.environ.get("STREAMLIT_ADMIN_PASSWORD", "demo")
USE_LEGACY = os.environ.get("STREAMLIT_LOGIN_MODE", "auto").lower() == "legacy"

if "authed" not in st.session_state:
    st.session_state.authed = False
    st.session_state.token = None
    st.session_state.user = None


def _api_login(email: str, password: str) -> dict | None:
    try:
        with httpx.Client(base_url=API_BASE, timeout=10) as c:
            r = c.post("/auth/login", json={"email": email, "password": password})
            if r.status_code == 200:
                return r.json()
    except Exception:
        pass
    return None


if not st.session_state.authed:
    st.title("🔐 SnabAgent — вход")
    if USE_LEGACY:
        pw = st.text_input("Пароль", type="password")
        if st.button("Войти"):
            if pw == LEGACY_ADMIN_PASS:
                st.session_state.authed = True
                st.session_state.token = None  # X-API-Key fallback
                st.session_state.user = {"role": "admin", "email": "admin@demo"}
                st.rerun()
            else:
                st.error("Неверный пароль")
    else:
        col1, col2 = st.columns(2)
        with col1:
            email = st.text_input("Email", placeholder="admin@sibur.demo")
        with col2:
            password = st.text_input("Пароль", type="password")
        col_a, col_b = st.columns([1, 3])
        with col_a:
            if st.button("Войти", type="primary"):
                data = _api_login(email, password) if email and password else None
                if data:
                    st.session_state.authed = True
                    st.session_state.token = data["access_token"]
                    st.session_state.user = {
                        "user_id": data["user_id"],
                        "customer_id": data["customer_id"],
                        "role": data["role"],
                        "email": data["email"],
                    }
                    st.rerun()
                else:
                    st.error("Неверный email или пароль")
        with col_b:
            if st.button("Demo-вход (dev)"):
                # X-API-Key dev-bypass для оффлайн-демо
                st.session_state.authed = True
                st.session_state.token = None
                st.session_state.user = {"role": "admin", "email": "demo@local"}
                st.rerun()
        with st.expander("Demo-учётки (после `make seed-users`)"):
            st.markdown(
                "- `admin@sibur.demo` / `admin123` — full access\n"
                "- `buyer@sibur.demo` / `buyer123` — может одобрять <5M ₽\n"
                "- `viewer@sibur.demo` / `viewer123` — только просмотр"
            )
    st.stop()


def _auth_headers() -> dict[str, str]:
    if st.session_state.token:
        return {"Authorization": f"Bearer {st.session_state.token}"}
    return {"X-API-Key": API_KEY}


_AUTH_HEADERS = _auth_headers()


def api_get(path: str, **kwargs) -> Any:
    with httpx.Client(base_url=API_BASE, timeout=15, headers=_AUTH_HEADERS) as c:
        r = c.get(path, **kwargs)
        r.raise_for_status()
        return r.json()


def api_post(path: str, **kwargs) -> Any:
    with httpx.Client(base_url=API_BASE, timeout=30, headers=_AUTH_HEADERS) as c:
        r = c.post(path, **kwargs)
        r.raise_for_status()
        return r.json()


# Logo in sidebar
st.sidebar.markdown(
    "<div style='text-align:center;padding:8px 0;'>"
    "<span style='font-size:2em;'>🏗️</span><br>"
    "<strong style='font-size:1.2em;'>SnabAgent</strong>"
    "</div>",
    unsafe_allow_html=True,
)
st.sidebar.divider()

PAGES = ["🏠 Лоты", "➕ Новый лот", "📋 Детали лота", "🔍 Audit Log", "📊 Метрики", "📈 Аналитика", "⚙️ Админ"]
choice = st.sidebar.radio("Навигация", PAGES, index=0)
st.sidebar.divider()

# Dark mode toggle
dark_mode = st.sidebar.toggle("Dark mode", value=st.session_state.dark_mode)
if dark_mode != st.session_state.dark_mode:
    st.session_state.dark_mode = dark_mode
    st.rerun()

st.sidebar.divider()
_user = st.session_state.get("user") or {}
st.sidebar.markdown(
    f"**{_user.get('email') or '—'}**  \n`role: {_user.get('role') or '—'}`"
)
if st.sidebar.button("Выйти"):
    st.session_state.authed = False
    st.session_state.token = None
    st.session_state.user = None
    st.rerun()
st.sidebar.markdown(f"`API_BASE = {API_BASE}`")

if choice == "🏠 Лоты":
    st.title("Лоты")
    # Фильтры
    fcol1, fcol2, fcol3 = st.columns([2, 2, 2])
    with fcol1:
        f_status = st.selectbox(
            "Статус",
            ["", "draft", "planned", "sourcing", "rfq_sent", "responses_collected",
             "negotiating", "verified", "report_ready", "approved", "rejected",
             "escalated", "failed"],
            index=0,
        )
    with fcol2:
        f_limit = st.slider("Лимит", 10, 200, 50, step=10)
    with fcol3:
        f_search = st.text_input("Поиск по preview", "")
    try:
        params: dict[str, Any] = {"limit": f_limit}
        if f_status:
            params["status"] = f_status
        lots = api_get("/lots/", params=params)
    except Exception as e:
        st.error(f"Не удалось получить лоты: {e}")
        st.stop()
    if f_search and lots:
        lots = [
            x for x in lots if f_search.lower() in (x.get("raw_request_preview") or "").lower()
        ]
    if not lots:
        st.info("Пока нет лотов — создайте первый на странице «➕ Новый лот».")
    else:
        df = pd.DataFrame(lots)
        st.metric("Лотов в выборке", len(df))
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Распределение по статусам
        try:
            status_counts = df["status"].value_counts().reset_index()
            status_counts.columns = ["status", "count"]
            fig = px.bar(
                status_counts, x="status", y="count",
                color="status",
                title="Распределение лотов по статусам",
            )
            st.plotly_chart(fig, use_container_width=True)
        except Exception:
            pass


elif choice == "➕ Новый лот":
    st.title("Новый лот")
    with st.form("new_lot"):
        customer = st.text_input("Заказчик", value="SIBUR Demo")
        phase = st.selectbox("Фаза закупки", ["pre_nmck", "unregulated", "post_tender_published"], 0)
        raw = st.text_area("Сырой запрос", height=250, placeholder="Например: «нужно швеллер 14 ст3пс, 10 тонн»")
        attach = st.file_uploader("Дополнительный ТЗ-файл (.pdf, .docx, .txt)", type=["pdf", "docx", "txt"])
        submitted = st.form_submit_button("Запустить", type="primary")
        if submitted and raw:
            try:
                extra = ""
                if attach:
                    # Парсим файл через API (без локального импорта)
                    with httpx.Client(base_url=API_BASE, timeout=30,
                                      headers=_AUTH_HEADERS) as c:
                        files = {"file": (attach.name, attach.getvalue())}
                        r = c.post("/lots/parse-attachment", files=files)
                        r.raise_for_status()
                        extra = "\n\n" + (r.json().get("text") or "")
                resp = api_post("/lots", json={
                    "customer_name": customer,
                    "raw_request": raw + extra,
                    "phase": phase,
                })
                st.success(f"Лот создан: {resp['id']} (статус {resp['status']})")
                st.info("Прогресс выполнения смотрите в «📋 Детали лота» — обновите страницу через 5–10 сек.")
                st.session_state["last_lot_id"] = resp["id"]
            except Exception as e:
                st.error(str(e))

    st.divider()
    st.subheader("📤 Импорт из Excel")
    excel_file = st.file_uploader(
        "Excel со списком позиций (xlsx)", type=["xlsx"], key="excel_imp"
    )
    excel_customer = st.text_input("Заказчик (для Excel)", value="SIBUR Demo", key="excel_cust")
    if st.button("Импортировать Excel") and excel_file:
        with httpx.Client(base_url=API_BASE, timeout=30, headers=_AUTH_HEADERS) as c:
            files = {"file": (
                excel_file.name,
                excel_file.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )}
            r = c.post(
                "/lots/import-excel",
                files=files,
                params={"customer_name": excel_customer, "phase": "pre_nmck"},
            )
            if r.status_code == 200:
                data = r.json()
                st.success(f"Импортировано {data['n_rows']} строк, лот {data['id']}")
            else:
                st.error(f"{r.status_code}: {r.text}")


elif choice == "📋 Детали лота":
    st.title("Детали лота")
    try:
        all_lots = api_get("/lots/")
    except Exception as e:
        st.error(str(e))
        st.stop()
    if not all_lots:
        st.info("Пока нет лотов")
        st.stop()
    lot_options = {
        f"{lot_item['id'][:8]} · {lot_item['status']} · {lot_item['raw_request_preview'][:60]}": lot_item["id"]
        for lot_item in all_lots
    }
    sel = st.selectbox("Выберите лот", list(lot_options.keys()))
    lot_id = lot_options[sel]
    lot = api_get(f"/lots/{lot_id}")
    audit = api_get(f"/lots/{lot_id}/audit")
    col1, col2 = st.columns([3, 2])
    with col1:
        st.subheader("Статус и резюме")
        st.markdown(f"**Статус:** `{lot['status']}` · **Категория:** {lot.get('category') or '—'}")
        st.markdown(f"**Создан:** {lot['created_at']}  ·  **Обновлён:** {lot['updated_at']}")
        st.code(lot["raw_request"], language="text")
        if lot.get("requires_human"):
            st.warning(f"⚠ Эскалация: {lot.get('escalation_reason') or 'без причины'}")
        if lot.get("final_report"):
            report = lot["final_report"]
            st.markdown("### Top-3 КП")
            top = report.get("top_3") or []
            if top:
                top_df = pd.DataFrame(top)
                if not top_df.empty:
                    st.dataframe(top_df, use_container_width=True, hide_index=True)
                # Сравнение цен Plotly
                try:
                    price_df = top_df.copy()
                    price_df["price"] = price_df.get("total_price_rub", 0)
                    fig = px.bar(
                        price_df,
                        x="supplier_name",
                        y="price",
                        color="supplier_name",
                        title="Сравнение цен Top-3 поставщиков, ₽",
                    )
                    st.plotly_chart(fig, use_container_width=True)
                except Exception:
                    pass
            st.markdown("### Резюме")
            st.success(report.get("summary") or "—")
            mcol1, mcol2 = st.columns(2)
            with mcol1:
                st.metric("Экономия vs средне-рыночной, %", report.get("savings_vs_avg_pct"))
            with mcol2:
                st.metric("Экономия, ₽", report.get("savings_vs_avg_rub"))
            cols = st.columns(2)
            with cols[0]:
                if st.button("✅ Approve Top-1", type="primary"):
                    resp = api_post(f"/lots/{lot_id}/approve", json={"reviewer_name": "demo"})
                    st.success(f"Подтверждено: {resp.get('status')}")
            with cols[1]:
                if st.button("❌ Reject"):
                    resp = api_post(f"/lots/{lot_id}/reject", json={"reviewer_name": "demo"})
                    st.warning(f"Отклонено: {resp.get('status')}")
            # P0-4: безопасное скачивание — Streamlit-бэкенд сам делает запрос
            # с правильным X-API-Key, отдаёт пользователю байты. Ключ не светится.
            try:
                with httpx.Client(
                    base_url=API_BASE, timeout=30, headers=_AUTH_HEADERS
                ) as c:
                    excel_resp = c.get(f"/lots/{lot_id}/report.xlsx")
                if excel_resp.status_code == 200:
                    st.download_button(
                        "📥 Скачать отчёт в Excel",
                        data=excel_resp.content,
                        file_name=f"snabagent-report-{lot_id[:8]}.xlsx",
                        mime=(
                            "application/vnd.openxmlformats-officedocument."
                            "spreadsheetml.sheet"
                        ),
                    )
                else:
                    st.caption(f"Excel недоступен: {excel_resp.status_code}")
            except Exception as _exc:
                st.caption(f"Excel-отчёт временно недоступен: {_exc}")
    with col2:
        st.subheader("Audit-tree")
        if not audit:
            st.info("Пока нет аудит-событий — запустите лот")
        for ev in audit:
            title = (
                f"[{ev['agent_name']}] {ev['step_name']}"
                f" — conf {ev.get('confidence')}"
                f" — {ev.get('latency_ms') or '—'}ms"
                f" — {ev.get('model_name') or '—'}"
            )
            with st.expander(title):
                t1, t2, t3, t4, t5 = st.tabs(["Input", "Output", "Prompt", "Raw LLM", "Meta"])
                with t1:
                    st.json(ev.get("input_payload") or {})
                with t2:
                    st.json(ev.get("output_payload") or {})
                with t3:
                    st.markdown(f"```\n{ev.get('prompt_text') or ''}\n```")
                with t4:
                    st.json(ev.get("llm_response_raw") or {})
                with t5:
                    st.write({
                        "model": ev.get("model_name"),
                        "tokens_in": ev.get("prompt_tokens"),
                        "tokens_out": ev.get("completion_tokens"),
                        "latency_ms": ev.get("latency_ms"),
                        "decision": ev.get("decision"),
                        "created_at": ev.get("created_at"),
                    })


elif choice == "🔍 Audit Log":
    st.title("Audit Log (глобально)")
    agent = st.selectbox(
        "Агент",
        ["", "planner", "sourcer", "communicator", "negotiator", "verifier", "reporter"],
    )
    rows = api_get("/lots/audit/global", params={"agent_name": agent} if agent else None)
    if not rows:
        st.info("Пусто")
    else:
        df = pd.DataFrame(rows)
        cols = [
            "created_at", "agent_name", "step_name", "decision",
            "confidence", "latency_ms", "model_name", "lot_id",
        ]
        st.dataframe(df[cols], use_container_width=True, hide_index=True)
        st.download_button("Скачать как CSV", df.to_csv(index=False).encode("utf-8"), "audit.csv", "text/csv")
        # Latency by agent
        try:
            df["latency_ms"] = pd.to_numeric(df["latency_ms"], errors="coerce")
            agg = df.groupby("agent_name", as_index=False)["latency_ms"].mean()
            fig = px.bar(
                agg, x="agent_name", y="latency_ms",
                title="Средняя задержка LLM по агенту, мс",
                color="agent_name",
            )
            st.plotly_chart(fig, use_container_width=True)
        except Exception:
            pass


elif choice == "📊 Метрики":
    st.title("Метрики")
    try:
        lots = api_get("/lots/", params={"limit": 200})
    except Exception as e:
        st.error(str(e))
        lots = []
    if not lots:
        st.info("Нет данных — создайте несколько лотов.")
    else:
        df = pd.DataFrame(lots)
        st.metric("Всего лотов", len(df))
        ready = df[df["status"] == "report_ready"]
        approved = df[df["status"] == "approved"]
        escalated = df[df["status"] == "escalated"]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("report_ready", len(ready))
        c2.metric("approved", len(approved))
        c3.metric("escalated", len(escalated))
        c4.metric("requires_human", int(df["requires_human"].sum()) if "requires_human" in df else 0)

        # Stage distribution
        try:
            status_df = df["status"].value_counts().reset_index()
            status_df.columns = ["status", "count"]
            fig = px.pie(status_df, names="status", values="count", title="Статусы лотов")
            st.plotly_chart(fig, use_container_width=True)
        except Exception:
            pass

        st.subheader("Prometheus /metrics (raw)")
        try:
            with httpx.Client(base_url=API_BASE, timeout=5, headers=_AUTH_HEADERS) as c:
                r = c.get("/metrics")
            if r.status_code == 200:
                st.code(r.text[:3000], language="text")
            else:
                st.caption(f"/metrics недоступен: {r.status_code}")
        except Exception as e:
            st.caption(f"/metrics временно недоступен: {e}")


elif choice == "📈 Аналитика":
    st.title("📈 Аналитика закупок")

    try:
        lots = api_get("/lots/", params={"limit": 500})
    except Exception as e:
        st.error(str(e))
        lots = []

    if not lots:
        st.info("Нет данных для аналитики. Создайте и обработайте несколько лотов.")
    else:
        df = pd.DataFrame(lots)

        # KPI Cards
        st.subheader("Ключевые показатели")
        k1, k2, k3, k4, k5 = st.columns(5)
        total = len(df)
        ready = len(df[df["status"] == "report_ready"]) if "status" in df else 0
        approved = len(df[df["status"] == "approved"]) if "status" in df else 0
        escalated = len(df[df["status"] == "escalated"]) if "status" in df else 0
        failed = len(df[df["status"] == "failed"]) if "status" in df else 0

        k1.metric("Всего лотов", total)
        k2.metric("Готовы к ревью", ready)
        k3.metric("Одобрены", approved)
        k4.metric("Эскалированы", escalated)
        k5.metric("Ошибки", failed)

        # Savings trends (placeholder with mock)
        st.subheader("Экономия по времени")
        if "created_at" in df.columns:
            df["date"] = pd.to_datetime(df["created_at"], errors="coerce").dt.date
            if df["date"].notna().any():
                daily = df.groupby("date").size().reset_index(name="count")
                fig_trend = px.line(daily, x="date", y="count", title="Лоты по дням")
                st.plotly_chart(fig_trend, use_container_width=True)

        # Status funnel
        st.subheader("Воронка статусов")
        if "status" in df.columns:
            status_order = [
                "draft", "planned", "sourcing", "rfq_sent",
                "responses_collected", "negotiating", "verified",
                "report_ready", "approved", "rejected", "escalated", "failed",
            ]
            status_counts = df["status"].value_counts()
            funnel_data = []
            for s in status_order:
                if s in status_counts.index:
                    funnel_data.append({"status": s, "count": int(status_counts[s])})
            if funnel_data:
                fdf = pd.DataFrame(funnel_data)
                fig_funnel = px.bar(fdf, x="status", y="count", title="Воронка обработки")
                st.plotly_chart(fig_funnel, use_container_width=True)

        # Category distribution
        st.subheader("По категориям")
        if "category" in df.columns:
            cat_df = df["category"].dropna().value_counts().reset_index()
            cat_df.columns = ["category", "count"]
            if not cat_df.empty:
                fig_cat = px.pie(cat_df, names="category", values="count", title="Распределение по категориям")
                st.plotly_chart(fig_cat, use_container_width=True)


elif choice == "⚙️ Админ":
    st.title("Админ")
    st.write("Здесь можно:")
    st.markdown(
        """
* Переключить LLM в `.env` (LLM_PRIMARY/FALLBACK/VERIFIER) и пере-стартовать API.
* Перезагрузить НСИ: `python scripts/seed_db.py`
* Перезалить НСИ в Qdrant: `python scripts/seed_qdrant.py`
* Health: API → `/health`, Qdrant → `:6333/healthz`
"""
    )
