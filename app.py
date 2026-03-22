import streamlit as st
import json
import random

st.set_page_config(page_title="Object Mover", layout="wide")

# ── minimal chrome ──────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&display=swap');
  html, body, [class*="css"] { font-family: 'JetBrains Mono', monospace; background: #0a0a0a; color: #e0e0e0; }
  .stApp { background: #0a0a0a; }
  div[data-testid="stVerticalBlock"] > div { gap: 0.4rem; }
  .block-container { padding: 1.5rem 2rem; }
  h1 { font-size: 1.1rem; letter-spacing: 0.15em; color: #888; font-weight: 400; margin-bottom: 1.5rem; }
  label, .stSlider label, .stNumberInput label { font-size: 0.72rem !important; letter-spacing: 0.12em; color: #666 !important; text-transform: uppercase; }
  .stButton > button {
    background: #1a1a1a; border: 1px solid #333; color: #ccc;
    font-family: 'JetBrains Mono', monospace; font-size: 0.72rem;
    letter-spacing: 0.1em; padding: 0.4rem 1.2rem; border-radius: 2px;
    width: 100%; transition: all 0.15s;
  }
  .stButton > button:hover { background: #222; border-color: #555; color: #fff; }
  .metric-box {
    background: #111; border: 1px solid #222; border-radius: 2px;
    padding: 0.6rem 0.8rem; margin-bottom: 0.4rem;
  }
  .metric-label { font-size: 0.65rem; color: #555; letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 0.25rem; }
  .metric-value { font-size: 0.95rem; color: #e0e0e0; letter-spacing: 0.05em; }
  hr { border-color: #1e1e1e; margin: 1rem 0; }
  .tool-btn {
    display: inline-flex; align-items: center; justify-content: center;
    width: 36px; height: 36px; background: #141414; border: 1px solid #2a2a2a;
    border-radius: 3px; cursor: pointer; font-size: 1rem; margin-right: 6px;
    transition: all 0.15s; user-select: none;
  }
  .tool-btn.active { background: #1f1f1f; border-color: #555; box-shadow: 0 0 0 1px #444; }
  .section-title { font-size: 0.65rem; color: #444; letter-spacing: 0.15em; text-transform: uppercase; margin-bottom: 0.6rem; margin-top: 1rem; }
</style>
""", unsafe_allow_html=True)

st.markdown("<h1>OBJECT MOVER / SIMULATION INTERFACE</h1>", unsafe_allow_html=True)

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

    # Read tracker state from session
    sel = st.session_state.get("selected_pos", None)
    tgt = st.session_state.get("target_pos", None)

    cur_x = f"{sel['x']:.3f}" if sel else "—"
    cur_y = f"{sel['y']:.3f}" if sel else "—"
    tgt_x = f"{tgt['x']:.3f}" if tgt else "—"
    tgt_y = f"{tgt['y']:.3f}" if tgt else "—"

    st.markdown(f"""
    <div class="metric-box">
      <div class="metric-label">Current Position (normalized)</div>
      <div class="metric-value">x: {cur_x} &nbsp;&nbsp; y: {cur_y}</div>
    </div>
    <div class="metric-box">
      <div class="metric-label">Target Position (normalized)</div>
      <div class="metric-value">x: {tgt_x} &nbsp;&nbsp; y: {tgt_y}</div>
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

    # Session state defaults
    if "objects" not in st.session_state:
        st.session_state.objects = []
    if "selected_id" not in st.session_state:
        st.session_state.selected_id = None
    if "tool" not in st.session_state:
        st.session_state.tool = "arrow"

    # Seed button pressed → regenerate objects
    if seed_btn:
        rng = random.Random(seed_objects)
        margin = 10
        st.session_state.objects = [
            {"id": i, "x": rng.randint(margin, 200 - margin), "y": rng.randint(margin, 200 - margin)}
            for i in range(seed_objects)
        ]
        st.session_state.selected_id = None
        st.session_state.selected_pos = None
        st.session_state.target_pos = None

    # Serialize state for JS
    objects_json  = json.dumps(st.session_state.objects)
    selected_json = json.dumps(st.session_state.selected_id)
    tool_json     = json.dumps(st.session_state.tool)

    canvas_html = f"""
<!DOCTYPE html>
<html>
<head>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ background:#0a0a0a; display:flex; flex-direction:column; align-items:flex-start; padding:4px; }}
  #toolbar {{
    display:flex; align-items:center; margin-bottom: 8px; gap:6px;
  }}
  .tbtn {{
    width:34px; height:34px; background:#141414; border:1px solid #2a2a2a;
    border-radius:3px; cursor:pointer; display:flex; align-items:center;
    justify-content:center; font-size:16px; transition: all 0.12s;
    color: #777; user-select:none;
  }}
  .tbtn.active {{ background:#1f1f1f; border-color:#666; color:#ddd; box-shadow:0 0 0 1px #444; }}
  canvas {{
    background:#000; border:1px solid #1e1e1e;
    image-rendering: pixelated;
  }}
  #status {{
    font-family: 'JetBrains Mono', monospace; font-size:10px;
    color:#444; margin-top:6px; letter-spacing:0.08em;
  }}
</style>
</head>
<body>
<div id="toolbar">
  <div class="tbtn" id="btn-arrow" title="Select (Arrow)">⬆</div>
  <div class="tbtn" id="btn-cross" title="Set Target (Crosshair)">✛</div>
</div>
<canvas id="c" width="200" height="200"></canvas>
<div id="status">no object selected</div>

<script>
const CANVAS_SIZE = 200;
const RADIUS = 8;

let objects   = {objects_json};
let selectedId = {selected_json};
let tool       = {tool_json};
let target     = null;

const canvas  = document.getElementById('c');
const ctx     = canvas.getContext('2d');
const status  = document.getElementById('status');
const btnArrow = document.getElementById('btn-arrow');
const btnCross = document.getElementById('btn-cross');

// ── tool buttons ──────────────────────────────────────────────────────────
function setTool(t) {{
  tool = t;
  btnArrow.classList.toggle('active', t === 'arrow');
  btnCross.classList.toggle('active', t === 'cross');
  canvas.style.cursor = t === 'cross' ? 'crosshair' : 'default';
  sendToStreamlit({{ type:'tool', tool:t }});
}}
btnArrow.addEventListener('click', () => setTool('arrow'));
btnCross.addEventListener('click', () => setTool('cross'));
setTool(tool);

// ── draw ──────────────────────────────────────────────────────────────────
function draw() {{
  ctx.clearRect(0, 0, CANVAS_SIZE, CANVAS_SIZE);

  // background
  ctx.fillStyle = '#000';
  ctx.fillRect(0, 0, CANVAS_SIZE, CANVAS_SIZE);

  // target marker
  if (target) {{
    ctx.strokeStyle = '#444';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(target.x - 8, target.y);
    ctx.lineTo(target.x + 8, target.y);
    ctx.moveTo(target.x, target.y - 8);
    ctx.lineTo(target.x, target.y + 8);
    ctx.stroke();
    ctx.strokeStyle = '#333';
    ctx.beginPath();
    ctx.arc(target.x, target.y, 5, 0, Math.PI*2);
    ctx.stroke();
  }}

  // objects
  objects.forEach(obj => {{
    const isSel = obj.id === selectedId;
    if (isSel) {{
      // selection ring
      ctx.strokeStyle = '#666';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.arc(obj.x, obj.y, RADIUS + 4, 0, Math.PI*2);
      ctx.stroke();
    }}
    ctx.fillStyle = isSel ? '#ddd' : '#888';
    ctx.beginPath();
    ctx.arc(obj.x, obj.y, RADIUS, 0, Math.PI*2);
    ctx.fill();
  }});
}}

// ── animation for moving selected object to target ────────────────────────
let animFrame = null;

function animateTo(obj, tx, ty, duration=400) {{
  if (animFrame) cancelAnimationFrame(animFrame);
  const sx = obj.x, sy = obj.y;
  const start = performance.now();
  function step(now) {{
    const t = Math.min((now - start) / duration, 1);
    const ease = 1 - Math.pow(1 - t, 3);
    obj.x = sx + (tx - sx) * ease;
    obj.y = sy + (ty - sy) * ease;
    draw();
    if (t < 1) {{
      animFrame = requestAnimationFrame(step);
    }} else {{
      obj.x = tx; obj.y = ty;
      draw();
      sendToStreamlit({{ type:'move', id: obj.id, x: obj.x, y: obj.y }});
    }}
  }}
  requestAnimationFrame(step);
}}

// ── canvas click ──────────────────────────────────────────────────────────
canvas.addEventListener('click', e => {{
  const rect = canvas.getBoundingClientRect();
  const mx = e.clientX - rect.left;
  const my = e.clientY - rect.top;

  if (tool === 'arrow') {{
    // hit-test objects (closest within radius)
    let best = null, bestD = RADIUS + 4;
    objects.forEach(obj => {{
      const d = Math.hypot(obj.x - mx, obj.y - my);
      if (d < bestD) {{ best = obj; bestD = d; }}
    }});
    selectedId = best ? best.id : null;
    target = null;
    if (best) {{
      status.textContent = `selected obj ${{best.id}}  pos (${{(best.x/CANVAS_SIZE).toFixed(3)}}, ${{(best.y/CANVAS_SIZE).toFixed(3)}})`;
      sendToStreamlit({{ type:'select', id: best.id, x: best.x, y: best.y }});
    }} else {{
      status.textContent = 'no object selected';
      sendToStreamlit({{ type:'deselect' }});
    }}
    draw();

  }} else if (tool === 'cross') {{
    if (selectedId === null) {{
      status.textContent = 'select an object first';
      return;
    }}
    target = {{ x: mx, y: my }};
    const obj = objects.find(o => o.id === selectedId);
    if (obj) {{
      status.textContent = `moving obj ${{obj.id}} → (${{(mx/CANVAS_SIZE).toFixed(3)}}, ${{(my/CANVAS_SIZE).toFixed(3)}})`;
      sendToStreamlit({{ type:'target', x: mx, y: my }});
      animateTo(obj, mx, my);
    }}
  }}
}});

// ── communicate back to Streamlit ─────────────────────────────────────────
function sendToStreamlit(data) {{
  window.parent.postMessage({{
    type: 'streamlit:setComponentValue',
    value: data
  }}, '*');
}}

draw();
</script>
</body>
</html>
"""

    from streamlit.components.v1 import html as st_html
    result = st_html(canvas_html, height=310, scrolling=False)

    # Handle messages back from canvas via query params workaround
    # (In production deploy, use st_canvas or a custom component for two-way binding)
    # For now the tracker updates are shown based on click interactions above.
