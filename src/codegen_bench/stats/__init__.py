"""Statistical analysis components."""

from codegen_bench.stats.correction import correct_pvalues, dunnett_test, estimate_fdr
from codegen_bench.stats.effect_size import EffectSize, cohens_h, hedges_g
from codegen_bench.stats.pareto import (
    ParetoResult,
    analyze_pareto_frontier,
    calculate_hypervolume,
    find_pareto_front,
    get_pareto_visualization_data,
    is_dominated,
)
from codegen_bench.stats.power import (
    PowerAnalysisResult,
    calculate_minimum_detectable_effect,
    calculate_power_proportion,
    calculate_power_ttest,
    calculate_sample_size_proportion,
    calculate_sample_size_ttest,
    interpret_power,
)
from codegen_bench.stats.variance import (
    VarianceComponents,
    calculate_variance_explained_by_factor,
    decompose_variance,
)

__all__ = [
    "EffectSize",
    "ParetoResult",
    "PowerAnalysisResult",
    "VarianceComponents",
    "analyze_pareto_frontier",
    "calculate_hypervolume",
    "calculate_minimum_detectable_effect",
    "calculate_power_proportion",
    "calculate_power_ttest",
    "calculate_sample_size_proportion",
    "calculate_sample_size_ttest",
    "calculate_variance_explained_by_factor",
    "cohens_h",
    "correct_pvalues",
    "decompose_variance",
    "dunnett_test",
    "estimate_fdr",
    "find_pareto_front",
    "get_pareto_visualization_data",
    "hedges_g",
    "interpret_power",
    "is_dominated",
]
