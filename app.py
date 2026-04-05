import streamlit as st
import json
import random
import numpy as np
import os
import streamlit.components.v1 as stc

st.set_page_config(page_title="Object Mover", layout="wide")

# ── minimal chrome ──────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&display=swap');
  html, body, [class*="css"] { font-family: 'JetBrains Mono', monospace; background: #f5f5f5; color: #1a1a1a; }
  .stApp { background: #f5f5f5; }
  div[data-testid="stVerticalBlock"] > div { gap: 0.4rem; }
  .block-container { padding: 1.5rem 2rem; }
  h1 { font-size: 1.1rem; letter-spacing: 0.15em; color: #666; font-weight: 400; margin-bottom: 1.5rem; }
  label, .stSlider label, .stNumberInput label { font-size: 0.72rem !important; letter-spacing: 0.12em; color: #888 !important; text-transform: uppercase; }
  .stButton > button {
    background: #efefef; border: 1px solid #ccc; color: #333;
    font-family: 'JetBrains Mono', monospace; font-size: 0.72rem;
    letter-spacing: 0.1em; padding: 0.4rem 1.2rem; border-radius: 2px;
    width: 100%; transition: all 0.15s;
  }
  .stButton > button:hover { background: #e0e0e0; border-color: #aaa; color: #111; }
  .metric-box {
    background: #fff; border: 1px solid #ddd; border-radius: 2px;
    padding: 0.6rem 0.8rem; margin-bottom: 0.4rem;
  }
  .metric-label { font-size: 0.65rem; color: #999; letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 0.25rem; }
  .metric-value { font-size: 0.95rem; color: #1a1a1a; letter-spacing: 0.05em; }
  hr { border-color: #e0e0e0; margin: 1rem 0; }
  .tool-btn {
    display: inline-flex; align-items: center; justify-content: center;
    width: 36px; height: 36px; background: #efefef; border: 1px solid #ccc;
    border-radius: 3px; cursor: pointer; font-size: 1rem; margin-right: 6px;
    transition: all 0.15s; user-select: none;
  }
  .tool-btn.active { background: #e0e0e0; border-color: #888; box-shadow: 0 0 0 1px #bbb; }
  .section-title { font-size: 0.65rem; color: #999; letter-spacing: 0.15em; text-transform: uppercase; margin-bottom: 0.6rem; margin-top: 1rem; }
</style>
""", unsafe_allow_html=True)

st.markdown("<h1>OBJECT MOVER / SIMULATION INTERFACE</h1>", unsafe_allow_html=True)

# ── Bidirectional canvas component ───────────────────────────────────────────
_canvas = stc.declare_component(
    "simulator_canvas",
    path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "canvas_component"),
)

left_col, right_col = st.columns([3, 2], gap="large")

# ── RIGHT CONTROLS ────────────────────────────────────────────────────────────
with right_col:
    st.markdown('<div class="section-title">Seed Controls</div>', unsafe_allow_html=True)
    seed_objects = st.slider("Seed Objects", min_value=1, max_value=30, value=1, key="seed_slider")
    seed_btn = st.button("⬡  SEED", key="seed_btn")

    st.markdown('<div class="section-title">Actions</div>', unsafe_allow_html=True)
    action1 = st.slider("Action 1", min_value=10, max_value=90, value=50, key="action1")
    action2 = st.slider("Action 2", min_value=10, max_value=90, value=50, key="action2")

    st.markdown('<hr>', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Tracker</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="metric-box">
      <div class="metric-label">Live tracker</div>
      <div class="metric-value" style="font-size:0.75rem; color:#999;">Displayed below the canvas — updates instantly as you select and target objects.</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Future: prediction hook ──────────────────────────────────────────────
    # from prediction_utils import predict
    # if sel and tgt:
    #     state  = [sel['x'], sel['y'], tgt['x'], tgt['y']]
    #     action = [action1 / 90, action2 / 90]
    #     predicted = predict(state, action)   # returns next [x, y]

# ── LEFT CANVAS ───────────────────────────────────────────────────────────────
with left_col:

    # Session state defaults — seed 1 object on first load
    if "objects" not in st.session_state:
        rng = random.Random(1)
        margin = 15
        st.session_state.objects = [
            {"id": 0, "x": rng.randint(margin, 500 - margin), "y": rng.randint(margin, 500 - margin)}
        ]
        st.session_state.selected_id = 0
    if "tool" not in st.session_state:
        st.session_state.tool = "cross"
    if "app_mode" not in st.session_state:
        st.session_state.app_mode = "Ideal"

    # Seed button pressed → regenerate objects
    if seed_btn:
        rng = random.Random(seed_objects)
        margin = 15
        st.session_state.objects = [
            {"id": i, "x": rng.randint(margin, 500 - margin), "y": rng.randint(margin, 500 - margin)}
            for i in range(seed_objects)
        ]
        # Auto-select a random object so crosshair is immediately usable
        st.session_state.selected_id = random.randint(0, seed_objects - 1)
        st.session_state.selected_pos = None
        st.session_state.target_pos = None

    # ── Process events from the previous canvas interaction ──────────────────
    prev = st.session_state.get("canvas")
    if prev and isinstance(prev, dict):
        eid = prev.get("event_id", 0)
        if eid != st.session_state.get("_last_eid", -1):
            st.session_state._last_eid = eid
            evtype = prev.get("type")

            if evtype == "select":
                st.session_state.selected_id = prev["id"]

            elif evtype == "move":
                sel = next((o for o in st.session_state.objects if o["id"] == prev["id"]), None)
                if sel:
                    sel["x"] = prev["x"]
                    sel["y"] = prev["y"]

            elif evtype == "predict_request":
                try:
                    from prediction_utils import get_next_state
                    s = np.array([[prev["sx"], prev["sy"]]])
                    t = np.array([[prev["tx"], prev["ty"]]])
                    a = np.array([[action1, action2]])
                    mode = prev.get("mode", st.session_state.app_mode).lower()
                    ns = get_next_state(state=s, target=t, action=a, mode=mode)
                    pred_x = float(np.clip(ns[0, 0], 0, 1)) * 500
                    pred_y = float(np.clip(ns[0, 1], 0, 1)) * 500
                    sel = next((o for o in st.session_state.objects if o["id"] == prev["id"]), None)
                    if sel:
                        st.session_state.pending_animate = {
                            "id": prev["id"],
                            "from_x": sel["x"],
                            "from_y": sel["y"],
                            "to_x": pred_x,
                            "to_y": pred_y,
                            "mode": mode,
                        }
                        sel["x"] = pred_x
                        sel["y"] = pred_y
                except Exception as e:
                    st.error(f"Prediction error: {e}")

    # Consume pending_animate for this render cycle only
    pending_animate = st.session_state.pop("pending_animate", None)

    # ── Render canvas component ───────────────────────────────────────────────
    _canvas(
        objects=st.session_state.objects,
        selected_id=st.session_state.get("selected_id"),
        tool=st.session_state.get("tool", "cross"),
        mode=st.session_state.app_mode,
        pending_animate=pending_animate,
        key="canvas",
        default=None,
    )


# ── MODE TOGGLE ───────────────────────────────────────────────────────────────
st.markdown("<hr>", unsafe_allow_html=True)
_, col_toggle, _ = st.columns([1, 2, 1])
with col_toggle:
    st.markdown('<div class="section-title">Operation Mode</div>', unsafe_allow_html=True)
    st.radio(
        "Operation Mode",
        options=["Ideal", "Predictive"],
        horizontal=True,
        key="app_mode",
        label_visibility="collapsed",
    )
