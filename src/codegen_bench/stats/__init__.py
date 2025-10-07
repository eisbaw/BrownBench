"""Statistical analysis components."""

from codegen_bench.stats.correction import correct_pvalues, dunnett_test, estimate_fdr
from codegen_bench.stats.effect_size import EffectSize, cohens_h, hedges_g

__all__ = [
    "EffectSize",
    "cohens_h",
    "correct_pvalues",
    "dunnett_test",
    "estimate_fdr",
    "hedges_g",
]
