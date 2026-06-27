import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

USERNAME = os.getenv("COPERNICUS_USERNAME")
PASSWORD = os.getenv("COPERNICUS_PASSWORD")

def get_access_token():
    url = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
    data = {
        "grant_type": "password",
        "username": USERNAME,
        "password": PASSWORD,
        "client_id": "cdse-public",
    }
    response = requests.post(url, data=data)
    response.raise_for_status()
    token = response.json()["access_token"]
    print("✓ Authentication successful")
    return token

def search_sentinel1(token):
    url = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
    area = "POLYGON((-118.30 33.68,-118.10 33.68,-118.10 33.78,-118.30 33.78,-118.30 33.68))"
    params = {
        "$filter": (
            f"Collection/Name eq 'SENTINEL-1' "
            f"and OData.CSC.Intersects(area=geography'SRID=4326;{area}') "
            f"and ContentDate/Start gt 2026-05-01T00:00:00.000Z "
            f"and ContentDate/Start lt 2026-06-26T00:00:00.000Z "
            f"and Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'productType' "
            f"and att/OData.CSC.StringAttribute/Value eq 'GRD')"
        ),
        "$top": 5,
        "$orderby": "ContentDate/Start desc",
    }
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, params=params, headers=headers)
    response.raise_for_status()
    products = response.json()["value"]
    print(f"✓ Found {len(products)} Sentinel-1 images over Port of LA")
    for p in products:
        print(f"  - {p['Name']}")
        print(f"    Date: {p['ContentDate']['Start'][:10]}")
        print(f"    Size: {round(p['ContentLength'] / 1e6, 1)} MB")
    return products

def save_product_info(products):
    output_path = os.path.join("outputs", "available_images.json")
    simplified = []
    for p in products:
        simplified.append({
            "id": p["Id"],
            "name": p["Name"],
            "date": p["ContentDate"]["Start"][:10],
            "size_mb": round(p["ContentLength"] / 1e6, 1),
        })
    with open(output_path, "w") as f:
        json.dump(simplified, f, indent=2)
    print(f"✓ Image list saved to {output_path}")
    return simplified

if __name__ == "__main__":
    token = get_access_token()
    products = search_sentinel1(token)
    if products:
        save_product_info(products)