"""Runtime provenance without assuming the checkout equals historical inference."""
import importlib.metadata
import subprocess
from pathlib import Path


def runtime_provenance(wrapper):
    root = Path(__file__).resolve().parents[2]
    try:
        commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
        dirty = bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=root, text=True).strip())
    except (OSError, subprocess.CalledProcessError):
        commit, dirty = None, None
    try:
        version = importlib.metadata.version('transformers')
    except importlib.metadata.PackageNotFoundError:
        version = None
    tokenizer = getattr(wrapper, 'tokenizer', None)
    model = getattr(wrapper, 'model', None)
    kwargs = wrapper.chat_template_configuration() if hasattr(wrapper, 'chat_template_configuration') else {}
    template = getattr(tokenizer, 'chat_template', None)
    return dict(git_commit=commit, git_dirty=dirty, transformers_version=version,
        model_revision=getattr(getattr(model, 'config', None), '_commit_hash', None),
        tokenizer_revision=getattr(tokenizer, 'init_kwargs', {}).get('_commit_hash'),
        thinking_enabled=kwargs.get('enable_thinking') if template else None,
        chat_template_configuration=kwargs, chat_template=template)
