import requests
import json
import pprint
from config import cookies, headers  # config.py에서 쿠키와 헤더 가져오기

def calculate_bounds(vertices):
    lons = [point[1] for point in vertices]
    lats = [point[0] for point in vertices]
    leftLon = min(lons)
    rightLon = max(lons)
    bottomLat = min(lats)
    topLat = max(lats)
    return leftLon, rightLon, topLat, bottomLat

def fetch_marker_info(cortars_info, divisionName, cortarName):
    cortarNo = cortars_info.get('cortarNo')
    cortarZoom = cortars_info.get('cortarZoom')
    cortarVertexLists = cortars_info.get('cortarVertexLists', [[]])

    # Calculate the bounds (leftLon, rightLon, topLat, bottomLat)
    if cortarVertexLists and cortarVertexLists[0]:
        leftLon, rightLon, topLat, bottomLat = calculate_bounds(cortarVertexLists[0])
    else:
        print(f"Invalid cortarVertexLists data for cortarNo: {cortarNo}")
        return None

    params = {
        'cortarNo': cortarNo,
        'zoom': cortarZoom,
        'priceType': 'RETAIL',
        'markerId': '',
        'markerType': '',
        'selectedComplexNo': '',
        'selectedComplexBuildingNo': '',
        'fakeComplexMarker': '',
        'realEstateType': 'APT',
        'tradeType': 'A1',
        'tag': '%3A%3A%3A%3A%3A%3A%3A%3A',
        'rentPriceMin': 0,
        'rentPriceMax': 900000000,
        'priceMin': 0,
        'priceMax': 900000000,
        'areaMin': 0,
        'areaMax': 900000000,
        'oldBuildYears': '',
        'recentlyBuildYears': '',
        'minHouseHoldCount': 300,
        'maxHouseHoldCount': '',
        'showArticle': 'false',
        'sameAddressGroup': 'false',
        'minMaintenanceCost': '',
        'maxMaintenanceCost': '',
        'directions': '',
        'leftLon': leftLon,
        'rightLon': rightLon,
        'topLat': topLat,
        'bottomLat': bottomLat,
        'isPresale': 'false'
    }

    response = requests.get(
        'https://new.land.naver.com/api/complexes/single-markers/2.0',
        params=params,
        cookies=cookies,
        headers=headers
    )

    print(f"Fetching marker IDs for cortarNo: {cortarNo} - HTTP status code: {response.status_code}")

    if response.status_code == 200:
        try:
            response_data = response.json()
            #pprint.pprint(response_data)  # 응답 데이터 전체를 출력하여 구조 확인

            marker_info_list = []
            for item in response_data:
                if 'markerId' in item and 'latitude' in item and 'longitude' in item:
                    marker_info = {
                        'markerId': item['markerId'],
                        'latitude': item['latitude'],
                        'longitude': item['longitude'],
                        'completionYearMonth': item['completionYearMonth'],
                        'totalHouseholdCount': item['totalHouseholdCount'],
                        'divisionName': divisionName,
                        'cortarName': cortarName
                    }
                    marker_info_list.append(marker_info)

            if marker_info_list:
                return marker_info_list
            else:
                print(f"No marker IDs found in the response for cortarNo: {cortarNo}.")
                return None
        except json.JSONDecodeError:
            print(f"Failed to parse JSON response for cortarNo: {cortarNo}.")
            return None
    else:
        print(f"Failed to fetch marker IDs for cortarNo: {cortarNo}. Status code: {response.status_code}")
        return None

if __name__ == "__main__":
    with open('cortars_info.json', 'r', encoding='utf-8') as file:
        cortars_data = json.load(file)
    
    if isinstance(cortars_data, dict):
        cortars_data = [cortars_data]
    
    all_marker_info = {}

    for cortars_info in cortars_data:
        divisionName = cortars_info.get('divisionName', 'Unknown')
        cortarName = cortars_info.get('cortarName', 'Unknown')
        cortar_name = f"{divisionName} {cortarName}"
        cortar_no = cortars_info.get('cortarNo')
        
        if cortar_no:
            marker_info_list = fetch_marker_info(cortars_info, divisionName, cortarName)
            if marker_info_list:
                all_marker_info[cortar_name] = marker_info_list
                print(f"Marker information for cortarNo {cortar_no} ({cortar_name}):")
                pprint.pprint(marker_info_list)
            else:
                print(f"No marker information found for cortarNo {cortar_no} ({cortar_name})")
        else:
            print(f"No cortarNo found for {cortar_name}")

    if all_marker_info:
        with open('all_marker_info.json', 'w', encoding='utf-8') as file:
            json.dump(all_marker_info, file, ensure_ascii=False, indent=4)
        print("All marker information has been collected and saved to all_marker_info.json")
    else:
        print("No marker information found.")