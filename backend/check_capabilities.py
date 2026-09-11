import urllib.request
import json
import xml.etree.ElementTree as ET

# Query GetCapabilities on PFZ_LandingCentres
cap_url = "https://www.incois.gov.in/geoserver/PFZ_LandingCentres/wfs?service=WFS&version=1.1.0&request=GetCapabilities"
print("Checking PFZ_LandingCentres WFS capabilities...")
req = urllib.request.Request(cap_url, headers={"User-Agent": "Mozilla/5.0"})
try:
    with urllib.request.urlopen(req) as resp:
        xml_content = resp.read()
    root = ET.fromstring(xml_content)
    # find all FeatureTypes
    for elem in root.iter():
        if elem.tag.endswith("FeatureType"):
            name_el = elem.find("{http://www.opengis.net/wfs}Name")
            title_el = elem.find("{http://www.opengis.net/wfs}Title")
            if name_el is not None:
                print(f"Layer: {name_el.text} | Title: {title_el.text if title_el is not None else ''}")
except Exception as e:
    print(f"Error checking capabilities: {e}")

# Check PFZ_Automation capabilities
cap_url2 = "https://www.incois.gov.in/geoserver/PFZ_Automation/wfs?service=WFS&version=1.1.0&request=GetCapabilities"
print("\nChecking PFZ_Automation WFS capabilities...")
try:
    with urllib.request.urlopen(urllib.request.Request(cap_url2, headers={"User-Agent": "Mozilla/5.0"})) as resp:
        xml_content = resp.read()
    root = ET.fromstring(xml_content)
    for elem in root.iter():
        if elem.tag.endswith("FeatureType"):
            name_el = elem.find("{http://www.opengis.net/wfs}Name")
            title_el = elem.find("{http://www.opengis.net/wfs}Title")
            if name_el is not None:
                print(f"Layer: {name_el.text} | Title: {title_el.text if title_el is not None else ''}")
except Exception as e:
    print(f"Error checking capabilities: {e}")
