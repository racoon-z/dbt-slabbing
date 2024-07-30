import json

def get_ea1141_dbt_truths(json_file: str, gt_type: str = 'biopsy', scope: str = 'volume-wise',
                          dbt_only: bool = True, mri_excluded: bool = True):
    """
    Load EA1141 DBT ground truth labels. Many options are available to load :
    1. Only malignant observed DBTs => 'dbt_only' = True, False otherwise with the possibility to keep or discard
    ambiguous cases (positive MRI but negative DBT) => 'mri_excluded' = True, False otherwise
    2. Choose the scope for generating ground truths: 'volume-wise', 'breast-wise', or 'patient-wise'
    - Volume-wise mapping is done with <SOPInstanceUID> (e.g., "1.3.6.1.4.1.14519.5.2.1.1620.1225.270755204881277229058297916749")
    - Breast-wise mapping is done with <Subject-DE>-<StudyDate>-<Laterality> (e.g., "EA1141-7948334-R")
    - Patient-wise mapping is done with <Subject-DE>-<StudyDate> (e.g., "EA1141-7948334")
    We only kept DBTs from the first study exam (year 0). Thus, there is only one StudyDate per patient.
    3. Choose which ground_truth type you want to load: 'acr4+' or 'biopsy:
    - acr4+ consider malignant DBT only according to the radiologists BI-RADS risk assessment > 3
    - biopsy consider malignant DBT if the DBT is a biopsy-proven malignant case

    This function is based from the first DBT mapping in src/generate_mapping.py

    Return the mapping according to the chosen scope, ground-truth type, and 'dbt_only' / 'mri_excluded'.
    """
    mapped_labels = {}
    for uid, values in json.loads(json_file).items():
        birads_dbt, birads_mri = values['DBT_BIRADS'], values['MRI_BIRADS']
        # Exclude all ambiguous cases: when a breast laterality is BI-RADS 3+, then we throw other laterality to
        # avoid breasts for which no ground truth is available
        if birads_dbt is not None and birads_mri is not None:
            if not dbt_only:
                global_birads = max(birads_dbt, birads_mri)
            else:
                if mri_excluded:
                    global_birads = None if birads_mri > birads_dbt else birads_dbt
                else:
                    global_birads = birads_dbt
            ##
            if global_birads:
                # If a global_birads has been detected, in case where positive mri_birads (>= 3) are throw away
                global_birads = int(global_birads)
                global_truth = None
                if gt_type == 'biopsy':
                    # DBT exam with a biopsy resulting as a malignant tumor either for DBT or MRI
                    biopsy_dbt, biopsy_mri = values['DBT_Outcome'], values['MRI_Outcome']
                    undesirable_biopsy_outcomes = ['UNKNOWN', None]
                    if global_birads < 3:
                        global_outcome = [1, 0]
                    elif biopsy_dbt in undesirable_biopsy_outcomes and biopsy_mri in undesirable_biopsy_outcomes:
                        global_outcome = None
                    else:
                        dbt_outcome = 1 if biopsy_dbt == 'MALIGNANT' else 0
                        mri_outcome = 1 if biopsy_mri == 'MALIGNANT' else 0
                        if not dbt_only:
                            global_outcome = max(dbt_outcome, mri_outcome)
                        else:
                            if mri_excluded:
                                global_outcome = None if mri_outcome > dbt_outcome else dbt_outcome
                            else:
                                global_outcome = dbt_outcome
                    if global_outcome is not None:
                        global_truth = [0, 1] if global_outcome == 1 else [1, 0]
                ##
                elif gt_type == 'acr4+':
                    # DBT with a global_birads superior to 3 are associated to malignant, otherwise to benign
                    global_truth = [0, 1] if global_birads > 3 else [1, 0]
                else:
                    raise ValueError(f"The gt_type:{gt_type} is not yet handle.")

                if global_truth:
                    subject_de, laterality = values['Subject_DE'], values['FrameLaterality']
                    studyUid = values['ImagePath'].split('/')[-2]
                    if scope == 'volume-wise':
                        _key = uid
                    elif scope == 'breast-wise':
                        _key = f'{subject_de}_{studyUid}_{laterality.upper()}'
                    elif scope == 'patient-wise':
                        _key = f'{subject_de}_{studyUid}'
                    else:
                        raise ValueError(f"The scope: {scope} is not yet handle.")
                    mapped_labels.setdefault(_key, {})
                    mapped_labels[_key].setdefault('uids', []).append(uid)
                    mapped_labels[_key].setdefault('truth', []).append(global_truth)
    return mapped_labels
