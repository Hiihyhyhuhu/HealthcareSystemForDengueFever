# Recife data Engineer

## Overview

- **75,745** rows
- **59** columns

## Target distribution

- 'Other': **41,351**
- 'Dengue': **26,703**
- 'Chikungunya': **7,,068**

## Groups of features:

### Demographics

- `age` (years).
- `sex`: Male, Female.
- `pregnancy_status`: 'Not_applicable', 'Unknown', 'Not_pregnant', '2nd_trimester', '3rd_trimester', '1st_trimester', nan
- `race`: 'Unknown', 'White', 'Brown', nan, 'Indigenous', 'Asian', 'Black'
- `is_pregnant`: bool flag derived from pregnancy_status
- `female_x_pregnancy`: female and pregnant
- `high_risk_age`:

### Symptoms

- `fever`, `headache`, `myalgia`, `rash`, `nausea`, `vomiting`, `back_pain`, `conjunctivitis`, `arthritis`, `arthralgia`, `petechiae`, `leukopenia` (**removed**)

### Comorbidities

Known medical background conditions. These help estimate vulnerability and severity risk

- `diabetes`, `hypertension`, `hematologic_disease`, `kidney_disease`, `liver_disease`, `peptic_acid_disease`, `autoimmune_disease`,
- `metabolic_comorbidity_score`: diabetes + hypertension +
- `immunocompromised_flag`: Composite vulnerability flag for immune-risk conditions such as autoimmune, hematologic, kidney, or liver disease.

### Timeline day-difference features

- `sign_to_note`: Days from first symptom suspicion to self-treatment (e.g. son has a flu, family notice and put on some lotion or go to a clinic for light diagnosis).
- `sign_to_proper_care`: Days from first symptom suspicion to either registration or thorough clinic checkup.
- `note_to_proper_care` = `sign_to_proper_care` - `sign_to_note`: Days from notificatino to investigation. Proxy for urgency or system delay, not a pure home-observable symptom.

### Timeline bins and illness-window flags

Bins are: 0-1, 2-3, 4-5, 6-7, 8-14, 15-21, 22+

- `note_bin`: categorical bucket of `sign_to_note`
- `proper_care_bin`: categorical bucket of `sign_to_proper_care`
- `early_contact`: Flag for `sign_to_note` in [0, 3]
- `acute_window`: Flag for `sign_to_note` in [0, 7]
- `warning_window`: Flag for `sign_to_note` in [3, 7]
- `subacute_window`: Flag for `sign_to_note` in [8, 14]
- `persistent_over_14d`: Flag for `sign_to_note` > 14

### Disease timing suspicion

According to WHO, timing cues correlate greatly to these two diseases, where dengue would both be suspected if first symptom lasts for 0-7 days, whereas dengue would be alarming in the 3-7-day bucket and chikungunya would be notified between 8 to 14 days. This is due to the behavior of each disease, because after a week dengue-suffered patients enter Recovery phase.

- Note: Febrile (Days 1–3), Critical (Days 3–7), and Recovery (After Day 7)

### Seasonality features

Normally, mosquitoes-infectious diseases go rampant during rainy season. So, capturing timing behavior assist greatly in identifying the illness. **YET**, we need to convert **VN** season to **BRAZIL** season, by minusing by two months from VN-based month

- `onset_month_sin`: month of first symptom onset.
- `onset_dayofyear_sin`: Day of year of first symptom onset.
- `onset_quarter_sin`: Quarter of first symptom onset.
- `onset_weekofyear_sin`: Week of year of first symptom onset.
- `in_rainy_season`: If first symptom happens from March to August.

### Composite symptom scores and interactions

Higher-level engineered features combining symptoms, risk factors, or timing windows.

- `joint_score`: `myalgia` + `back_pain` + `arthritis` + `arthralgia`, represents the aches in bones and joints.
- `gi_score`: `nausea` + 2*`vomiting` + 0.75*`peptic_acid_disease` + 0.25\*(`kidney_disease` + `liver_disease`)
  Reason: said WHO/CDC, vomiting persistently is a strong indicator for dengue (usually 3 times in 24 hours). But since we do not know that information, we account a small buff for it. Since `peptic_acid_disease` relates to GERD (**reflux**) and `kidney or liver-disease` people usually experience abdominal pain, we assign small weights.

* Sources: GSRS scale calcs 5 clusters: reflux, abdominal pain, indigestion, diarrhea, and constipation. **GSRS_AstraZeneca.pdf**

- `dengue_triad`: Composite dengue-like symptom pattern flag/score. (fever + headache + myalgia + retroorbital)
- `dengue_warning_triad`: `warning_window` + `gi_score` + `petechiae` + `retroorbital`
- `chik_triad` = `fever` + 2 x max(`rash`, `conjunctivitis`) + max(`arthralgia`, `arthritis`) + 0.5 x `myalgia`: esp joint-centered illness
- `total_symptom_burden`: total appearances of symptoms and risks
- `joint_gi_ratio` = `joint_score` / (`gi_score` + 1): Ratio comparing joint symptom burden to GI symptom burden
- `dengue_warning_time_x_petechiae`
- `age_x_arthritis`: captures whether joint inflammation has different meaning across ages.

## Modeling cautions

- `days_onset_to_investigation` and `days_notification_to_investigation` may leak healthcare workflow information if not carefully converted to home-stage data.
- `leukopenia` and `tourniquet_test` require lab info.
- `pregnancy_status`, `quarter_sin`, and `quarter_cos` have relatively high missingness; imputation or missing indicators may be needed.
- Class imbalance exists: Chikungunya is much smaller than Other and Dengue, so use balanced metrics such as macro F1 and balance accuracy.
