# STM Manipulation Simulator

This app simulates the manipulation of carbon monoxide (CO) molecules using a scanning tunneling microscope (STM).

It is inspired by experimental STM manipulation of CO molecules on a Cu(111) surface, where a selected molecule is guided toward a target position by adjusting the manipulation conditions. The simulator provides a simple interactive way to explore that process and visualize how particles move under different settings.

The simulator is a Gausssian Mixture model that is trained on experimental datasets


## Open the App

<p align="center">
  <a href="https://manipulationsimulator-95u2rnvvz3af4ktuj8v7qj.streamlit.app/">
    <img
      src="https://img.shields.io/badge/OPEN%20THE%20APP-STM%20Manipulation%20Simulator-0A84FF?style=for-the-badge&logo=streamlit&logoColor=white"
      alt="Open the STM Manipulation Simulator app"
    />
  </a>
</p>

<p align="center">
  <a href="https://manipulationsimulator-95u2rnvvz3af4ktuj8v7qj.streamlit.app/"><strong>https://manipulationsimulator-95u2rnvvz3af4ktuj8v7qj.streamlit.app/</strong></a>
</p>

## Modes

- `Ideal`: a simplified mode where the selected CO molecule moves toward the chosen target under favorable manipulation settings (Bias < 20 mV; Setpoint > 80nA).
- `Predictive`: a data-driven mode where the next position is estimated from learned behavior based on experimental manipulation data.

## How to Use

1. Open the app using the blue link above.
2. Use `Seed Objects` and `SEED` to place particles on the canvas.
3. Click the arrow tool to select a particle.
4. Click the crosshair tool, then click a target point on the canvas.
5. Adjust `Bias (mV)` and `Setpoint (nA)` to change the motion behavior.
6. Switch between `Ideal` and `Predictive` mode as needed.

## Project Structure

```text
.
|-- app.py
|-- prediction_utils.py
|-- collision_detection.py
|-- canvas_component/
|   `-- index.html
|-- models/
|   |-- gmm_model0.pt
|   `-- gmm_model0_meta.json
|-- requirements.txt
`-- README.md
```

## Acknowledgement / Credits

This simulator is based on STM manipulation ideas and data involving carbon monoxide molecules on Cu(111). 

Experimental support - Mykola Telychko, CNMS, ORNL.


## Contact

For questions or feedback, please contact the repository maintainer.
