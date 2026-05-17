from __future__ import annotations

import os
import shlex
import tempfile
from pathlib import Path

from IPython import get_ipython
from IPython.display import clear_output, display
import ipywidgets as widgets


WEBUI_CHOICES = [
    "A1111",
    "Forge",
    "ReForge",
    "ReForge-old",
    "Forge-Classic",
    "Forge-Neo",
    "ComfyUI",
    "SwarmUI",
]

LAUNCH_ARGS = {
    "A1111": "--xformers",
    "Forge": "--disable-xformers --opt-sdp-attention --cuda-stream",
    "ReForge": "--xformers --cuda-stream",
    "ReForge-old": "--xformers --cuda-stream",
    "Forge-Classic": "--xformers --cuda-stream --persistent-patches",
    "Forge-Neo": "--xformers --cuda-stream",
    "ComfyUI": "--dont-print-server --use-pytorch-cross-attention",
    "SwarmUI": "--launch_mode none",
}


def _ip():
    shell = get_ipython()
    if shell is None:
        raise RuntimeError("This helper must run inside an IPython/Jupyter notebook.")
    return shell


def _ns(name, default=None, required=False):
    value = _ip().user_ns.get(name, default)
    if required and value is None:
        raise RuntimeError(f"Notebook variable '{name}' is not ready. Run the installer first.")
    return value


def _button(text, style="primary"):
    return widgets.Button(
        description=text,
        button_style=style,
        layout=widgets.Layout(width="180px"),
    )


def _textarea(description, placeholder="", rows=4):
    return widgets.Textarea(
        description=description,
        placeholder=placeholder,
        layout=widgets.Layout(width="760px", height=f"{max(rows, 2) * 28}px"),
        style={"description_width": "140px"},
    )


def _text(description, value="", placeholder="", password=False):
    klass = widgets.Password if password else widgets.Text
    return klass(
        description=description,
        value=value,
        placeholder=placeholder,
        layout=widgets.Layout(width="760px"),
        style={"description_width": "140px"},
    )


def _lines(value):
    return [line.strip() for line in value.splitlines() if line.strip()]


def _parallel_download(queue, max_workers=3):
    if not queue:
        return
    try:
        from nenen88 import parallel_batch_download
    except Exception as exc:
        raise RuntimeError("parallel_batch_download is not available. Run the installer first.") from exc
    parallel_batch_download(queue, max_workers=max_workers)


def _run_download(url, dest):
    ip = _ip()
    ip.run_line_magic("cd", f"-q {shlex.quote(str(dest))}")
    ip.run_line_magic("download", url)


def display_installer(setup_path):
    webui = widgets.Dropdown(
        description="WebUI",
        options=WEBUI_CHOICES,
        value="Forge-Neo",
        layout=widgets.Layout(width="420px"),
        style={"description_width": "90px"},
    )
    civitai = _text("Civitai key", password=True, placeholder="Required for Civitai downloads")
    hf_token = _text("HF token", password=True, placeholder="Optional Hugging Face READ token")
    run_button = _button("Install WebUI")
    out = widgets.Output()

    def run(_):
        with out:
            clear_output(wait=True)
            key = civitai.value.strip()
            hf = hf_token.value.strip()
            if not key:
                print("Civitai key is required.")
                return
            if len(key) < 32:
                print("Civitai key looks too short. Paste the full API key.")
                return
            args = [
                shlex.quote(str(setup_path)),
                "--webui",
                shlex.quote(webui.value),
                "--civitai_key",
                shlex.quote(key),
            ]
            if hf:
                args += ["--hf_read_token", shlex.quote(hf)]
            print(f"Installing {webui.value}...")
            _ip().run_line_magic("run", " ".join(args))

    run_button.on_click(run)
    display(widgets.VBox([webui, civitai, hf_token, run_button, out]))


def display_model_downloader():
    ckpt = _textarea("Checkpoints", "One checkpoint URL per line", rows=5)
    lora = _textarea("LoRA", "One LoRA URL per line", rows=5)
    vae = _text("VAE URL", placeholder="Optional VAE URL")
    parallel = widgets.Checkbox(value=True, description="Parallel download")
    workers = widgets.IntSlider(value=3, min=1, max=6, step=1, description="Workers")
    run_button = _button("Download Models")
    out = widgets.Output()

    def run(_):
        with out:
            clear_output(wait=True)
            queue = []
            for url in _lines(ckpt.value):
                queue.append((url, str(_ns("CKPT", required=True)), None))
            for url in _lines(lora.value):
                queue.append((url, str(_ns("LORA", required=True)), None))
            if vae.value.strip():
                queue.append((vae.value.strip(), str(_ns("VAE", required=True)), None))
            if not queue:
                print("No URLs provided.")
                return
            if parallel.value:
                _parallel_download(queue, max_workers=workers.value)
            else:
                for url, dest, _ in queue:
                    _run_download(url, dest)

    run_button.on_click(run)
    display(widgets.VBox([ckpt, lora, vae, widgets.HBox([parallel, workers]), run_button, out]))


def display_extra_assets():
    extensions = _textarea("Extensions", "One git clone URL per line", rows=3)
    embeddings = _textarea("Embeddings", "One embedding URL per line", rows=2)
    upscalers = _textarea("Upscalers", "One upscaler URL per line", rows=2)
    run_button = _button("Download Assets")
    out = widgets.Output()

    def run(_):
        with out:
            clear_output(wait=True)
            ext_urls = _lines(extensions.value)
            if ext_urls:
                with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tmp:
                    tmp.write("\n".join(ext_urls))
                    tmp_path = tmp.name
                try:
                    _ip().run_line_magic("cd", f"-q {shlex.quote(str(_ns('Extensions', required=True)))}")
                    _ip().run_line_magic("clone", tmp_path)
                finally:
                    Path(tmp_path).unlink(missing_ok=True)

            queue = []
            for url in _lines(embeddings.value):
                queue.append((url, str(_ns("Embeddings", required=True)), None))
            for url in _lines(upscalers.value):
                queue.append((url, str(_ns("Upscalers", required=True)), None))
            if queue:
                _parallel_download(queue, max_workers=3)
            if not ext_urls and not queue:
                print("No assets provided.")

    run_button.on_click(run)
    display(widgets.VBox([extensions, embeddings, upscalers, run_button, out]))


def display_flux_downloader():
    variant = widgets.Dropdown(
        description="Variant",
        options=["None", "FLUX.1-schnell (Fast, 4-step)", "FLUX.1-dev (Quality, 20-step)"],
        value="None",
        layout=widgets.Layout(width="520px"),
        style={"description_width": "90px"},
    )
    unet = _text("UNet", "https://huggingface.co/Kijai/flux-fp8/resolve/main/flux1-schnell-fp8.safetensors")
    clip_l = _text("CLIP-L", "https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/clip_l.safetensors")
    t5xxl = _text("T5XXL", "https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/t5xxl_fp8_e4m3fn.safetensors")
    vae = _text("VAE", "https://huggingface.co/black-forest-labs/FLUX.1-schnell/resolve/main/ae.safetensors")
    run_button = _button("Download FLUX")
    out = widgets.Output()

    def run(_):
        with out:
            clear_output(wait=True)
            if variant.value == "None":
                print('Variant is "None"; skipping.')
                return
            selected_unet = unet.value.strip()
            if "dev" in variant.value.lower() and "schnell" in selected_unet:
                selected_unet = selected_unet.replace("schnell", "dev")
            queue = [
                (selected_unet, str(_ns("UNET", required=True)), None),
                (clip_l.value.strip(), str(_ns("CLIP", required=True)), None),
                (t5xxl.value.strip(), str(_ns("CLIP", required=True)), None),
                (vae.value.strip(), str(_ns("VAE", required=True)), "flux_ae.safetensors"),
            ]
            queue = [item for item in queue if item[0]]
            _parallel_download(queue, max_workers=2)

    run_button.on_click(run)
    display(widgets.VBox([variant, unet, clip_l, t5xxl, vae, run_button, out]))


def display_temporary_downloader():
    ckpt = _textarea("Temp checkpoints", "URL optional_filename, one per line", rows=2)
    lora = _textarea("Temp LoRA", "One URL per line", rows=2)
    run_button = _button("Download Temporary")
    out = widgets.Output()

    def run(_):
        with out:
            clear_output(wait=True)
            queue = []
            for raw in _lines(ckpt.value):
                parts = raw.split(None, 1)
                queue.append((parts[0], str(_ns("TMP_CKPT", required=True)), parts[1] if len(parts) > 1 else None))
            for raw in _lines(lora.value):
                queue.append((raw, str(_ns("TMP_LORA", required=True)), None))
            if not queue:
                print("No temporary URLs provided.")
                return
            _parallel_download(queue, max_workers=3)

    run_button.on_click(run)
    display(widgets.VBox([ckpt, lora, run_button, out]))


def display_launcher():
    marked_ui = None
    try:
        home = Path(_ns("HOME"))
        marked = home / "gutris1" / "marking.json"
        if marked.exists():
            import json

            marked_ui = json.loads(marked.read_text()).get("ui")
    except Exception:
        marked_ui = None

    software = widgets.Dropdown(
        description="Software",
        options=WEBUI_CHOICES,
        value=marked_ui if marked_ui in WEBUI_CHOICES else "Forge-Neo",
        layout=widgets.Layout(width="420px"),
        style={"description_width": "90px"},
    )
    skip_comfy = widgets.Checkbox(value=False, description="Skip ComfyUI dependency check")
    ngrok = _text("Ngrok token", password=True, placeholder="Optional")
    zrok = _text("Zrok token", password=True, placeholder="Optional")
    preview = widgets.HTML()
    run_button = _button("Launch WebUI", "success")
    out = widgets.Output()

    def build_args():
        args = LAUNCH_ARGS.get(software.value, "")
        if skip_comfy.value:
            args += " --skip-comfyui-check"
        if ngrok.value.strip():
            args += f" --N={shlex.quote(ngrok.value.strip())}"
        if zrok.value.strip():
            args += f" --Z={shlex.quote(zrok.value.strip())}"
        return args.strip()

    def refresh(_=None):
        preview.value = f"<code>{build_args()}</code>"

    def run(_):
        with out:
            clear_output(wait=True)
            webui_path = _ns("WebUI", required=True)
            home = Path(_ns("HOME", Path(webui_path).parent))
            selected_path = home / software.value
            if selected_path.exists():
                webui_path = selected_path
                _ip().user_ns["WebUI"] = selected_path
                marked = home / "gutris1" / "marking.json"
                if marked.exists():
                    import json

                    data = json.loads(marked.read_text())
                    data["ui"] = software.value
                    marked.write_text(json.dumps(data, indent=4))
            else:
                print(f"{selected_path} does not exist; using current WebUI path: {webui_path}")
            args = build_args()
            print(f"Launching {software.value} with args: {args}")
            _ip().run_line_magic("cd", f"-q {shlex.quote(str(webui_path))}")
            _ip().run_line_magic("run", f"segsmaker.py {args}")

    for item in [software, skip_comfy, ngrok, zrok]:
        item.observe(refresh, names="value")
    run_button.on_click(run)
    refresh()
    display(widgets.VBox([software, skip_comfy, ngrok, zrok, preview, run_button, out]))


def display_zipper():
    name = _text("Zip name", "my_outputs", "e.g. my_outputs_2026")
    run_button = _button("Zip Outputs")
    out = widgets.Output()

    def run(_):
        with out:
            clear_output(wait=True)
            zip_name = name.value.strip() or "my_outputs"
            output_dir = _ns("WebUI_Output", required=True)
            home = _ns("HOME", os.getcwd())
            cell = f"name = {zip_name}\ninputs = {output_dir}\noutputs = {home}"
            _ip().run_cell_magic("zipping", "", cell)

    run_button.on_click(run)
    display(widgets.VBox([name, run_button, out]))
