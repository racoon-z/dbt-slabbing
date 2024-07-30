## **Digital Breast Tomosynthesis (DBT) Slabbing**

This repository completes the accepted paper for MICCAI 2024, part of the DeepBreath workshop. Our paper is entitled: **Thick Slices for Optimal Digital Breast Tomosynthesis Classification With Deep-Learning**.  

We benchmark the impact of slabbing for CNN-based methods used for classification of Digital Breast Tomosynthesis (DBT). In our study, we used a multi-modal dataset, named EA1141. As we are the first study exploring DBTs from EA1141, we wanted to publish the code and mapping to make our experiments reproducible.

### Structure of the GitHub repository
```
Root  
├── src  
│   ├── generate_mapping.py  
│   └── load_ground_truths.py  
├── EA1141-Reviewed-Clinical-Data-and-Data-Dictionaries.zip  
├── ea1141-mapping.json  
└── README.md  
```

*EA1141-Reviewed-Clinical-Data-and-Data-Dictionaries.zip* must be unzipped  
*ea1141-mapping.json* is the Json file containing the DBT mapping, using *generate_mapping.py*

### EA1141 data structuration

All our code is developed based on the following data architecture. The root folder *EA1141* contains
all patient folders named *EA1141-\<PatientID>*. Each patient directory is divided into study dates at the format YYYY-MM-DD.

E.g., EA1141 -> EA1141-9011509 -> 19450327 -> 1.3.6.1.4.1.14519.5.2.1.1620.1225.124982595355003732709362633888.dcm

```
EA1141  
├── EA1141-\<PatientID:1>  
│   ├── \<StuyDate:1>  
│   │   ├── \<SOPInstanceUID:1>   
│   │   ├── ...  
│   │   └── \<SOPInstanceUID:X>  
│   ├── ...  
│   └── \<StuyDate:M>  
├── ...  
└── EA1141-\<PatientID:N>
```

### Python scripts

**generate_mapping.py**

This code can be used to identify DBTs from other modalities in the whole dataset. The global dataset must follows the above data architecture. This script contains function and can be used as a main to return the Json mapping of all DBTs with their BIRADS assessments and biopsy outcomes.

**load_ground_truths.py**

This code serves to load DBT ground truths to generate metrics. The function allows the user to choose the scope: 'volume-wise', 'breast-wise', or 'patient-wise', the type of ground truth: 'acr4+' or 'biopsy' and whether it ignores DBT with negative assessment or outcome but the MRI is suspicious or positive. Global details to run the function are available in the code.
