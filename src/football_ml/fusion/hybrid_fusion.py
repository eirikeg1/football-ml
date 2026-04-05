"""Hybrid fusion (Option C): project per group, then transformer encoder."""

import torch
from torch import Tensor, nn

from football_ml.base import FusionModule
from football_ml.config import FusionConfig


class HybridFusion(FusionModule):
    """Hybrid fusion with explicit per-group projection before transformer.

    Unlike TransformerFusion which lazily creates projections, this variant
    takes explicit group dimensions at init time and creates dedicated
    projection + normalization per group before the transformer encoder.
    """

    def __init__(self, config: FusionConfig, group_dims: list[int]) -> None:
        super().__init__()
        self.output_dim = config.output_dim
        self.d_model = config.d_model

        # Per-group projection with layer norm
        self.group_projections = nn.ModuleList()
        for dim in group_dims:
            self.group_projections.append(
                nn.Sequential(
                    nn.Linear(dim, config.d_model),
                    nn.LayerNorm(config.d_model),
                    nn.ReLU(),
                )
            )

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
        """Fuse feature embeddings via per-group projection then transformer.

        Args:
            embeddings: List of tensors, each (batch, group_dim_i).
                        Must match the group_dims provided at init.

        Returns:
            Fused match representation of shape (batch, output_dim).
        """
        tokens = []
        for proj, emb in zip(self.group_projections, embeddings):
            tokens.append(proj(emb))

        token_seq = torch.stack(tokens, dim=1)
        encoded = self.transformer(token_seq)
        pooled = encoded.mean(dim=1)

        return self.output_projection(pooled)
