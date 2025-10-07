"""Statistical analysis components."""

from codegen_bench.stats.correction import correct_pvalues, dunnett_test, estimate_fdr
from codegen_bench.stats.effect_size import EffectSize, cohens_h, hedges_g
from codegen_bench.stats.variance import (
    VarianceComponents,
    calculate_variance_explained_by_factor,
    decompose_variance,
)

__all__ = [
    "EffectSize",
    "VarianceComponents",
    "calculate_variance_explained_by_factor",
    "cohens_h",
    "correct_pvalues",
    "decompose_variance",
    "dunnett_test",
    "estimate_fdr",
    "hedges_g",
]
