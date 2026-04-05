"""Transformer fusion (Option B): feature embeddings as tokens → unified match representation."""

import torch
from torch import Tensor, nn

from football_ml.base import FusionModule
from football_ml.config import FusionConfig


class TransformerFusion(FusionModule):
    """Fuse feature embeddings using a transformer encoder.

    Each feature group embedding becomes a token. Self-attention allows
    cross-feature interaction (e.g., player form attending to opponent strength).
    Handles variable numbers of input tokens, supporting modular feature toggling.
    """

    def __init__(self, config: FusionConfig) -> None:
        super().__init__()
        self.output_dim = config.output_dim
        self.d_model = config.d_model

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=config.d_model,
            nhead=config.nhead,
            dim_feedforward=config.d_model * 4,
            batch_first=True,
        )
        self.transformer = nn.TransformerEncoder(
            encoder_layer,
            num_layers=config.num_layers,
        )
        self.output_projection = nn.Linear(config.d_model, config.output_dim)

    def forward(self, embeddings: list[Tensor]) -> Tensor:
        """Fuse feature embeddings via transformer self-attention.

        Each embedding is projected to d_model, stacked as tokens, passed
        through the transformer encoder, then mean-pooled and projected.

        Args:
            embeddings: List of tensors, each (batch, embed_dim).
                        Embed dims may differ; each is projected to d_model.

        Returns:
            Fused match representation of shape (batch, output_dim).
        """
        # Lazily create projection layers for each input dimension
        if not hasattr(self, "_input_projections"):
            self._input_projections = nn.ModuleList()
        while len(self._input_projections) < len(embeddings):
            dim = embeddings[len(self._input_projections)].shape[-1]
            proj = nn.Linear(dim, self.d_model).to(embeddings[0].device)
            self._input_projections.append(proj)

        # Project each embedding to d_model and stack as sequence
        tokens = []
        for i, emb in enumerate(embeddings):
            tokens.append(self._input_projections[i](emb))
        # (batch, num_tokens, d_model)
        token_seq = torch.stack(tokens, dim=1)

        # Transformer encoder
        encoded = self.transformer(token_seq)

        # Mean pool over tokens → single vector
        pooled = encoded.mean(dim=1)

        return self.output_projection(pooled)
