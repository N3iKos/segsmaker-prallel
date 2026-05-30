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
    for expected in [
        "aria_connections=16",
        "aria_split=16",
        "min_split_size='1M'",
        "skip_completed=True",
        "fallback_to_wget=True",
        "format_download_complete",
    ]:
        assert expected in source


def test_civitai_api_links_get_safe_analysis_labels():
    source = read_text("script/nenen88.py")

    assert "fallback_name = f'download-{index}'" in source
    assert "label_source = filename or _download_filename(url, known_host) or fallback_name" in source


def test_notebook_download_calls_do_not_display_task_repr():
    source = joined_notebook_source("notebook/Segsmaker_COLAB.ipynb")

    assert "_download_results = download_many(" in source
    assert re.search(r"^\s*download_many\(", source, flags=re.MULTILINE) is None


def test_colab_notebook_exposes_parallel_setup_and_five_model_lora_slots():
    source = joined_notebook_source("notebook/Segsmaker_COLAB.ipynb")

    for param_name in [
        "Parallel_Setup_Download",
        "Setup_Max_Workers",
        "Setup_Aria_Connections",
        "Setup_Aria_Split",
        "Setup_Min_Split_Size",
        "download_mode",
        "parallel_workers",
        "aria_connections",
        "aria_split",
        "min_split_size",
        "skip_completed_files",
        "fallback_to_wget",
    ]:
        assert param_name in source

    for index in range(1, 6):
        assert re.search(rf"Checkpoint_{index}\s*=", source)
        assert re.search(rf"Lora_{index}\s*=", source)

    assert "download_many" in source
    assert "FLUX Model Downloader" in source
    assert "Temporary Model Downloader" in source


def test_colab_launcher_uses_dropdown_driven_presets():
    source = joined_notebook_source("notebook/Segsmaker_COLAB.ipynb")

    for expected in [
        "Launcher WebUI",
        "Software",
        "Ngrok_Token",
        "Zrok_Token",
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
