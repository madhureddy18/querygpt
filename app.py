# app.py

import streamlit as st
import api_client

# ── Page config ───────────────────────────────────────────────
st.set_page_config(
    page_title="QueryGPT",
    page_icon="✦",
    layout="centered"
)

# ── CSS ───────────────────────────────────────────────────────
st.markdown("""
<style>
html, body, .stApp { background:#0d0d0d; color:#f0f0f0; font-family:'Inter',sans-serif; }
header[data-testid="stHeader"] { display: none !important; }
#MainMenu { display: none !important; }
footer { display: none !important; }
.stDeployButton { display: none !important; }

.block-container {
    padding-top: 16px !important;
    max-width: 720px;
}

/* Header */
.qgpt-header {
    display:flex; align-items:center; gap:10px;
    padding-bottom:12px; border-bottom:1px solid #1f1f1f;
    margin-bottom:20px;
}
.qgpt-title { font-size:20px; font-weight:700; color:#fff; }
.qgpt-badge {
    background:#1a1a1a; border:1px solid #333; color:#4ae24a;
    font-size:11px; padding:2px 8px; border-radius:20px; font-weight:600;
}

/* Pro tip */
.pro-tip {
    background:#111d11; border-left:3px solid #4ae24a;
    border-radius:6px; padding:10px 14px;
    font-size:12px; color:#888; margin-bottom:16px;
}

/* Workspace panel */
.ws-panel {
    background:#111; border:1px solid #222;
    border-radius:12px; padding:20px;
    margin-bottom:16px;
}
.ws-section-label {
    font-size:11px; font-weight:700; color:#555;
    letter-spacing:1px; text-transform:uppercase;
    margin:12px 0 8px 0;
}
.ws-card {
    background:#161616; border:1px solid #222;
    border-radius:10px; padding:14px 16px;
    margin-bottom:8px;
}
.ws-card:hover { border-color:#4a90e2; }
.ws-card-selected { border-color:#4a90e2 !important; background:#0d1a2e; }
.ws-card-none {
    background:#111; border:1px dashed #333;
    border-radius:10px; padding:12px 16px;
    margin-bottom:8px;
}
.ws-name { font-size:14px; font-weight:600; color:#fff; margin:4px 0; }
.ws-desc { font-size:12px; color:#666; margin:0; }
.badge-system {
    background:#0d2040; color:#4a90e2;
    font-size:10px; padding:1px 8px; border-radius:20px; font-weight:700;
}
.badge-custom {
    background:#200d40; color:#a04ae2;
    font-size:10px; padding:1px 8px; border-radius:20px; font-weight:700;
}
.badge-none {
    background:#1a1a1a; color:#666;
    font-size:10px; padding:1px 8px; border-radius:20px; font-weight:700;
}

/* Chat bubbles */
.bubble-bot {
    background:#161616; border:1px solid #222;
    border-radius:0 12px 12px 12px;
    padding:12px 16px; font-size:13px; color:#ccc;
    margin:8px 0; max-width:90%;
}
.bubble-user {
    background:#1a2a4a; border:1px solid #2a3a6a;
    border-radius:12px 0 12px 12px;
    padding:12px 16px; font-size:13px; color:#fff;
    margin:8px 0 8px auto; max-width:90%; text-align:right;
}

/* Table confirmation box */
.table-box {
    background:#111; border:2px solid #4a90e2;
    border-radius:10px; padding:16px;
    margin:12px 0;
}
.table-box-title {
    font-size:12px; font-weight:700; color:#4a90e2;
    margin-bottom:12px; letter-spacing:0.5px;
}
.table-row {
    display:flex; justify-content:space-between;
    align-items:center; padding:8px 0;
    border-bottom:1px solid #1f1f1f; font-size:13px; color:#ddd;
}

/* Result meta tags */
.meta-tag {
    display:inline-block;
    padding:2px 10px; border-radius:20px;
    font-size:11px; font-weight:600;
    margin-right:6px; margin-bottom:8px;
}
.meta-intent  { background:#0d2010; color:#4ae24a; }
.meta-valid   { background:#0d2010; color:#4ae24a; }
.meta-invalid { background:#2d0d0d; color:#e24a4a; }
.meta-rows    { background:#1a1a2e; color:#4a90e2; }
.meta-latency { background:#1a1a1a; color:#888; }
.meta-fixed   { background:#2d1a00; color:#e2a44a; }

/* Explanation box */
.explanation-box {
    background:#0d1a0d; border:1px solid #1a3a1a;
    border-radius:8px; padding:12px 16px;
    font-size:12px; color:#888;
    margin-top:12px;
}

/* Preview table */
.preview-box {
    background:#111; border:1px solid #222;
    border-radius:8px; padding:12px;
    margin-top:12px; overflow-x:auto;
}
.preview-title {
    font-size:11px; font-weight:700; color:#555;
    letter-spacing:1px; text-transform:uppercase;
    margin-bottom:8px;
}

/* Validation issues */
.issue-box {
    background:#1a0d0d; border:1px solid #3a1a1a;
    border-radius:8px; padding:12px 16px;
    font-size:12px; color:#e24a4a;
    margin-top:8px;
}

/* Looks good button */
.stButton button[kind="primary"] {
    background:#1a1a1a; border:1px solid #4a90e2;
    color:#4a90e2; border-radius:20px;
    padding:8px 24px; font-weight:600;
}
</style>
""", unsafe_allow_html=True)


# ── Session state ─────────────────────────────────────────────
def init():
    defaults = {
        "step":               "question",
        "show_workspaces":    False,
        "show_create_form":   False,
        "selected_workspace": None,
        "question":           "",
        "enhanced_question":  "",
        "intent":             "",
        "suggested_tables":   [],
        "pipeline_result":    None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init()


# ══════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════
col1, col2, col3 = st.columns([3, 2, 1])
with col1:
    st.markdown("""
        <div class='qgpt-header'>
            <span class='qgpt-title'>✦ QueryGPT</span>
            <span class='qgpt-badge'>Beta</span>
        </div>
    """, unsafe_allow_html=True)
with col2:
    if st.session_state["selected_workspace"]:
        btn_label = f"🗂 {st.session_state['selected_workspace']}"
    else:
        btn_label = "🗂 Workspaces · None"

    if st.button(btn_label, key="ws_toggle"):
        st.session_state["show_workspaces"] = not st.session_state["show_workspaces"]
        st.rerun()

with col3:
    if st.session_state["selected_workspace"]:
        if st.button("✕", key="clear_ws", help="Clear selected workspace"):
            st.session_state["selected_workspace"] = None
            st.session_state["show_workspaces"]    = False
            st.session_state["step"]               = "question"
            st.session_state["pipeline_result"]    = None
            st.session_state["suggested_tables"]   = []
            st.rerun()


# ══════════════════════════════════════════════════════════════
# WORKSPACE PANEL
# ══════════════════════════════════════════════════════════════
if st.session_state["show_workspaces"]:

    ws_resp    = api_client.get_all_workspaces()
    workspaces = ws_resp.get("workspaces", []) if "error" not in ws_resp else []

    if "error" in ws_resp:
        st.error(f"⚠️ Could not load workspaces: {ws_resp['error']}")

    system_ws = [w for w in workspaces if w["workspace_type"] == "system"]
    custom_ws = [w for w in workspaces if w["workspace_type"] == "custom"]

    st.markdown("<div class='ws-panel'>", unsafe_allow_html=True)

    search = st.text_input(
        "", placeholder="🔍  Search workspaces...",
        key="ws_search", label_visibility="collapsed"
    )
    query = search.lower().strip()

    # ── No Workspace ──────────────────────────────────────────
    st.markdown("<div class='ws-section-label'>General</div>", unsafe_allow_html=True)
    is_none_selected = st.session_state["selected_workspace"] is None
    none_class = "ws-card-selected" if is_none_selected else ""
    st.markdown(f"""
        <div class='ws-card-none {none_class}'>
            <span class='badge-none'>NO FILTER</span>
            <div class='ws-name'>🌐 No Workspace</div>
            <div class='ws-desc'>
                Ask freely across all tables with no domain restriction.
                Intent agent classifies your question automatically.
            </div>
        </div>
    """, unsafe_allow_html=True)

    if st.button(
        "✓ Already selected" if is_none_selected else "Select →",
        key="sel_none", disabled=is_none_selected
    ):
        st.session_state["selected_workspace"] = None
        st.session_state["show_workspaces"]    = False
        st.session_state["step"]               = "question"
        st.session_state["pipeline_result"]    = None
        st.session_state["suggested_tables"]   = []
        st.rerun()

    # ── System workspaces ─────────────────────────────────────
    st.markdown("<div class='ws-section-label'>System Workspaces</div>", unsafe_allow_html=True)

    filtered_sys = [
        w for w in system_ws
        if query in w["name"].lower() or query in w["description"].lower()
    ] if query else system_ws

    for ws in filtered_sys:
        is_sel     = st.session_state["selected_workspace"] == ws["name"]
        card_class = "ws-card ws-card-selected" if is_sel else "ws-card"
        st.markdown(f"""
            <div class='{card_class}'>
                <span class='badge-system'>SYSTEM</span>
                <div class='ws-name'>{ws['name']}</div>
                <div class='ws-desc'>{ws['description']}</div>
            </div>
        """, unsafe_allow_html=True)

        if st.button(
            "✓ Selected" if is_sel else "Select →",
            key=f"sel_{ws['name']}", disabled=is_sel
        ):
            st.session_state["selected_workspace"] = ws["name"]
            st.session_state["show_workspaces"]    = False
            st.session_state["step"]               = "question"
            st.session_state["pipeline_result"]    = None
            st.session_state["suggested_tables"]   = []
            st.rerun()

    # ── Custom workspaces ─────────────────────────────────────
    st.markdown("<div class='ws-section-label'>Custom Workspaces</div>", unsafe_allow_html=True)

    filtered_cust = [
        w for w in custom_ws
        if query in w["name"].lower() or query in w["description"].lower()
    ] if query else custom_ws

    if filtered_cust:
        for ws in filtered_cust:
            is_sel     = st.session_state["selected_workspace"] == ws["name"]
            card_class = "ws-card ws-card-selected" if is_sel else "ws-card"
            st.markdown(f"""
                <div class='{card_class}'>
                    <span class='badge-custom'>CUSTOM</span>
                    <div class='ws-name'>{ws['name']}</div>
                    <div class='ws-desc'>{ws['description']}</div>
                </div>
            """, unsafe_allow_html=True)
            c1, c2 = st.columns([3, 1])
            with c1:
                if st.button(
                    "✓ Selected" if is_sel else "Select →",
                    key=f"sel_c_{ws['name']}", disabled=is_sel
                ):
                    st.session_state["selected_workspace"] = ws["name"]
                    st.session_state["show_workspaces"]    = False
                    st.session_state["step"]               = "question"
                    st.session_state["pipeline_result"]    = None
                    st.session_state["suggested_tables"]   = []
                    st.rerun()
            with c2:
                if st.button("🗑", key=f"del_{ws['name']}"):
                    del_res = api_client.delete_workspace(ws["name"])
                    if "error" in del_res:
                        st.error(del_res["error"])
                    else:
                        if st.session_state["selected_workspace"] == ws["name"]:
                            st.session_state["selected_workspace"] = None
                        st.rerun()
    else:
        st.markdown(
            "<p style='color:#555; font-size:13px'>No custom workspaces yet.</p>",
            unsafe_allow_html=True
        )

    # ── Create custom workspace ───────────────────────────────
    st.divider()
    if st.button("➕ Create Custom Workspace", key="show_create"):
        st.session_state["show_create_form"] = not st.session_state["show_create_form"]

    if st.session_state["show_create_form"]:
        with st.form("create_ws_form"):
            st.markdown("**New Custom Workspace**")
            new_name = st.text_input("Name")
            new_desc = st.text_area("Description", height=70)

            tables_resp = api_client.list_all_tables()
            all_tables  = [t["full_name"] for t in tables_resp.get("tables", [])] if "error" not in tables_resp else []

            sel_tables = st.multiselect("Tables", options=all_tables)

            if st.form_submit_button("Create"):
                if not new_name or not sel_tables:
                    st.error("Name and at least one table required.")
                else:
                    res = api_client.create_workspace(
                        name=new_name,
                        description=new_desc,
                        tables=sel_tables,
                    )
                    if "error" in res:
                        st.error(f"⚠️ {res['error']}")
                    else:
                        st.success(f"'{new_name}' created.")
                        st.session_state["show_create_form"] = False
                        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

    if st.button("✕ Close Panel", key="close_ws"):
        st.session_state["show_workspaces"] = False
        st.rerun()


# ══════════════════════════════════════════════════════════════
# MAIN CHAT AREA
# ══════════════════════════════════════════════════════════════
else:

    st.markdown("""
        <div class='pro-tip'>
        💡 <b>Pro Tip</b> — If your use case is specific,
        consider creating a Custom Workspace to improve accuracy.
        </div>
    """, unsafe_allow_html=True)

    ws_name = st.session_state["selected_workspace"]
    st.markdown(f"""
        <div class='bubble-bot'>
        Hey! Ask me a question about your NYC taxi data and I'll generate a SQL query for you.
        {'&nbsp;&nbsp;🗂 <b>' + ws_name + '</b>' if ws_name else '&nbsp;&nbsp;<span style="color:#555">No workspace selected</span>'}
        </div>
    """, unsafe_allow_html=True)


    # ── STEP: QUESTION ────────────────────────────────────────
    if st.session_state["step"] == "question":

        question = st.text_area(
            "", placeholder="Ask a question about your data...",
            height=80, label_visibility="collapsed", key="q_input"
        )

        if st.button("Submit ➤", type="primary"):
            if not question.strip():
                st.warning("Please enter a question.")
            else:
                st.session_state["question"] = question.strip()

                with st.spinner("Finding relevant tables..."):
                    result = api_client.suggest_tables(
                        question=question.strip(),
                        workspace_name=st.session_state["selected_workspace"],
                    )

                if result.get("error"):
                    st.error(f"⚠️ {result['error']}")
                else:
                    st.session_state["suggested_tables"]  = result.get("suggested_tables", [])
                    st.session_state["enhanced_question"] = result.get("enhanced_question", question.strip())
                    st.session_state["intent"]            = result.get("intent", "")
                    st.session_state["step"]              = "tables"
                    st.rerun()


    # ── STEP: TABLE CONFIRMATION ──────────────────────────────
    elif st.session_state["step"] == "tables":

        st.markdown(
            f"<div class='bubble-user'>{st.session_state['question']}</div>",
            unsafe_allow_html=True
        )
        st.markdown(
            "<div class='bubble-bot'>I'm planning to use the tables below "
            "to generate the query</div>",
            unsafe_allow_html=True
        )

        st.markdown("<div class='table-box'>", unsafe_allow_html=True)
        st.markdown(
            "<div class='table-box-title'>TABLES TO BE USED:</div>",
            unsafe_allow_html=True
        )

        table_search = st.text_input(
            "", placeholder="🔍  Table name",
            key="table_search", label_visibility="collapsed"
        )

        for i, table in enumerate(st.session_state["suggested_tables"]):
            if table_search.lower() in table.lower() or not table_search:
                c1, c2 = st.columns([6, 1])
                with c1:
                    st.markdown(
                        f"<div class='table-row'>{table}</div>",
                        unsafe_allow_html=True
                    )
                with c2:
                    if st.button("✕", key=f"rm_{i}"):
                        st.session_state["suggested_tables"].remove(table)
                        st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

        # ── Add more tables dropdown ──────────────────────────
        tables_resp = api_client.list_all_tables()
        if "error" not in tables_resp:
            all_table_names = [t["full_name"] for t in tables_resp.get("tables", [])]
            remaining = [t for t in all_table_names if t not in st.session_state["suggested_tables"]]
        else:
            remaining = []

        if remaining:
            extra = st.multiselect(
                "", options=remaining,
                label_visibility="collapsed",
                placeholder="+ Add table..."
            )
            if extra:
                for t in extra:
                    if t not in st.session_state["suggested_tables"]:
                        st.session_state["suggested_tables"].append(t)
                        st.rerun()

        c1, c2 = st.columns([2, 3])
        with c1:
            if st.button("✅  Looks Good", type="primary"):
                if not st.session_state["suggested_tables"]:
                    st.error("Please select at least one table.")
                else:
                    st.session_state["step"] = "result"
                    st.rerun()
        with c2:
            if st.button("← Edit Question"):
                st.session_state["step"] = "question"
                st.rerun()


    # ── STEP: SQL RESULT ──────────────────────────────────────
    elif st.session_state["step"] == "result":

        st.markdown(
            f"<div class='bubble-user'>{st.session_state['question']}</div>",
            unsafe_allow_html=True
        )
        st.markdown(
            "<div class='bubble-bot'>Here's the SQL query I generated:</div>",
            unsafe_allow_html=True
        )

        if st.session_state["pipeline_result"] is None:
            with st.spinner("Generating SQL... this may take up to 30 seconds"):
                result = api_client.generate_sql(
                    question=st.session_state["question"],
                    confirmed_tables=st.session_state["suggested_tables"],
                    workspace_name=st.session_state["selected_workspace"],
                )

            if result.get("error"):
                st.error(f"⚠️ {result['error']}")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("← Back to Tables"):
                        st.session_state["step"] = "tables"
                        st.rerun()
                with c2:
                    if st.button("🔄 New Question"):
                        st.session_state["step"]            = "question"
                        st.session_state["pipeline_result"] = None
                        st.session_state["suggested_tables"] = []
                        st.rerun()
                st.stop()

            st.session_state["pipeline_result"] = result

        result = st.session_state["pipeline_result"]

        if result.get("error"):
            st.error(result["error"])

        else:
            # ── Enhanced question (if different from original) ─
            enhanced = result.get("enhanced_question", "")
            original = result.get("question", "")
            if enhanced and enhanced.lower() != original.lower():
                st.markdown(f"""
                    <div style='font-size:11px; color:#555; margin-bottom:8px;'>
                    ✨ Enhanced: <span style='color:#888'>{enhanced}</span>
                    </div>
                """, unsafe_allow_html=True)

            # ── Meta tags ──────────────────────────────────────
            validated = result.get("validated", False)
            issues    = result.get("validation_issues", [])
            latency   = result.get("latency_ms", 0)
            fixed     = len(issues) > 0 and validated

            valid_class = "meta-valid"   if validated else "meta-invalid"
            valid_label = "✓ Valid"      if validated else "✗ Invalid"
            fixed_tag   = "<span class='meta-tag meta-fixed'>🔧 Auto-fixed</span>" if fixed else ""

            st.markdown(f"""
                <div style='margin-bottom:10px;'>
                    <span class='meta-tag meta-intent'>🎯 {result.get('intent','')}</span>
                    <span class='meta-tag {valid_class}'>{valid_label}</span>
                    <span class='meta-tag meta-latency'>⚡ {latency}ms</span>
                    {fixed_tag}
                </div>
            """, unsafe_allow_html=True)

            # ── Validation issues ──────────────────────────────
            if issues and not validated:
                issues_html = "".join(f"<div>• {i}</div>" for i in issues)
                st.markdown(f"""
                    <div class='issue-box'>
                    ⚠️ <b>Validation issues found:</b><br>{issues_html}
                    </div>
                """, unsafe_allow_html=True)

            # ── SQL ────────────────────────────────────────────
            st.code(result["sql"], language="sql")

            # ── Tables used ────────────────────────────────────
            st.markdown(
                "<p style='font-size:11px; color:#555; margin-top:4px;'>"
                "Tables used: " + " · ".join(result.get("tables", [])) + "</p>",
                unsafe_allow_html=True
            )

            # ── Explanation ────────────────────────────────────
            if result.get("explanation"):
                st.markdown(f"""
                    <div class='explanation-box'>
                    💬 <b>What this query does:</b><br><br>
                    {result['explanation']}
                    </div>
                """, unsafe_allow_html=True)

        st.divider()

        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔄 New Question"):
                st.session_state["step"]             = "question"
                st.session_state["pipeline_result"]  = None
                st.session_state["suggested_tables"] = []
                st.rerun()
        with c2:
            if st.button("🗂 Change Workspace"):
                st.session_state["show_workspaces"]  = True
                st.session_state["pipeline_result"]  = None
                st.session_state["suggested_tables"] = []
                st.rerun()
