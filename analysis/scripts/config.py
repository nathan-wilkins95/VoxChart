# voxchart_roi/scripts/config.py
# Central assumptions — edit these to customize the analysis

SHIFT_HOURS          = 12       # hours per nursing shift
SHIFTS_PER_MONTH     = 20       # average shifts per nurse per month
OT_RATE              = 54.00    # RN overtime hourly rate ($)
RN_REPLACEMENT_COST  = 61110    # cost to replace one bedside RN ($)
TURNOVER_RATE        = 0.164    # national RN annual turnover rate
VOXCHART_COST_MONTH  = 1000     # VoxChart unit plan monthly cost ($)
UNIT_SIZES           = [10, 20, 30, 40, 50]  # nurses per unit scenarios
SAVINGS_SCENARIOS    = {
    "Conservative (15 min)": 15,
    "Moderate (25 min)":     25,
    "Optimistic (35 min)":   35,
}
PROJECTION_YEARS     = 5
RNS_RETAINED_PER_YR  = 1       # assumed nurse retention improvement per unit/yr
