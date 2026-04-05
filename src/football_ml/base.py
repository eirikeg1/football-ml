"""Base classes defining the interfaces for all pipeline components."""

from abc import ABC, abstractmethod

import torch
from torch import Tensor, nn


class FeatureExtractor(nn.Module, ABC):
    """Base class for all feature extractors (Layer 1).

    Feature extractors transform raw input data into fixed-size embeddings.
    Subclasses must set `output_dim` and implement `forward`.
    """

    output_dim: int

    @abstractmethod
    def forward(self, *args, **kwargs) -> Tensor:
        """Produce an embedding tensor of shape (batch, output_dim)."""
        ...


class CompositionModule(nn.Module, ABC):
    """Base class for composition models (Layer 2).

    Composition models combine individual embeddings (e.g., player-level)
    into a higher-level representation (e.g., team-level).
    """

    output_dim: int

    @abstractmethod
    def forward(self, *args, **kwargs) -> Tensor:
        """Produce a composed embedding tensor."""
        ...


class FusionModule(nn.Module, ABC):
    """Base class for fusion layers (Layer 3).

    Fusion modules aggregate multiple feature embeddings into a single
    unified match representation. Implementations should handle variable
    numbers of input embeddings to support modular feature toggling.
    """

    output_dim: int

    @abstractmethod
    def forward(self, embeddings: list[Tensor]) -> Tensor:
        """Fuse a list of embeddings into a single match representation.

        Args:
            embeddings: List of tensors, each (batch, embed_dim).
                        Embed dims may differ across entries.

        Returns:
            Tensor of shape (batch, output_dim).
        """
        ...


class TemporalModule(nn.Module, ABC):
    """Base class for temporal models (Layer 4).

    Temporal modules process sequences of match representations to capture
    dynamics over time (form, trends, etc.).
    """

    output_dim: int

    @abstractmethod
    def forward(self, sequence: Tensor) -> Tensor:
        """Process a sequence of match representations.

        Args:
            sequence: Tensor of shape (batch, seq_len, input_dim).

        Returns:
            Tensor of shape (batch, output_dim).
        """
        ...


class PredictionHead(nn.Module, ABC):
    """Base class for prediction heads (Layer 5).

    Prediction heads produce task-specific outputs from the temporal state.
    """

    @abstractmethod
    def forward(self, temporal_state: Tensor) -> Tensor:
        """Produce predictions from temporal state.

        Args:
            temporal_state: Tensor of shape (batch, input_dim).

        Returns:
            Task-specific output tensor.
        """
        ...
