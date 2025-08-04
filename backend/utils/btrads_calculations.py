"""
BT-RADS Calculation Utilities
Quantitative functions for BT-RADS scoring based on volume data and dates
"""
from datetime import datetime, date
from typing import Tuple, Optional, Union
import logging

logger = logging.getLogger(__name__)

# Clinical significance threshold
MIN_SIGNIFICANT_ABS_CHANGE = 1.0  # 1 ml = 1 x 1 x 1 cm = measurable disease

def apply_enhancement_priority_rule(
    flair_change_pct: float,
    enh_change_pct: float,
    baseline_flair: Optional[float] = None,
    baseline_enh: Optional[float] = None,
    followup_flair: Optional[float] = None,
    followup_enh: Optional[float] = None
) -> Tuple[str, str]:
    """
    Apply enhancement priority rule for imaging assessment.
    
    Key rules:
    1. NEGATIVE percentage = DECREASED volume = IMPROVEMENT
    2. POSITIVE percentage = INCREASED volume = WORSENING
    3. Mixed patterns: Enhancement changes take priority
    4. Absolute changes < 1ml are not clinically significant
    
    Returns:
        Tuple of (assessment, reasoning)
        assessment: "improved", "unchanged", "worse", or "unknown"
    """
    try:
        flair_val = float(flair_change_pct)
        enh_val = float(enh_change_pct)
    except (ValueError, TypeError):
        return "unknown", "Cannot parse volume changes"
    
    # Calculate absolute volume changes if data available
    flair_abs_change = None
    enh_abs_change = None
    
    if baseline_flair is not None and followup_flair is not None:
        try:
            flair_abs_change = float(followup_flair) - float(baseline_flair)
        except (ValueError, TypeError):
            pass
    
    if baseline_enh is not None and followup_enh is not None:
        try:
            enh_abs_change = float(followup_enh) - float(baseline_enh)
        except (ValueError, TypeError):
            pass
    
    # Determine direction with absolute volume validation
    def get_direction_with_validation(pct_change: float, abs_change: Optional[float] = None) -> Tuple[str, str]:
        """Determine direction considering both percentage and absolute changes"""
        if abs_change is not None:
            # If absolute change is less than 1 ml, consider stable
            if abs(abs_change) < MIN_SIGNIFICANT_ABS_CHANGE:
                return "stable", f"Absolute change {abs_change:.2f}ml < 1ml threshold"
        
        # Standard percentage-based logic
        if pct_change > 10:
            return "up", f"Increased {pct_change:.1f}%"
        elif pct_change < -10:
            return "down", f"Decreased {pct_change:.1f}%"
        else:
            return "stable", f"Stable {pct_change:.1f}% (within ±10%)"
    
    # Get directions with validation
    flair_direction, flair_reason = get_direction_with_validation(flair_val, flair_abs_change)
    enh_direction, enh_reason = get_direction_with_validation(enh_val, enh_abs_change)
    
    # Check for mixed pattern
    if flair_direction != enh_direction and flair_direction != "stable" and enh_direction != "stable":
        # Mixed pattern - prioritize enhancement
        logger.info(f"Mixed pattern detected: FLAIR {flair_direction}, Enhancement {enh_direction}")
        logger.info("Applying enhancement priority rule")
        
        if enh_direction == "up":
            return "worse", f"Mixed pattern - Enhancement priority: ENH {enh_reason}"
        else:  # enh_direction == "down"
            return "improved", f"Mixed pattern - Enhancement priority: ENH {enh_reason}"
    
    # Standard logic for non-mixed patterns
    if flair_direction == "up" or enh_direction == "up":
        reasons = []
        if flair_direction == "up":
            reasons.append(f"FLAIR {flair_reason}")
        if enh_direction == "up":
            reasons.append(f"ENH {enh_reason}")
        return "worse", " and ".join(reasons)
    elif flair_direction == "down" or enh_direction == "down":
        reasons = []
        if flair_direction == "down":
            reasons.append(f"FLAIR {flair_reason}")
        if enh_direction == "down":
            reasons.append(f"ENH {enh_reason}")
        return "improved", " and ".join(reasons)
    else:
        return "unchanged", f"FLAIR {flair_reason}, ENH {enh_reason}"


def calculate_days_between(date_a: Union[str, date], date_b: Union[str, date]) -> int:
    """
    Calculate days between two dates.
    
    Args:
        date_a: Earlier date (e.g., radiation completion)
        date_b: Later date (e.g., followup imaging)
    
    Returns:
        Number of days between dates, or -1 if parsing fails
    """
    def parse_date(d: Union[str, date]) -> Optional[date]:
        if isinstance(d, date):
            return d
        
        for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m/%d/%y", "%m-%d-%Y", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(str(d), fmt).date()
            except ValueError:
                continue
        return None
    
    parsed_a = parse_date(date_a)
    parsed_b = parse_date(date_b)
    
    if parsed_a and parsed_b:
        return (parsed_b - parsed_a).days
    else:
        logger.warning(f"Could not parse dates: {date_a} or {date_b}")
        return -1


def determine_radiation_timing(days_since_radiation: int) -> Tuple[str, str]:
    """
    Apply BT-RADS 90-day rule for radiation timing.
    
    Returns:
        Tuple of (timing, reasoning)
        timing: "within_90_days", "beyond_90_days", or "unknown"
    """
    if days_since_radiation < 0:
        return "unknown", "Radiation date unknown or calculation failed"
    elif days_since_radiation < 90:
        return "within_90_days", f"{days_since_radiation} days since radiation (<90 days)"
    else:
        return "beyond_90_days", f"{days_since_radiation} days since radiation (≥90 days)"


def determine_component_worsening(
    flair_change_pct: float,
    enh_change_pct: float
) -> Tuple[str, str]:
    """
    Determine which components show worsening for BT-RADS.
    
    Returns:
        Tuple of (component, reasoning)
        component: "flair_or_enh", "flair_and_enh", or "unknown"
    """
    try:
        flair_val = float(flair_change_pct)
        enh_val = float(enh_change_pct)
    except (ValueError, TypeError):
        return "unknown", "Cannot parse volume changes"
    
    # Significant increase = >+10% positive change
    flair_worse = flair_val > 10
    enh_worse = enh_val > 10
    
    if flair_worse and enh_worse:
        return "flair_and_enh", f"Both components worse: FLAIR +{flair_val:.1f}%, ENH +{enh_val:.1f}%"
    elif flair_worse or enh_worse:
        if flair_worse:
            return "flair_or_enh", f"FLAIR worse: +{flair_val:.1f}% (ENH {enh_val:+.1f}%)"
        else:
            return "flair_or_enh", f"Enhancement worse: +{enh_val:.1f}% (FLAIR {flair_val:+.1f}%)"
    else:
        return "unknown", f"No significant worsening: FLAIR {flair_val:+.1f}%, ENH {enh_val:+.1f}%"


def apply_40_percent_rule(
    flair_change_pct: float,
    enh_change_pct: float
) -> Tuple[str, str]:
    """
    Apply BT-RADS 40% threshold rule for extent analysis.
    
    Returns:
        Tuple of (extent, reasoning)
        extent: "major" (≥40%), "minor" (<40%), or "unknown"
    """
    try:
        flair_val = float(flair_change_pct)
        enh_val = float(enh_change_pct)
    except (ValueError, TypeError):
        return "unknown", "Cannot parse volume changes"
    
    # Take the larger of the two increases
    max_increase = max(flair_val, enh_val)
    
    if max_increase >= 40:
        component = "FLAIR" if flair_val >= 40 else "Enhancement"
        return "major", f"{component} increased {max_increase:.1f}% (≥40% threshold)"
    elif max_increase > 0:
        return "minor", f"Maximum increase {max_increase:.1f}% (<40% threshold)"
    else:
        return "unknown", f"No positive changes to evaluate: FLAIR {flair_val:+.1f}%, ENH {enh_val:+.1f}%"


def get_btrads_score(
    algorithm_path: str,
    imaging_assessment: str,
    medication_status: Optional[str] = None,
    radiation_timing: Optional[str] = None,
    component_worsening: Optional[str] = None,
    extent: Optional[str] = None,
    progression_pattern: Optional[str] = None
) -> Tuple[str, str]:
    """
    Determine final BT-RADS score based on algorithm path.
    
    Returns:
        Tuple of (score, reasoning)
    """
    # Node 1: No suitable prior
    if "suitable_prior" in algorithm_path and "BT-0" in algorithm_path:
        return "0", "No suitable prior imaging for comparison"
    
    # Node 2: Imaging assessment
    if imaging_assessment == "unchanged":
        return "2", "Stable disease - no significant change"
    
    # Improved pathway
    if imaging_assessment == "improved":
        # Check medications
        if medication_status == "avastin":
            # TODO: Need Avastin response type (first vs sustained)
            return "1b", "Improvement on Avastin (medication effect)"
        elif medication_status == "increasing_steroids":
            return "1b", "Improvement with increasing steroids (medication effect)"
        else:
            return "1a", "True tumor improvement (no medication effects)"
    
    # Worse pathway
    if imaging_assessment == "worse":
        # Check radiation timing
        if radiation_timing == "within_90_days":
            return "3a", "Worsening within 90 days of radiation (favor treatment effect)"
        
        # Component analysis
        if component_worsening == "flair_or_enh":
            return "3b", "Indeterminate progression (only one component worse)"
        elif component_worsening == "flair_and_enh":
            # Extent analysis
            if extent == "major":
                return "4", "Highly suspicious for tumor progression (>40% increase)"
            elif extent == "minor":
                # Progression pattern
                if progression_pattern == "yes":
                    return "4", "Progressive disease over multiple studies"
                else:
                    return "3c", "Favors tumor but not clearly progressive"
    
    # Fallback
    return "3b", "Indeterminate (insufficient data for definitive classification)"