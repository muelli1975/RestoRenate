"""Register the pinned Nunchaku Qwen-Image loader for RestoRenate."""
from .nodes.models.qwenimage import NunchakuQwenImageDiTLoader

NODE_CLASS_MAPPINGS = {"NunchakuQwenImageDiTLoader": NunchakuQwenImageDiTLoader}
