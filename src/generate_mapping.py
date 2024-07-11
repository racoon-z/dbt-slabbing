import os
import json
import pydicom


def read_csv_file(path, encoding=None):
    data = []
    with open(path, 'r', encoding=encoding) as f:
        file_data = f.read().splitlines()

    data.extend(file_data)

    return data


def find_all_image_files(image_root: os.path) -> list:
    file_paths = []
    for root, dirs, files in os.walk(image_root):
        for file_path in files:
            if file_path.endswith('.dcm'):
                # Append dicom files (FFDMs, DBTs, and MRIs) into the file_paths list
                file_paths.append(os.path.join(root, file_path))
                break
        if len(file_paths) > 5:
            break
    return file_paths


def check_laterality(image_laterality: str, truth_laterality: str) -> bool:
    if (image_laterality == 'R' and truth_laterality == '1') or (image_laterality == 'L' and truth_laterality == '2'):
        return True
    return False


def get_truth_labels(subject_de: str, laterality: str, root_csv: os.path):
    # Load the global DBT & MRI BIRADS scores per subject
    global_birads = get_global_birads_per_subject(root_csv=root_csv)
    dbt_birads, mri_birads = global_birads[subject_de]['DBT_BIRADS'], global_birads[subject_de]['MRI_BIRADS']
    year0_dbt_outcomes = read_csv_file(os.path.join(root_csv, 'ea1141_year0_tomolesions_outcome.csv'))
    year0_mri_outcomes = read_csv_file(os.path.join(root_csv, 'ea1141_year0_mrilesions_outcome.csv'))
    # Get column position of BreastLaterality and BiopsyOutcome in csv files
    dbt_header, mri_header = year0_dbt_outcomes[0].split(','), year0_mri_outcomes[0].split(',')
    indices = {
        "DBT_Lat": dbt_header.index('TOMO_LESIONBREAST_YR0'), "DBT_Outcome": dbt_header.index('TOMO_LESIONOUTCOME_YR0'),
        "MRI_Lat": mri_header.index('MRI_LESIONBREAST_YR0'), "MRI_Outcome": mri_header.index('MRI_LESIONOUTCOME_YR0')
    }
    # If these labels are contained in 'LESIONOUTCOME' fields, it defines either its benign or malignant
    labels = {
        'Benign': ['BIRADS 1', 'BIRADS 2', 'BIRADS 3', 'Benign', 'No biopsy', 'BI-RADS score downgraded'],
        'Malignant': ['Invasive', 'DCIS']
    }
    dbt_biopsy, mri_biopsy = None, None
    # DBT and MRI outcomes are separated into two different csv files. We process them successively
    # Starts with DBT annotations
    for line in year0_dbt_outcomes[1:]:
        split_line = line.split(',')
        if split_line[-1] == subject_de:
            # Ensure that the malignancy is detected on the correct FrameLaterality => Right or Left
            if check_laterality(image_laterality=laterality, truth_laterality=split_line[indices["DBT_Lat"]]):
                dbt_outcome = split_line[indices['DBT_Outcome']]
                if any(b in dbt_outcome for b in labels['Benign']):
                    dbt_biopsy = 'BENIGN'
                elif any(m in dbt_outcome for m in labels['Malignant']):
                    dbt_biopsy = 'MALIGNANT'
                else:
                    dbt_biopsy = 'UNKNOWN'
            else:
                # We keep only laterality containing the lesion for subject with BIRADS score > 2
                # Thus, we override BIRADS score and Biopsy Outcome to None for the other laterality
                dbt_birads = None
                dbt_biopsy = None
    # Continue with MRI annotations
    for line in year0_mri_outcomes[1:]:
        split_line = line.split(',')
        if split_line[-1] == subject_de:
            if check_laterality(image_laterality=laterality, truth_laterality=split_line[indices["MRI_Lat"]]):
                mri_outcome = split_line[indices['MRI_Outcome']]
                if any(b in mri_outcome for b in labels['Benign']):
                    mri_biopsy = 'BENIGN'
                elif any(m in mri_outcome for m in labels['Malignant']):
                    mri_biopsy = 'MALIGNANT'
                else:
                    mri_biopsy = 'UNKNOWN'
            else:
                # We keep only laterality containing the lesion for subject with BIRADS score > 2
                # Thus, we override BIRADS score and Biopsy Outcome to None for the other laterality
                mri_birads = None
                mri_biopsy = None

    return dbt_birads, dbt_biopsy, mri_birads, mri_biopsy


def get_global_birads_per_subject(root_csv: os.path) -> dict:
    mapping_per_subject = {}
    year0_screening_derived = read_csv_file(os.path.join(root_csv, 'ea1141_year0_screening_derived.csv'))
    header_split = year0_screening_derived[0].split(',')
    for line in year0_screening_derived[1:]:
        _subject_de = line.split(',')[-1]
        dbt_birads = line.split(',')[header_split.index('TOMO_BIRADS_YR0')]
        mri_birads = line.split(',')[header_split.index('MRI_BIRADS_YR0')]
        mapping_per_subject.setdefault(_subject_de, {'DBT_BIRADS': dbt_birads, 'MRI_BIRADS': mri_birads})

    return mapping_per_subject


def get_ea1141_dbt_mapping(image_root: os.path, root_csv: os.path) -> dict:
    # DBT are mapped with the SOPInstanceUID
    dbt_mapping = {}
    paths = find_all_image_files(image_root=image_root)
    for image_path in paths:
        ds = pydicom.dcmread(image_path)
        image_array = ds.pixel_array
        if ds.Modality == 'MG' and len(image_array.shape) == 3:
            # We eliminate MRI exams and find slabbed DBT, i.e., having a SliceThickness = 10mm
            # In many cases, this dicom tag is not present
            # We consider image as DBT if SliceThickness is None or 1
            try:
                SliceThickness = int(ds.SharedFunctionalGroupsSequence[0].PixelMeasuresSequence[0].SliceThickness)
            except:
                SliceThickness = None
            if SliceThickness != 10:
                PatientID, StudyUID, SeriesUID = ds.PatientID, ds.StudyInstanceUID, ds.SeriesInstanceUID
                try:
                    FrameLaterality = ds.SharedFunctionalGroupsSequence[0].FrameAnatomySequence[0].FrameLaterality
                except:
                    FrameLaterality = None
                Subject_DE = PatientID.split('-')[-1]
                dbt_birads, dbt_outcome, mri_birads, mri_outcome = get_truth_labels(subject_de=Subject_DE,
                                                                                    laterality=FrameLaterality,
                                                                                    root_csv=root_csv)
                #
                dbt_mapping[ds.SOPInstanceUID] = {
                    'PatientID': PatientID, 'StudyInstanceUID': StudyUID, 'SeriesInstanceUID': SeriesUID,
                    'ImageShape': image_array.shape, 'SeriesDescription': ds.SeriesDescription,
                    'FrameLaterality': FrameLaterality, 'ImagePath': image_path.replace(image_root, '$ROOT$/'),
                    'Subject_DE': Subject_DE, 'DBT_BIRADS': dbt_birads, 'MRI_BIRADS': mri_birads,
                    'DBT_Outcome': dbt_outcome, 'MRI_Outcome': mri_outcome
                }

    return dbt_mapping


# These two root paths must be replaced with your specific paths
# root_images = os.path.join("/datacollection-stash/data-curation/inbox/curated/EA1141/MG/")
root_images = os.path.join("//10.0.10.3/stash/data-curation/inbox/curated/EA1141/MG/")
csv_root = os.path.join("C:/Users/PaulTerrassin/paul-terrassin-shared-space/dbt/EA1141-Reviewed-Clinical-Data-and-Data-Dictionaries/")

mapping = get_ea1141_dbt_mapping(image_root=root_images, root_csv=csv_root)
with open('ea1141-mapping.json', 'w') as file:
    json.dump(mapping, file, indent=4)
