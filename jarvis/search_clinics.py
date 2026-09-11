import requests
from bs4 import BeautifulSoup

def search_clinics():
    # This is a simulated search as I don't have direct web browsing, 
    # but I will structure the data for the user based on known reputable clinics.
    clinics = [
        {"name": "International Hospital Kampala (IHK)", "location": "Namuwongo"},
        {"name": "Nakasero Hospital", "location": "Nakasero Hill"},
        {"name": "Case Hospital", "location": "Buganda Road"},
        {"name": "The Surgery", "location": "Naguru"},
        {"name": "Aga Khan University Hospital (Medical Centre)", "location": "Kampala"}
    ]
    with open("clinics_list.txt", "w") as f:
        for clinic in clinics:
            f.write(f"{clinic['name']} - {clinic['location']}\n")

search_clinics()
