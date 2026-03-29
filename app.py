import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from streamlit_calendar import calendar
import os
import re

if "selected_event_detail" not in st.session_state:
    st.session_state["selected_event_detail"] = None
if "admin_unlocked" not in st.session_state:
    st.session_state["admin_unlocked"] = False
if "current_view" not in st.session_state:
    st.session_state["current_view"] = "📋 전체 목록"

st.set_page_config(page_title="🌸 3-1반 수행평가 비서", page_icon="✨", layout="wide", initial_sidebar_state="collapsed")

URL_FILE = "sheet_url.txt"
UPLOAD_DIR = "uploads"

# 배포 시에는 환경변수 APP_ADMIN_PASSWORD 설정을 권장합니다.
ADMIN_PASSWORD = os.getenv("APP_ADMIN_PASSWORD", "teacher31")

saved_url = ""
if os.path.exists(URL_FILE):
    with open(URL_FILE, "r", encoding="utf-8") as f:
        saved_url = f.read().strip()

st.markdown(
    """
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    * { font-family: 'Pretendard', sans-serif; }
    [data-testid="stSidebar"] { display: none; }
    .stApp { background-color: #FFF9FB; }
    .main-header {
        text-align: center;
        padding: 1.2rem 0.8rem;
        background: linear-gradient(135deg, #FFB7C5 0%, #FF94B4 100%);
        border-radius: 0 0 22px 22px;
        color: white;
        margin-bottom: 16px;
        box-shadow: 0 4px 15px rgba(255, 148, 180, 0.3);
    }
    .main-header h1 {
        font-size: 1.35rem;
        margin: 0;
    }
    .main-header p {
        font-size: 0.85rem;
        margin-top: 0.35rem;
        margin-bottom: 0;
    }
    .student-card {
        border-radius: 16px;
        border: none;
        padding: 14px 16px;
        background: #ffffff;
        box-shadow: 0 8px 16px rgba(255, 182, 197, 0.16);
        margin-top: 8px;
        margin-bottom: 10px;
    }
    .student-card h4 {
        margin: 0 0 6px 0;
        color: #2c3e50;
        font-size: 16px;
    }
    .student-card p {
        margin: 4px 0;
        color: #34495e;
        font-size: 14px;
    }
    .section-title {
        font-size: 0.75rem;
        font-weight: 700;
        color: #2c3e50;
        margin-bottom: 8px;
    }
    .mobile-menu-label {
        font-size: 0.9rem;
        font-weight: 700;
        color: #2c3e50;
        margin-bottom: 4px;
    }
    .list-card {
        border-radius: 18px;
        border: none;
        padding: 14px 14px;
        background: #ffffff;
        box-shadow: 0 8px 16px rgba(255, 182, 197, 0.12);
        margin-bottom: 10px;
        border-left: 6px solid #d3d3d3;
    }
    .status-pink { border-left-color: #FF69B4 !important; }
    .status-blue { border-left-color: #87CEEB !important; }
    .status-gray { border-left-color: #D3D3D3 !important; }
    .list-card .header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 10px;
    }
    .list-card .subject {
        font-weight: 800;
        color: #1f2d3d;
        margin-bottom: 4px;
        font-size: 1rem;
    }
    .list-card .badge {
        color: #fff;
        border-radius: 999px;
        padding: 2px 10px;
        font-size: 0.72rem;
        font-weight: 700;
        white-space: nowrap;
    }
    .list-card .meta {
        font-size: 0.84rem;
        color: #4b5563;
        margin: 2px 0;
    }
    </style>
    """,
    unsafe_allow_html=True
)

today_header = datetime.now().strftime("%Y년 %m월 %d일")
st.markdown(
    f"<div class='main-header'><h1>🌸 3-1반 수행평가 비서</h1><p>{today_header} 오늘도 화이팅!</p></div>",
    unsafe_allow_html=True
)

# ----------------- 데이터 로딩 로직 -----------------
@st.cache_data(ttl=60)
def load_data_from_csv_url():
    if os.path.exists(URL_FILE):
        with open(URL_FILE, "r", encoding="utf-8") as f:
            url = f.read().strip()
        if url:
            try:
                if "/pubhtml" in url:
                    url = url.replace("/pubhtml", "/pub?output=csv")
                elif "/pub" in url and "output=csv" not in url:
                    url = url.split("?")[0] + "?output=csv"
                elif "/edit" in url:
                    # 공유된 편집 URL도 게시 CSV URL로 최대한 자동 변환
                    url = url.split("/edit")[0] + "/pub?output=csv"
                    
                df_raw = pd.read_csv(url)
                if df_raw.empty or "과목명" not in df_raw.columns:
                    return pd.DataFrame() 
                return df_raw
            except Exception:
                st.error("⚠️ 설정 주소를 다시 확인해주세요.")
                return None
    return None

df_raw = load_data_from_csv_url()
today = datetime.now().date()
today_str = today.strftime("%Y-%m-%d")

# ----------------- 한국어 날짜 스마트 파싱 함수 -----------------
def parse_date_flexibly(date_string):
    if pd.isna(date_string) or not str(date_string).strip():
        return None
    s = str(date_string).strip()
    # 예: "3월 25일" -> "3-25"
    s = s.replace("월", "-").replace("일", "").replace(" ", "")
    # 예: "2026.03.25" -> "2026-03-25"
    s = s.replace(".", "-").replace("/", "-")
    
    parts = [p for p in s.split("-") if p] # 양끝 공백이나 빈 항목 제거
    
    if len(parts) == 2:
        # 연도 없이 "3-25"만 썼다면 무조건 올해로 강제 연결
        s = f"{today.year}-{int(parts[0]):02d}-{int(parts[1]):02d}"
    try:
        # pandas가 아주 너그럽게 날짜 변환해 줌
        return pd.to_datetime(s).date()
    except:
        return None


def parse_date_range_flexibly(date_string):
    """'4월1일~4월7일' 같은 기간 문자열도 (시작일, 종료일)로 변환."""
    if pd.isna(date_string) or not str(date_string).strip():
        return None, None

    raw = str(date_string).strip()
    parts = re.split(r"\s*[~\-–—]\s*", raw)
    parts = [p.strip() for p in parts if p.strip()]

    if len(parts) >= 2:
        start = parse_date_flexibly(parts[0])
        end = parse_date_flexibly(parts[1])
        if start and end:
            if end < start:
                end = start
            return start, end

    single = parse_date_flexibly(raw)
    if single:
        return single, single
    return None, None


def extract_event_click_payload(calendar_state):
    """streamlit_calendar 버전에 따라 다른 반환 형태를 통합 처리."""
    if not isinstance(calendar_state, dict):
        return None

    # 형태 A: {"callback":"eventClick", "event": {...}}
    if calendar_state.get("callback") == "eventClick":
        event_obj = calendar_state.get("event")
        if isinstance(event_obj, dict):
            return event_obj
        # callback만 있고 event가 중첩 구조인 경우는 아래 분기에서 계속 탐색

    # 형태 B: {"eventClick": {"event": {...}}} 또는 {"eventClick": {...}}
    event_click_obj = calendar_state.get("eventClick")
    if isinstance(event_click_obj, dict):
        nested = event_click_obj.get("event")
        if isinstance(nested, dict):
            return nested
        return event_click_obj

    # 형태 C: {"event": {...}} (콜백 단일 사용 시)
    event_obj = calendar_state.get("event")
    if isinstance(event_obj, dict):
        return event_obj

    # 형태 D: 중첩 구조에서 event 객체 탐색
    def _search_event(obj):
        if isinstance(obj, dict):
            # event-like object 판단
            if any(k in obj for k in ["title", "start", "startStr", "extendedProps", "id"]):
                if "title" in obj or "extendedProps" in obj:
                    return obj
            for v in obj.values():
                found = _search_event(v)
                if found:
                    return found
        elif isinstance(obj, list):
            for v in obj:
                found = _search_event(v)
                if found:
                    return found
        return None

    return _search_event(calendar_state)


def normalize_calendar_event(event_info):
    """streamlit_calendar event payload를 공통 구조로 정규화."""
    if not isinstance(event_info, dict):
        return {"id": "", "title": "", "start": "", "extendedProps": {}}

    # event가 한 단계 더 중첩된 형태 대응
    evt = event_info.get("event") if isinstance(event_info.get("event"), dict) else event_info
    evt_def = evt.get("_def", {}) if isinstance(evt.get("_def", {}), dict) else {}
    evt_inst = evt.get("_instance", {}) if isinstance(evt.get("_instance", {}), dict) else {}
    evt_range = evt_inst.get("range", {}) if isinstance(evt_inst.get("range", {}), dict) else {}

    event_id = str(evt.get("id") or evt.get("publicId") or evt_def.get("publicId") or "").strip()
    title = str(evt.get("title") or evt_def.get("title") or "").strip()
    start = (
        str(evt.get("startStr") or "").strip()
        or str(evt.get("start") or "").strip()
        or str(evt_range.get("start") or "").strip()
    )
    if "T" in start:
        start = start.split("T")[0]

    extended_props = evt.get("extendedProps")
    if not isinstance(extended_props, dict):
        extended_props = evt_def.get("extendedProps", {})
    if not isinstance(extended_props, dict):
        extended_props = {}

    return {
        "id": event_id,
        "title": title,
        "start": start,
        "extendedProps": extended_props
    }


def build_detail_from_df(df_clean, start_col, clicked_subject="", clicked_date=""):
    """클릭 실패 시에도 동일한 방식으로 상세를 찾기 위한 공용 함수."""
    if not isinstance(df_clean, pd.DataFrame) or df_clean.empty:
        return None

    if clicked_subject:
        for _, src in df_clean.iterrows():
            src_subject = str(src.get("과목명", "")).strip()
            src_raw_date = str(src.get(start_col, "")).strip()
            src_start, _ = parse_date_range_flexibly(src_raw_date)
            src_date_str = src_start.strftime("%Y-%m-%d") if src_start else src_raw_date
            if src_subject == clicked_subject and (not clicked_date or src_date_str == clicked_date or src_raw_date == clicked_date):
                return {
                    "subject": src_subject,
                    "content": str(src.get("평가내용", "")).strip(),
                    "date_text": src_raw_date or src_date_str,
                    "method": str(src.get("평가방식", "")).strip() or "-",
                    "status_text": str(src.get("기한", "")).strip()
                }

    return None

# ----------------- 데이터(샘플 또는 실제) 전처리 -----------------
if df_raw is None or df_raw.empty:
    df_raw = pd.DataFrame({
        "과목명": ["국어(예시)", "영어(예시)", "수학(예시)", "과학(예시)"],
        "평가내용": ["문학작품 작성", "영어 말하기", "수학 문제풀이", "과학 실험"],
        "수행평가일": [
            (today + timedelta(days=3)).strftime("%Y-%m-%d"), 
            (today + timedelta(days=8)).strftime("%Y-%m-%d"),
            (today + timedelta(days=15)).strftime("%Y-%m-%d"),
            (today - timedelta(days=2)).strftime("%Y-%m-%d") 
        ],
        "마감일": ["", "", "", ""],
        "평가방식": ["보고서", "발표", "지필평가", "보고서"],
        "등록일": [
            today_str, today_str, 
            (today - timedelta(days=3)).strftime("%Y-%m-%d"), 
            (today - timedelta(days=10)).strftime("%Y-%m-%d")
        ]
    })
    st.info("👆 위 표는 임시 예시 화면입니다. 관리자 탭에서 구글 시트 웹게시 링크를 연결해 주세요!")

start_col = "수행평가일" if "수행평가일" in df_raw.columns else "수행평가일(시작일)"
if start_col not in df_raw.columns:
    df_raw[start_col] = "" 

if "평가방식" not in df_raw.columns:
    df_raw["평가방식"] = ""
if "등록일" not in df_raw.columns:
    df_raw["등록일"] = today_str
if "마감일" not in df_raw.columns:
    df_raw["마감일"] = ""

df_raw = df_raw.fillna("")

no_list = []
status_list = []
events = []
valid_indices = []
display_items = []
event_detail_map = {}

for idx, row in df_raw.iterrows():
    start_date_raw = str(row.get(start_col, "")).strip()
    reg_date_raw = str(row.get("등록일", "")).strip()
    
    # 단일 날짜 + 기간형 날짜(예: 4월1일~4월7일) 모두 처리
    start_date, end_date = parse_date_range_flexibly(start_date_raw)
    if start_date is None or end_date is None:
        # 날짜를 아예 안 썼거나 아예 해석 못하면 조용히 숨겨서 전체 에러를 방지
        continue
        
    valid_indices.append(idx)
    days_to_deadline = (start_date - today).days
    start_date_str = start_date.strftime("%Y-%m-%d")
    end_date_str = end_date.strftime("%Y-%m-%d")
    
    reg_date = parse_date_flexibly(reg_date_raw)
    if reg_date is not None:
        days_since_add = (today - reg_date).days
    else:
        days_since_add = 999
        
    # N 문자열 삽입 로직 (등록일이 오늘이면 귀여운 별 ⭐️)
    if days_since_add == 0:
        no_list.append("⭐️")
    else:
        # 1, 2, 3.. 순서대로 매기기 위해 valid_indices의 길이를 사용
        no_list.append(str(len(valid_indices)))
        
    # 상태 색상 로직 적용 (수행평가일 기준으로 마감 산정)
    status_icon = "⚪ 여유/마감"
    color_hex = "#bdc3c7" # 기본 (연회색)
    text_color = "#ffffff"
    border_color = "#bdc3c7"
    
    if days_to_deadline < 0: 
        status_icon = "⚪ 마감됨"
        color_hex = "#ffffff" 
        border_color = "#dddddd"
        text_color = "#95a5a6" 
        card_class = "status-gray"
        badge_color = "#b3b3b3"
        status_badge = "종료"
    elif 0 <= days_to_deadline <= 5: 
        status_icon = "💗 임박" 
        color_hex = "#ff69b4" # 5일이내 핑크
        border_color = "#ff69b4"
        text_color = "#ffffff"
        card_class = "status-pink"
        badge_color = "#ff69b4"
        status_badge = f"D-{days_to_deadline} 🔥"
    elif 5 < days_to_deadline <= 10: 
        status_icon = "☁️ 주의" # 하늘색 구름 ☁️
        color_hex = "#87ceeb" 
        border_color = "#87ceeb"
        text_color = "#000000" 
        card_class = "status-blue"
        badge_color = "#87ceeb"
        status_badge = f"D-{days_to_deadline} ☁️"
    else:
        card_class = "status-gray"
        badge_color = "#c5c5c5"
        status_badge = f"D-{days_to_deadline} ✨"
        
    status_list.append(status_icon)
    
    subject_text = str(row.get("과목명", "")).strip()
    content_text = str(row.get("평가내용", "")).strip()
    method_text = str(row.get("평가방식", "")).strip() or "-"
    # 캘린더에는 과목명만 표시
    title_text = subject_text
    if days_to_deadline >= 0:
        dday_text = f"D-{days_to_deadline}"
    else:
        dday_text = "종료"

    status_text = status_icon
    tooltip_text = (
        f"과목: {subject_text}\n"
        f"내용: {content_text}\n"
        f"평가일: {start_date_str}\n"
        f"평가방식: {method_text}\n"
        f"상태: {status_text}"
    )
        
    events.append({
        "id": str(idx),
        "title": title_text,
        "start": start_date_str,
        "end": (end_date + timedelta(days=1)).strftime("%Y-%m-%d"),
        "backgroundColor": color_hex,
        "borderColor": border_color,
        "textColor": text_color,
        "extendedProps": {
            "tooltip": tooltip_text,
            "subject": subject_text,
            "content": content_text,
            "method": method_text,
            "status_text": status_text,
            "dday": dday_text,
            "date_text": start_date_raw or start_date_str
        }
    })

    display_items.append({
        "subject": subject_text,
        "content": content_text,
        "date_text": start_date_raw or start_date_str,
        "method": method_text,
        "status_text": status_icon,
        "badge_text": status_badge,
        "badge_color": badge_color,
        "card_class": card_class
    })

    event_detail_map[str(idx)] = {
        "subject": subject_text,
        "content": content_text,
        "date_text": start_date_raw or start_date_str,
        "method": method_text,
        "status_text": status_icon
    }

# 오류난 쓰레기 값(빈줄) 제거한 깔끔한 데이터프레임으로 교체
df_clean = df_raw.loc[valid_indices].copy()
df_clean.insert(0, "No", no_list)
df_clean["기한"] = status_list

# 열 정렬 (사용자 시트 순서 존중)
target_columns = ["No", "과목명", "평가내용", start_col, "평가방식", "기한"]
display_df = df_clean[[col for col in target_columns if col in df_clean.columns]]

# ----------------- UI 렌더링 -----------------
st.markdown('<div class="mobile-menu-label">메뉴</div>', unsafe_allow_html=True)
menu_options = ["📋 전체 목록", "📆 캘린더", "🔒 관리자"]
current_view = st.session_state.get("current_view", "📋 전체 목록")
default_index = menu_options.index(current_view) if current_view in menu_options else 0
view = st.radio(
    "화면",
    options=menu_options,
    index=default_index,
    horizontal=True,
    label_visibility="collapsed"
)
st.session_state["current_view"] = view

if view == "📋 전체 목록":
    st.markdown('<div class="section-title">📋 전체 수행평가 목록</div>', unsafe_allow_html=True)
    if display_df.empty:
        st.info("표시할 수행평가 일정이 아직 없어요.")
    else:
        imminent_count = sum(1 for item in display_items if "🔥" in item["badge_text"])
        if imminent_count > 0:
            st.warning(f"🔔 이번 주 임박한 수행평가가 **{imminent_count}개** 있어요!")

        for item in display_items:
            st.markdown(
                f"""
                <div class="list-card {item['card_class']}">
                    <div class="header">
                        <div class="subject">{item['subject']}</div>
                        <div class="badge" style="background:{item['badge_color']};">{item['badge_text']}</div>
                    </div>
                    <div class="meta">📝 내용: {item['content']}</div>
                    <div class="meta">📅 평가일: {item['date_text']}</div>
                    <div class="meta">🧪 방식: {item['method']}</div>
                    <div class="meta">⏰ 상태: {item['status_text']}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

    with st.expander("표 형태로 보기"):
        st.dataframe(display_df, width="stretch", hide_index=True)

elif view == "📆 캘린더":
    st.markdown('<div class="section-title">📆 캘린더 대시보드</div>', unsafe_allow_html=True)

    calendar_css = """
        .fc-toolbar-title {
            font-size: 1.05em !important;
            font-weight: 700 !important;
        }
        .fc-button {
            font-size: 0.78em !important;
            padding: 0.35em 0.65em !important;
            height: auto !important;
            border-radius: 8px !important;
            border: none !important;
            outline: none !important;
            box-shadow: none !important;
        }
        .fc-button:focus,
        .fc-button:active,
        .fc-button-primary:focus,
        .fc-button-primary:active {
            outline: none !important;
            box-shadow: none !important;
        }
        .fc-col-header-cell-cushion {
            font-size: 0.9em !important;
            font-weight: 700;
        }
        .fc-daygrid-day-number {
            font-size: 0.9em !important;
            font-weight: 600;
        }
        .fc-event-title.fc-sticky {
            font-weight: 700;
            padding: 4px 7px;
            font-size: 1.02em;
            line-height: 1.35 !important;
            white-space: normal !important;
            word-break: keep-all !important;
            overflow: visible !important;
            text-overflow: unset !important;
        }
        .fc-daygrid-dot-event .fc-event-title {
            white-space: normal !important;
            overflow: visible !important;
            text-overflow: unset !important;
        }
        .fc-event {
            border-radius: 9px;
            border-style: solid;
            box-shadow: 0 2px 6px rgba(44, 62, 80, 0.1);
            cursor: pointer;
        }
    """

    calendar_options = {
        "headerToolbar": {
            "left": "today prev,next",
            "center": "title",
            "right": "dayGridMonth,listWeek"
        },
        "initialView": "dayGridMonth",
        "height": 560,
        "dayMaxEventRows": 3,
        "eventDisplay": "block"
    }
    calendar_state = calendar(
        events=events,
        options=calendar_options,
        custom_css=calendar_css,
        key="main_calendar"
    )

    event_info = extract_event_click_payload(calendar_state)
    if isinstance(event_info, dict):
        normalized = normalize_calendar_event(event_info)
        props = normalized.get("extendedProps", {})
        clicked_id = normalized.get("id", "")
        clicked_subject = (props.get("subject") or normalized.get("title") or "").strip()
        clicked_date = (
            props.get("date_text")
            or normalized.get("start", "")
        )

        selected_detail = None

        # 1) 이벤트 id로 바로 매칭 (가장 정확)
        if clicked_id in event_detail_map:
            selected_detail = event_detail_map[clicked_id]

        # 2) id가 없거나 매칭 실패 시, 과목+날짜 -> 과목 순으로 재검색
        if selected_detail is None:
            selected_detail = build_detail_from_df(df_clean, start_col, clicked_subject, clicked_date)
        if selected_detail is None:
            selected_detail = build_detail_from_df(df_clean, start_col, clicked_subject, "")

        # 4) 마지막 fallback: 캘린더 props 표시
        if selected_detail is None:
            selected_detail = {
                "subject": clicked_subject,
                "content": props.get("content", ""),
                "date_text": clicked_date,
                "method": props.get("method", ""),
                "status_text": props.get("status_text", "")
            }

        # 빈 상세로 덮어쓰는 상황 방지
        if any(str(selected_detail.get(k, "")).strip() for k in ["subject", "content", "date_text", "method", "status_text"]):
            st.session_state["selected_event_detail"] = selected_detail

    selected = st.session_state.get("selected_event_detail")
    if selected:
        st.markdown(
            f"""
            <div class="student-card">
                <h4>🔎 선택한 일정 상세</h4>
                <p><b>과목:</b> {selected.get('subject','')}</p>
                <p><b>내용:</b> {selected.get('content','')}</p>
                <p><b>평가일:</b> {selected.get('date_text','')}</p>
                <p><b>평가방식:</b> {selected.get('method','')}</p>
                <p><b>상태:</b> {selected.get('status_text','')}</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.info("캘린더 날짜 칸의 과목명을 클릭하면 아래에 상세 배너가 표시됩니다.")

    st.caption("🔔 상태 요약: 💗 5일내 임박(핑크) | ☁️ 5~10일내(구름) | ⚪ 여유/마감됨(하양)")

else:
    st.markdown("#### 🔒 관리자 전용 설정")
    st.caption("학생 배포 화면에서는 이 탭을 열어도 설정을 볼 수 없습니다. 비밀번호 입력 시에만 활성화됩니다.")

    if not st.session_state["admin_unlocked"]:
        admin_input = st.text_input("관리자 비밀번호", type="password", placeholder="관리자만 알고 있는 비밀번호")
        if st.button("관리자 모드 열기"):
            if admin_input == ADMIN_PASSWORD:
                st.session_state["admin_unlocked"] = True
                st.success("관리자 모드가 열렸습니다.")
                st.rerun()
            else:
                st.error("비밀번호가 올바르지 않습니다.")
    else:
        st.success("관리자 모드 활성화됨")
        new_url = st.text_input("CSV 웹 주소를 붙여넣기(Ctrl+V)", value=saved_url)

        if st.button("💾 주소 저장 및 구글시트 연동하기"):
            if new_url.startswith("https://docs.google.com/"):
                with open(URL_FILE, "w", encoding="utf-8") as f:
                    f.write(new_url.strip())
                st.success("✅ 구글 시트가 성공적으로 연결되었습니다!")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error("⚠️ 올바른 연동 주소가 아닙니다.")

        if saved_url:
            edit_url = saved_url.split("/pub?")[0] + "/edit"
            st.markdown(f"[👉 **우리반 구글 시트(원본) 가기**]({edit_url})")

        st.markdown("---")
        st.markdown("##### 📂 파일 업로드 (엑셀/이미지)")
        uploaded_files = st.file_uploader(
            "엑셀(xlsx, xls) 또는 이미지(png, jpg, jpeg)를 업로드하세요.",
            type=["xlsx", "xls", "png", "jpg", "jpeg"],
            accept_multiple_files=True
        )

        if uploaded_files:
            os.makedirs(UPLOAD_DIR, exist_ok=True)
            for file in uploaded_files:
                save_path = os.path.join(UPLOAD_DIR, file.name)
                with open(save_path, "wb") as f:
                    f.write(file.getbuffer())

                st.success(f"업로드 완료: {file.name}")
                if file.name.lower().endswith((".png", ".jpg", ".jpeg")):
                    st.image(save_path, caption=file.name, use_container_width=True)
                elif file.name.lower().endswith((".xlsx", ".xls")):
                    try:
                        preview_df = pd.read_excel(save_path)
                        st.write(f"미리보기: {file.name}")
                        st.dataframe(preview_df.head(20), width="stretch", hide_index=True)
                    except Exception:
                        st.warning(f"{file.name} 미리보기를 불러오지 못했습니다.")

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("🔄 수동 새로 고침"):
                st.cache_data.clear()
                st.rerun()
        with col_b:
            if st.button("🔒 관리자 모드 닫기"):
                st.session_state["admin_unlocked"] = False
                st.rerun()
