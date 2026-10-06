"""
Diagnostic tools for Biomedical Genetic Variant Classification.
Provides deterministic simulation of variant evidence queries.
"""

from typing import Dict, Any, List

def get_variant_tools(instance_data: Dict[str, Any]):
    variant = instance_data["variant"]
    gene_rules = instance_data["gene_rules"]
    
    def population_frequency_tool() -> Dict[str, Any]:
        """Query gnomAD and ExAC for overall and continental ancestry allele frequencies."""
        inst_id = instance_data["instance_id"]
        # In later perturbations, population frequencies can change
        return {
            "gene": variant["gene"],
            "variant": variant["hgvs_c"],
            "gnomad_overall_af": 0.008 if inst_id == "biomed-001" else (0.082 if inst_id == "biomed-003" else 0.00001),
            "subpopulation_frequencies": {
                "SAS": 0.014 if inst_id == "biomed-006" else 0.00002,
                "AFR": 0.082 if inst_id == "biomed-003" else 0.00001,
                "NFE": 0.006 if inst_id == "biomed-004" else 0.00001
            },
            "homozygote_count": 12 if inst_id == "biomed-001" else 0
        }

    def insilico_predictor_tool() -> Dict[str, Any]:
        """Query computational effect scores: REVEL, AlphaMissense, SpliceAI, CADD."""
        inst_id = instance_data["instance_id"]
        return {
            "variant": variant["hgvs_c"],
            "revel_score": 0.44 if inst_id == "biomed-008" else 0.88,
            "cadd_phred": 28.4,
            "splice_ai_delta": 0.00 if inst_id == "biomed-003" else (0.82 if inst_id == "biomed-004" else 0.05),
            "consensus": "benign" if inst_id in ["biomed-003", "biomed-006"] else "damaging"
        }

    def functional_assay_tool() -> Dict[str, Any]:
        """Query in vitro and in vivo functional assay experimental readouts."""
        inst_id = instance_data["instance_id"]
        if inst_id == "biomed-004":
            return {"assay": "Mini-gene and RNA sequencing", "result": "Normal full-length splicing 100%", "interpretation": "non-damaging"}
        elif inst_id == "biomed-006":
            return {"assay": "Primary fibroblast radiolabeled LDL uptake", "result": "98% wild-type activity", "interpretation": "non-damaging"}
        elif inst_id == "biomed-007":
            return {"assay": "BRCA1 transactivation assay", "result": "Partial activity ~22% (intermediate)", "interpretation": "intermediate"}
        elif inst_id == "biomed-008":
            return {"assay": "Patch clamp with KCNE1 beta-subunit", "result": "Severe loss of I_Ks current", "interpretation": "damaging"}
        elif inst_id == "biomed-009":
            return {"assay": "Saturation mutagenesis transactivation", "result": "Severe loss of transactivation on 8 promoters", "interpretation": "damaging"}
        elif inst_id == "biomed-010":
            return {"assay": "In Vitro Contracture Test (IVCT)", "result": "Halothane/caffeine hyper-contracture positive", "interpretation": "damaging"}
        else:
            return {"assay": "Standard functional assay", "result": "Severe functional disruption", "interpretation": "damaging"}

    def clinical_evidence_tool() -> Dict[str, Any]:
        """Query patient case reports, cosegregation pedigrees, and disease registry records."""
        inst_id = instance_data["instance_id"]
        return {
            "condition": variant["condition"],
            "lod_score": 4.2 if inst_id == "biomed-005" else (0.4 if inst_id == "biomed-004" else 2.1),
            "unrelated_proband_count": 8 if inst_id in ["biomed-001", "biomed-005", "biomed-008"] else 1,
            "co_occurrence_in_trans": True if inst_id == "biomed-007" else False,
            "phenotype_specificity": "high" if inst_id == "biomed-001" else "moderate"
        }

    def gene_guideline_tool() -> Dict[str, Any]:
        """Query gene-specific ClinGen VCEP rules and disease mechanism specifications."""
        return {
            "gene": variant["gene"],
            "loss_of_function_mechanism": gene_rules.get("loss_of_function_mechanism", True),
            "disallowed_criteria": gene_rules.get("disallowed_criteria", [])
        }

    return {
        "population_frequency_tool": population_frequency_tool,
        "insilico_predictor_tool": insilico_predictor_tool,
        "functional_assay_tool": functional_assay_tool,
        "clinical_evidence_tool": clinical_evidence_tool,
        "gene_guideline_tool": gene_guideline_tool
    }
