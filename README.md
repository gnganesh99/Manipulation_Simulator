# stm_co_mani_sim
STM manipulation simulator using steamlit app

# Object Mover — Simulation Interface

An interactive simulation tool for placing and moving circular objects within a bounded arena. Built with Streamlit.

## 🚀 Launch App

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://YOUR-APP-NAME.streamlit.app)

> Replace the link above with your Streamlit Cloud URL after deployment (see below).

---

## Controls

| Control | Description |
|---|---|
| **Seed Objects** | Number of objects to place (1–30) |
| **SEED button** | Randomly place objects in the arena |
| **⬆ Arrow tool** | Click to select an object |
| **✛ Crosshair tool** | Click to set a target; selected object moves there |
| **Action 1 / Action 2** | Parameters passed to the prediction model (10–90) |

The **Tracker** panel shows the current and target positions of the selected object, normalised to [0, 1].

---

## Deploy to Streamlit Community Cloud (free)

1. Push this repo to GitHub (if not already there)
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub
3. Click **"New app"** → select your repo → set **Main file path** to `app.py`
4. Click **Deploy** — you'll get a public URL in ~1 minute
5. Paste the URL into the badge link at the top of this README

---

## Project Structure

```
.
├── app.py               # Streamlit application
├── prediction_utils.py  # Model inference hook (stub until model is ready)
├── gaussian_model.pt    # TorchScript model (add when ready)
└── requirements.txt     # Python dependencies
```

---

## Adding the Prediction Model

Once your `gaussian_model.pt` is ready:

1. Add `torch` to `requirements.txt`
2. Uncomment the model-loading code in `prediction_utils.py`
3. Uncomment the prediction hook in `app.py` (marked with `# Future: prediction hook`)
