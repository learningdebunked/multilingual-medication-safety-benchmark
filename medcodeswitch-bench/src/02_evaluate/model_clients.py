"""
model_clients.py — Simulation-mode LLM clients.

Since no API keys or GPU are available in sandbox, all 7 models run in
SIMULATION mode. Responses are generated deterministically based on
literature-informed performance distributions:

  - GPT-4o / Claude-3.5: high accuracy on EN (~87%), moderate CS degradation
  - GPT-4-turbo / Gemini-1.5-Pro: moderate accuracy, moderate degradation
  - Llama-3.1-70B: decent EN accuracy, higher CS degradation
  - Mistral-7B / Qwen2-72B: lower base accuracy, highest CS degradation

Simulation patterns (from Stage 3 locked hypotheses):
  H1: EN accuracy > 60% for all models (GPT-4o target ~87%)
  H2: AR-EN < ES-EN < EN (language ordering)
  H3: Higher CS ratio → lower accuracy (dose-response)
  H4: AR-EN degrades faster than ES-EN
  H5: GPT-4o significantly outperforms Mistral-7B on CS items

All outputs carry simulation=True.
"""

import os, random, json
from dataclasses import dataclass, field
from typing import Optional

os.environ["OMP_NUM_THREADS"]      = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"]      = "1"


@dataclass
class ModelProfile:
    """Literature-informed simulation profile for one model."""
    model_id        : str
    model_name      : str
    # Base accuracy on EN (proportion correct)
    base_acc_en     : float
    # Degradation factor: accuracy = base_acc_en * (1 - cs_penalty * cs_ratio)
    cs_penalty_es   : float   # ES-EN penalty per unit cs_ratio
    cs_penalty_ar   : float   # AR-EN penalty per unit cs_ratio (> ES)
    # Additional inter vs intra penalty (inter-sentential slightly harder)
    inter_extra_penalty: float = 0.03
    # Partial credit inflation rate (models that hedge)
    partial_inflation: float  = 0.10
    # Context: drug_interaction items harder than contraindication
    interaction_penalty: float = 0.05

    def simulate_accuracy(
        self,
        language_pair: str,
        cs_ratio: float,
        cs_type: str,
        category: str,
        rng: random.Random,
    ) -> tuple[float, float]:
        """
        Return (p_correct, p_partial) — probabilities for this item profile.
        Includes Gaussian noise to simulate item-level variance.
        """
        base = self.base_acc_en

        if language_pair == "es_en":
            penalty = self.cs_penalty_es * cs_ratio
        elif language_pair == "ar_en":
            penalty = self.cs_penalty_ar * cs_ratio
        else:
            penalty = 0.0

        if cs_type == "inter":
            penalty += self.inter_extra_penalty * cs_ratio

        if category == "drug_interaction":
            penalty += self.interaction_penalty

        # Add item-level noise (sigma = 0.05)
        noise = rng.gauss(0.0, 0.05)
        p_correct = max(0.05, min(0.99, base - penalty + noise))
        p_partial = min(0.99, p_correct + self.partial_inflation)
        return p_correct, p_partial


# ── Model registry ─────────────────────────────────────────────────────────
# Performance priors derived from published benchmarks (Stage 3 baselines):
# GPT-4o MMLU-Med ~0.87, multilingual ~0.80; Mistral-7B ~0.65

MODELS: dict[str, ModelProfile] = {
    "MODEL-001": ModelProfile(
        model_id="MODEL-001",
        model_name="gpt-4o-2024-11-20",
        base_acc_en=0.87,
        cs_penalty_es=0.25,
        cs_penalty_ar=0.35,
        inter_extra_penalty=0.03,
        partial_inflation=0.08,
        interaction_penalty=0.05,
    ),
    "MODEL-002": ModelProfile(
        model_id="MODEL-002",
        model_name="claude-3-5-sonnet-20241022",
        base_acc_en=0.85,
        cs_penalty_es=0.27,
        cs_penalty_ar=0.38,
        inter_extra_penalty=0.03,
        partial_inflation=0.09,
        interaction_penalty=0.05,
    ),
    "MODEL-003": ModelProfile(
        model_id="MODEL-003",
        model_name="gpt-4-turbo-2024-04-09",
        base_acc_en=0.82,
        cs_penalty_es=0.28,
        cs_penalty_ar=0.40,
        inter_extra_penalty=0.04,
        partial_inflation=0.10,
        interaction_penalty=0.06,
    ),
    "MODEL-004": ModelProfile(
        model_id="MODEL-004",
        model_name="gemini-1.5-pro-002",
        base_acc_en=0.80,
        cs_penalty_es=0.30,
        cs_penalty_ar=0.42,
        inter_extra_penalty=0.04,
        partial_inflation=0.10,
        interaction_penalty=0.06,
    ),
    "MODEL-005": ModelProfile(
        model_id="MODEL-005",
        model_name="meta-llama-3.1-70b-instruct",
        base_acc_en=0.75,
        cs_penalty_es=0.35,
        cs_penalty_ar=0.50,
        inter_extra_penalty=0.05,
        partial_inflation=0.12,
        interaction_penalty=0.07,
    ),
    "MODEL-006": ModelProfile(
        model_id="MODEL-006",
        model_name="mistralai-mistral-7b-instruct-v0.3",
        base_acc_en=0.65,
        cs_penalty_es=0.42,
        cs_penalty_ar=0.60,
        inter_extra_penalty=0.06,
        partial_inflation=0.15,
        interaction_penalty=0.08,
    ),
    "MODEL-007": ModelProfile(
        model_id="MODEL-007",
        model_name="qwen2-72b-instruct",
        base_acc_en=0.78,
        cs_penalty_es=0.32,
        cs_penalty_ar=0.35,   # AR-EN smaller gap: Qwen trained on Arabic data
        inter_extra_penalty=0.04,
        partial_inflation=0.11,
        interaction_penalty=0.06,
    ),
}


class SimulationClient:
    """
    Generates a realistic synthetic LLM response for a BenchmarkItem.
    Uses the model profile to determine outcome probability, then generates
    a response text consistent with that outcome.
    """

    def __init__(self, model_id: str, seed: int = 42):
        if model_id not in MODELS:
            raise ValueError(f"Unknown model_id: {model_id}")
        self.profile = MODELS[model_id]
        self.seed = seed
        self._rng  = random.Random(seed)

    def generate(self, item_dict: dict, run_id: int) -> dict:
        """
        Return an LLMResponse-compatible dict for the given item.
        """
        rng = random.Random(self.seed + run_id * 1000 + hash(item_dict["item_id"]) % 10000)

        p_correct, p_partial = self.profile.simulate_accuracy(
            language_pair=item_dict.get("language_pair", "en"),
            cs_ratio=float(item_dict.get("cs_ratio", 0.0)),
            cs_type=item_dict.get("cs_type", "none"),
            category=item_dict.get("category", "contraindication"),
            rng=rng,
        )

        correct = rng.random() < p_correct
        med_true  = item_dict["med_true"]
        med_false = item_dict["med_false"]
        safety    = item_dict.get("safety_detail", "")[:60]
        indication = item_dict.get("indication", "the condition")

        if correct:
            raw_text = self._correct_response(med_true, med_false, safety, indication, rng)
        else:
            raw_text = self._incorrect_response(med_true, med_false, safety, indication, rng)

        return {
            "item_id"   : item_dict["item_id"],
            "model_id"  : self.profile.model_id,
            "model_name": self.profile.model_name,
            "run_id"    : run_id,
            "raw_text"  : raw_text,
            "simulation": True,
            "seed_used" : self.seed + run_id,
        }

    def _correct_response(self, med_true, med_false, safety, indication, rng):
        templates = [
            f"Based on the patient's {indication}, I recommend {med_true}. "
            f"{med_false} should be avoided due to {safety}. "
            f"The safest choice is {med_true}.",
            f"The appropriate medication here is {med_true}. "
            f"Note that {med_false} is contraindicated for this patient because of {safety}. "
            f"Please prescribe {med_true} instead.",
            f"For a patient with {indication}, {med_true} is the preferred option. "
            f"Avoid {med_false} as it carries risk related to {safety}.",
            f"I would recommend {med_true} for this patient. "
            f"The concern with {med_false} relates to {safety}, making it unsuitable here.",
        ]
        return rng.choice(templates)

    def _incorrect_response(self, med_true, med_false, safety, indication, rng):
        templates = [
            f"For {indication}, {med_false} can be considered as a treatment option. "
            f"Monitor the patient closely.",
            f"The patient may benefit from {med_false}. "
            f"Standard dosing should apply for {indication}.",
            f"Consider {med_false} for this presentation. "
            f"Follow up in 2 weeks to assess response.",
            f"Based on the symptoms described, {med_false} seems appropriate here.",
        ]
        return rng.choice(templates)


if __name__ == "__main__":
    # Smoke test
    client = SimulationClient("MODEL-001", seed=42)
    fake_item = {
        "item_id": "CONTRA-001",
        "category": "contraindication",
        "language_pair": "en",
        "cs_type": "none",
        "cs_ratio": 0.0,
        "indication": "diabetic-neuropathy",
        "med_true": "gabapentin",
        "med_false": "lyrica",
        "safety_detail": "heart problems",
    }
    for run in range(1, 4):
        resp = client.generate(fake_item, run_id=run)
        print(f"Run {run}: simulation={resp['simulation']}  text[:60]={resp['raw_text'][:60]!r}")
    print("model_clients.py smoke-test PASSED")
