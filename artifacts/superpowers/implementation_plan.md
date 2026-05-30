# Implementation Plan - Fork and Revamp to N3iKos/segsmaker-prallel (Updated with User Layout)

We will revamp the Jupyter Notebook and scripts to make them highly user-friendly for lay users. This includes implementing a multi-threaded parallel download engine, fully exposing all download/run parameters to Google Colab forms (`#@param`), replacing all references to the original repository with the user's fork `N3iKos/segsmaker-prallel`, and displaying a clean unified download console as designed by the user.

---

## Proposed Technical Design

### 1. Concurrent & Parallel Download Engine
To replace the sequential downloader without breaking existing functionality, we will implement:
- **Thread-safe download pipeline**: The original `netorare` function in `nenen88.py` uses process-wide working directory modifications via `os.chdir()`. We will refactor this to be thread-safe by:
  - Removing process-wide `os.chdir` in concurrent operations.
  - Passing `cwd` directly to `subprocess.Popen` in the `ariari` (aria2c) and `curlly` (curl) functions.
  - Resolving targets using absolute paths thread-safely.
- **Dynamic Thread Pool Executor**: A new high-level helper `download_parallel(items, max_workers)` in `nenen88.py` that utilizes Python's `concurrent.futures.ThreadPoolExecutor` to handle concurrent downloads up to the configured limit.
- **Cloning Parallelization**: Accelerating the `clone` function when pulling multiple extensions/custom nodes.

### 2. Full UI/UX Exposure via `#@param`
We will redesign the Jupyter Notebook cells to act as forms where every setting is customizable without modifying the underlying script code:
- **Cell Setup Forms**:
  - Expose a `Parallel_Download` checkbox and `Max_Simultaneous` slider.
  - Automatically pass these parameters to `setup.py` via the command line `--parallel` and `--max_simultaneous`.
- **5-Slot Model & 5-Slot LoRA Forms**:
  - 5 text slots for Checkpoints (`Model_1` to `Model_5`) and 5 text slots for LoRAs (`LoRA_1` to `LoRA_5`).
  - Optional custom filenames can be appended inside the slots (e.g., `https://url.com/model.safetensors custom_name.safetensors`).
  - Thread-safe parsing that aggregates all non-empty inputs and executes parallel downloads immediately.
- **Extensions & Other Assets Forms**:
  - Expose slots for custom VAEs, Embeddings, Upscalers, FLUX UNet, FLUX Clip, and SD Extensions / ComfyUI Custom Nodes.
- **Launcher WebUI Form**:
  - Dropdown for launch arguments with presets for A1111, Forge, ReForge, ComfyUI, SwarmUI, and a "Custom" input.
  - Easy dropdown selector for tunnel types (Ngrok, Zrok, None) and corresponding token input fields.

### 3. Repository-wide Fork Renaming
We will systematically replace all references from the original `gutris1/segsmaker` to `N3iKos/segsmaker-prallel` inside:
- `Segsmaker_COLAB.ipynb` and `Segsmaker.ipynb`
- `README.md`
- `script/controlnet.py`
- `script/cupang.py`
- `script/KC/setup.py`
- `script/SM/conda.py`
- `script/SM/setup.py`
- `script/SM/util.py`

---

## User Review Required

> [IMPORTANT]
> **Process-wide directory tracking warning**: Changing to a multi-threaded parallel execution model requires disabling process-wide working directory changes (`os.chdir`) inside the download loops. We have designed a thread-safe refactoring for `nenen88.py` that keeps the original parsing and UI feedback intact while using localized process execution directories (`cwd` parameter).

---

## Unified Progress Dashboard Layout (User Proposal)
During concurrent downloads, the console output will display a clean, single-screen refreshing layout designed exactly to the user's specification:

1. **Analysis Phase**:
   ```
   [INFO] Analyzing 5 link(s)...
   [OK] [1] juggernaut_xl_v9.safetensors
   [OK] [2] ponyDiffusion_v6.safetensors
   ...
   [INFO] Valid: 5/5
   ```
2. **Download Phase** (Dynamic Real-Time Update):
   ```
   [INFO] Starting parallel download...

   TOTAL: [████████████████░░░░░░░░░░░░░░] 53.4%
   Speed: 24.50 MB/s | Active: 3 | Done: 2/5
   ----------------------------------------------------------------------
   [ 1] juggernaut_xl_v9.safetensors: 45.3% |  12.50 MB/s | 📥 Downloading
   [ 2] ponyDiffusion_v6.safetensors: 50.0% |  12.00 MB/s | 📥 Downloading
   [ 3] detail_tweaker_xl.safetensors: 100.0%|   0.00 MB/s | ✅ Done
   [ 4] pony_more_details.safetensors: 100.0%|   0.00 MB/s | ✅ Done
   [ 5] style-enhancer-xl.safetensors:  0.0% |   0.00 MB/s | ⏳ Pending
   ```

---

## Proposed Changes

We will systematically modify the following components:

### [Jupyter Notebooks]

#### [MODIFY] [Segsmaker_COLAB.ipynb](file:///d:/1NGODING/segsmaker-main-backup/notebook/Segsmaker_COLAB.ipynb)
- Redesign the Setup Cell to include `#@param` parallel toggles.
- Redesign Code Cell 2 into an Extensions/Custom Nodes/VAEs downloader form.
- Redesign Code Cell 3 to provide 5 slots for Models and 5 slots for LoRAs form.
- Redesign Launch Cell to provide preset dropdown and tunnel parameters.
- Replace all repository link references.

#### [MODIFY] [Segsmaker.ipynb](file:///d:/1NGODING/segsmaker-main-backup/notebook/Segsmaker.ipynb)
- Update GitHub repository link references to `N3iKos/segsmaker-prallel`.

### [Python Scripts]

#### [MODIFY] [nenen88.py](file:///d:/1NGODING/segsmaker-main-backup/script/nenen88.py)
- Refactor `netorare` to be thread-safe (remove `os.chdir` dependencies).
- Pass `cwd` safely in `ariari` and `curlly`.
- Implement `download_parallel(items, max_workers)` and refactor `clone` for concurrent execution.
- Implement the user-designed stdout progress updating console.

#### [MODIFY] [setup.py](file:///d:/1NGODING/segsmaker-main-backup/script/KC/setup.py)
- Add command-line arguments: `--parallel` and `--max_simultaneous`.
- Integrate parallel download helper `download_parallel` for upscalers, scripts, and extra models.
- Replace repository URLs.

#### [MODIFY] [conda.py](file:///d:/1NGODING/segsmaker-main-backup/script/SM/conda.py), [setup.py](file:///d:/1NGODING/segsmaker-main-backup/script/SM/setup.py), [util.py](file:///d:/1NGODING/segsmaker-main-backup/script/SM/util.py), [controlnet.py](file:///d:/1NGODING/segsmaker-main-backup/script/controlnet.py)
- Replace all repository references to use `N3iKos/segsmaker-prallel`.

---

## Verification Plan

### Automated/Local Tests
Since the workspace is on a local machine, we will verify:
1. Syntax correctness of all updated python files by compiling them:
   `python -m py_compile script/nenen88.py script/KC/setup.py`
2. Run localized unit tests for the thread-safe `netorare` function and parallel downloading logic using dummy URLs to verify proper execution.
3. Validate Jupyter notebook JSON schemas of both modified notebooks.
