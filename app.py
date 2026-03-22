import streamlit as st
import json
import random

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
  body {{ background:#f5f5f5; display:flex; flex-direction:column; align-items:flex-start; padding:4px; }}
  #toolbar {{
    display:flex; align-items:center; margin-bottom: 8px; gap:6px;
  }}
  .tbtn {{
    width:34px; height:34px; background:#efefef; border:1px solid #ccc;
    border-radius:3px; cursor:pointer; display:flex; align-items:center;
    justify-content:center; font-size:16px; transition: all 0.12s;
    color: #555; user-select:none;
  }}
  .tbtn.active {{ background:#e0e0e0; border-color:#888; color:#111; box-shadow:0 0 0 1px #bbb; }}
  canvas {{
    background:#FFF8F0; border:2px solid #556B2F;
    image-rendering: pixelated;
  }}
  #status {{
    font-family: 'JetBrains Mono', monospace; font-size:10px;
    color:#888; margin-top:6px; letter-spacing:0.08em;
  }}
  #tracker {{
    margin-top: 12px; width: 510px;
    font-family: 'JetBrains Mono', monospace;
  }}
  .tr-label {{
    font-size: 9px; color: #999; text-transform: uppercase;
    letter-spacing: 0.12em; margin-bottom: 3px;
  }}
  .tr-value {{
    font-size: 12px; color: #1a1a1a; letter-spacing: 0.05em;
    background: #fff; border: 1px solid #ddd; border-radius: 2px;
    padding: 5px 10px; margin-bottom: 8px;
  }}
</style>
</head>
<body>
<div id="toolbar">
  <div class="tbtn" id="btn-arrow" title="Select (Arrow)">⬆</div>
  <div class="tbtn" id="btn-cross" title="Set Target (Crosshair)">✛</div>
</div>
<canvas id="c" width="500" height="500"></canvas>
<div id="status">no object selected</div>
<div id="tracker">
  <div class="tr-label">Current Position (normalized)</div>
  <div id="cur-pos" class="tr-value">x: &mdash; &nbsp;&nbsp; y: &mdash;</div>
  <div class="tr-label">Target Position (normalized)</div>
  <div id="tgt-pos" class="tr-value">x: &mdash; &nbsp;&nbsp; y: &mdash;</div>
</div>

<script>
const CANVAS_SIZE = 500;
const RADIUS = 12;

let objects   = {objects_json};
let selectedId = {selected_json};
let tool       = {tool_json};
let target     = null;

const canvas  = document.getElementById('c');
const ctx     = canvas.getContext('2d');
const status  = document.getElementById('status');
const btnArrow = document.getElementById('btn-arrow');
const btnCross = document.getElementById('btn-cross');
const curPos   = document.getElementById('cur-pos');
const tgtPos   = document.getElementById('tgt-pos');

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
// crosshair is default — canvas cursor set accordingly
setTool(tool);
// always show crosshair cursor inside canvas regardless of tool
canvas.addEventListener('mouseenter', () => {{ canvas.style.cursor = tool === 'arrow' ? 'default' : 'crosshair'; }});

// ── draw ──────────────────────────────────────────────────────────────────
function draw() {{
  ctx.clearRect(0, 0, CANVAS_SIZE, CANVAS_SIZE);

  // background — light cream
  ctx.fillStyle = '#FFF8F0';
  ctx.fillRect(0, 0, CANVAS_SIZE, CANVAS_SIZE);

  // target marker
  if (target) {{
    ctx.strokeStyle = '#556B2F';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(target.x - 12, target.y);
    ctx.lineTo(target.x + 12, target.y);
    ctx.moveTo(target.x, target.y - 12);
    ctx.lineTo(target.x, target.y + 12);
    ctx.stroke();
    ctx.strokeStyle = '#556B2F';
    ctx.beginPath();
    ctx.arc(target.x, target.y, 6, 0, Math.PI*2);
    ctx.stroke();
  }}

  // objects
  objects.forEach(obj => {{
    const isSel = obj.id === selectedId;
    if (isSel) {{
      // selection ring — olive green
      ctx.strokeStyle = '#556B2F';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(obj.x, obj.y, RADIUS + 5, 0, Math.PI*2);
      ctx.stroke();
    }}
    ctx.fillStyle = '#1a1a1a';
    ctx.strokeStyle = isSel ? '#556B2F' : '#444';
    ctx.lineWidth = isSel ? 2 : 1;
    ctx.beginPath();
    ctx.arc(obj.x, obj.y, RADIUS, 0, Math.PI*2);
    ctx.fill();
    ctx.stroke();
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
      curPos.innerHTML = `x: ${{(obj.x/CANVAS_SIZE).toFixed(3)}} &nbsp;&nbsp; y: ${{(obj.y/CANVAS_SIZE).toFixed(3)}}`;
      sendToStreamlit({{ type:'move', id: obj.id, x: obj.x, y: obj.y }});
    }}
  }}
  requestAnimationFrame(step);
}}

// ── auto-select first object if none selected on load ───────────────────
if (selectedId === null && objects.length > 0) {{
  selectedId = objects[0].id;
  const first = objects[0];
  curPos.innerHTML = `x: ${{(first.x/CANVAS_SIZE).toFixed(3)}} &nbsp;&nbsp; y: ${{(first.y/CANVAS_SIZE).toFixed(3)}}`;
  status.textContent = `selected obj ${{first.id}}  pos (${{(first.x/CANVAS_SIZE).toFixed(3)}}, ${{(first.y/CANVAS_SIZE).toFixed(3)}})`;
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
      curPos.innerHTML = `x: ${{(best.x/CANVAS_SIZE).toFixed(3)}} &nbsp;&nbsp; y: ${{(best.y/CANVAS_SIZE).toFixed(3)}}`;
      tgtPos.innerHTML = 'x: &mdash; &nbsp;&nbsp; y: &mdash;';
      sendToStreamlit({{ type:'select', id: best.id, x: best.x, y: best.y }});
      // auto-switch back to crosshair after selection
      setTool('cross');
    }} else {{
      status.textContent = 'no object selected';
      curPos.innerHTML = 'x: &mdash; &nbsp;&nbsp; y: &mdash;';
      tgtPos.innerHTML = 'x: &mdash; &nbsp;&nbsp; y: &mdash;';
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
      tgtPos.innerHTML = `x: ${{(mx/CANVAS_SIZE).toFixed(3)}} &nbsp;&nbsp; y: ${{(my/CANVAS_SIZE).toFixed(3)}}`;
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
    result = st_html(canvas_html, height=740, scrolling=False)

    # Handle messages back from canvas via query params workaround
    # (In production deploy, use st_canvas or a custom component for two-way binding)
    # For now the tracker updates are shown based on click interactions above.
