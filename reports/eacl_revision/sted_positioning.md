# STED citation and positioning

Use the accompanying `sted_reference.bib` entry for the arXiv version. The
[author manuscript](https://arxiv.org/abs/2512.23712) lists Guanghui Wang as first
author; the [Amazon Science publication record](https://www.amazon.science/publications/sted-and-consistency-scoring-a-framework-for-evaluating-llm-structured-output-reliability)
uses Gordon Wang and identifies the NeurIPS 2025 workshop venue. The BibTeX
consistently follows the cited arXiv record rather than mixing the two records.

The [full manuscript, sections 3.1–3.7](https://arxiv.org/html/2512.23712v1)
describes semantic tree comparison, assignment-based matching and aggregation
across repeated outputs for identical inputs. It addresses semantic and structural
similarity and provides diagnostic analysis; it should not be characterized as
merely a binary validator or as lacking diagnostic information.

Suggested related-work paragraph:

> Wang et al. (2025) introduce Semantic Tree Edit Distance (STED) and consistency
> scoring for structured outputs, combining semantic matching with structural
> comparison and aggregating repeated generations. Our study complements this
> approach by reporting concurrent diagnostic error families and opportunity-based
> rates across benchmarks and prompting conditions. We analyze archived task
> outputs rather than estimating repeated-generation consistency for identical
> prompts, and do not claim a direct performance comparison with STED.

Add this paragraph near evaluation metrics in Related Work and use
`\citep{wang2025sted}`. No STED scores, embedding calls, new model generations
or claimed superiority were added to the experiment.
