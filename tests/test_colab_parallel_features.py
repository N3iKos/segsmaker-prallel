import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def read_notebook(path: str) -> dict:
    return json.loads(read_text(path))


def joined_notebook_source(path: str) -> str:
    notebook = read_notebook(path)
    return "\n".join("".join(cell.get("source", [])) for cell in notebook["cells"])


def test_batch_download_helpers_are_defined():
    source = read_text("script/nenen88.py")

    for name in [
        "DownloadTask",
        "DownloadProgress",
        "analyze_download_links",
        "render_parallel_dashboard",
        "download_many",
    ]:
        assert name in source

    assert "ThreadPoolExecutor" in source
    assert "clear_output(wait=True)" in source


def test_colab_notebook_exposes_parallel_setup_and_five_model_lora_slots():
    source = joined_notebook_source("notebook/Segsmaker_COLAB.ipynb")

    for param_name in [
        "Enable_Parallel_Setup",
        "Setup_Max_Parallel_Downloads",
        "Enable_Parallel_Model_LoRA_Downloads",
        "Model_LoRA_Max_Parallel_Downloads",
    ]:
        assert param_name in source

    for index in range(1, 6):
        assert re.search(rf"Model_{index}\s*=", source)
        assert re.search(rf"LoRA_{index}\s*=", source)

    assert "download_many" in source


def test_colab_launcher_uses_dropdown_driven_presets():
    source = joined_notebook_source("notebook/Segsmaker_COLAB.ipynb")

    for expected in [
        "Launch_Preset",
        "Custom_Launch_Args",
        "Skip_ComfyUI_Check",
        "NGROK_Token",
        "ZROK_Token",
        "recommended_args",
    ]:
        assert expected in source

    assert "%run segsmaker.py" in source


def test_fork_self_references_are_updated():
    tracked = [
        "README.md",
        "notebook/Segsmaker_COLAB.ipynb",
        "notebook/Segsmaker.ipynb",
        "script/KC/setup.py",
    ]

    combined = "\n".join(read_text(path) for path in tracked)
    assert "N3iKos/segsmaker-prallel" in combined

    for line in combined.splitlines():
        if "github.com/gutris1/segsmaker" in line:
            assert "authored by gutris1" in line or "repository https://github.com/gutris1/segsmaker" in line
