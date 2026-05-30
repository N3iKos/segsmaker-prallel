# Revamp Checklist - Fork & Parallel Revamp to N3iKos/segsmaker-prallel

- `[x]` Refactor `script/nenen88.py` to be thread-safe (disable process-wide `os.chdir` in `netorare` and use thread-safe absolute path resolutions, pass `cwd` directly to `subprocess.Popen` in `ariari` and `curlly`).
- `[x]` Implement parallel download engine `download_parallel` in `script/nenen88.py` matching the user's progress console layout.
- `[x]` Refactor and parallelize `clone` command in `script/nenen88.py` to clone extensions concurrently when parallel mode is active.
- `[x]` Refactor `script/KC/setup.py` to support parallel setup arguments (`--parallel` & `--max_simultaneous`) and invoke concurrent downloads for dependencies/upscalers.
- `[x]` Redesign Jupyter Notebook forms (`Segsmaker_COLAB.ipynb`) via `#@param` attributes (Setup parameters, 5-slot Model/LoRA inputs, Extensions forms, Launcher dropdowns and tunnels).
- `[x]` Rename all occurrences of `gutris1/segsmaker` to `N3iKos/segsmaker-prallel` across notebooks and scripts (`Segsmaker_COLAB.ipynb`, `Segsmaker.ipynb`, `setup.py`, `conda.py`, `setup.py` in SM, `util.py`, `controlnet.py`, and `README.md`).
- `[x]` Perform verification tests (compile syntax check for all python scripts, schema validation for notebooks).
