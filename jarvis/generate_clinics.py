
import json
import os

clinics = [
    {"name": "International Hospital Kampala (IHK)", "location": "Namuwongo"},
    {"name": "Case Hospital", "location": "Buganda Road"},
    {"name": "Nakasero Hospital", "location": "Nakasero"},
    {"name": "The Surgery", "location": "Naguru"},
    {"name": "Victoria Hospital", "location": "Bukoto"},
    {"name": "Norvik Hospital", "location": "Bombo Road"},
    {"name": "St. Catherine's Hospital", "location": "Nakasero"}
]

with open("clinics_data.json", "w") as f:
    json.dump(clinics, f, indent=4)

print("Data generated successfully.")
