# Fusion 360 Model Sprue Generator

A Python script for Autodesk Fusion that automatically arranges visible solid bodies into a flat layout, connects them with a structural frame and support sprues, and merges everything into a single solid body – exactly like a plastic model kit parts tree (sprue). The result is optimized for convenient 3D printing as one piece.

Before:
<img width="1266" height="980" alt="Screenshot_20260703021644" src="https://github.com/user-attachments/assets/6d68cb32-2d9a-4e01-a98a-7e5185392e71" />

After:
<img width="993" height="630" alt="Screenshot_20260723203544" src="https://github.com/user-attachments/assets/135c1de9-a7e4-4b47-881c-ac0b59a744bc" />

---

## Features

- **Auto‑orientation** – Rotates each part so its largest planar face points downward and sets Z=0.
- **Smart tiling** – Arranges parts in a near‑square grid, minimizing wasted space.
- **Adjustable parameters** – Easily tune gaps, bar thickness, frame margins, and sprue count based on part area.
- **Adaptive sprues** – Each part gets 1, 2, or 3 connecting bars depending on its projected area (thresholds configurable).
- **Full merge** – All parts and the supporting frame are joined into one solid body, ready for 3D printing as a single piece.

---

## How It Works

1. The script scans all **visible** bodies in the active Fusion design.
2. Each body is rotated to bring its largest flat face to the bottom, then translated so its lowest point is at Z=0.
3. Parts are packed into a rectangular grid (rows × columns) with a user‑defined gap between them.
4. A rectangular outer frame is created around the whole layout, and inner separating bars are added between rows/columns.
5. For each part, the script checks the available gaps to the frame/bars and places connecting sprues (short bars) from the part to the nearest frame elements. The number of sprues depends on the part's XY projected area:
   - `< AREA_1` → 1 sprue
   - `< AREA_2` → 2 sprues
   - `≥ AREA_2` → 3 sprues
6. All parts and frame elements are joined into a single solid body.

---

## Parameters (tweak at the top of the script)

| Variable      | Default (cm) | Description |
|---------------|--------------|-------------|
| `GAP`         | 0.3          | Distance between parts (cm) |
| `BAR_W`       | 0.2          | Width of frame and sprue bars (cm) |
| `BAR_T`       | 0.15         | Thickness (height) of all bars (cm) |
| `FRAME_PAD`   | 0.3          | Outer margin from parts to the frame (cm) |
| `AREA_1`      | 4.0          | Area threshold (cm²) for 1 sprue |
| `AREA_2`      | 16.0         | Area threshold (cm²) for 2 sprues |

> **Note:** All dimensions are in **cm**. The script uses Fusion’s internal units (cm by default), so adjust accordingly if your design uses mm or inches.

---

## Requirements

- Autodesk Fusion (with integrated Python API)
- The design must have at least one visible solid body.

---

## Usage

1. Open your Fusion design containing the parts you want to arrange.
2. Make sure only the bodies you wish to include are **visible** (light bulb on, and all parent components visible as well).
3. Run the script:
   - Go to `Tools` > `Add‑Ins` > `Scripts and Add‑Ins`.
   - Click `New` and paste the script code, or place the `.py` file in the appropriate folder.
   - Select the script and click `Run`.
4. The script will print progress messages to the console and, on success, you will have a single combined body ready.

---

## Installation for GitHub

To use this script, clone or download this repository and place the Python file in your Fusion scripts directory (usually `%APPDATA%/Autodesk/Autodesk Fusion 360/API/Scripts/` on Windows, or `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/Scripts/` on macOS).

---

## Notes & Tips

- All parts are processed **in the order they appear** in the browser. The grid is filled row‑by‑row.
- The script assumes bodies are separate solids (not components). If your parts are inside components, make sure the component occurrences are visible.
- After running, you can manually edit the frame or sprues if needed – the script does not lock further modifications.
- Designed for **Fusion 360** personal or commercial editions (tested on recent versions).

---

## License

MIT License – free to use, modify, and distribute. See [LICENSE](LICENSE) for details.

---

## Contributing

Feel free to open issues or submit pull requests for improvements. Suggestions for smarter packing algorithms, variable bar geometry, or UI integration are welcome!

---

**Happy printing!** 🖨️
