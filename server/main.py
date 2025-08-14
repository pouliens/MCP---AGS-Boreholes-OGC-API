"""
AGS Boreholes MCP Server

A Model Context Protocol (MCP) server for accessing British Geological Survey 
borehole data via the OGC API. Provides tools for geological research and 
site investigation data analysis.

Version: 2.0.0
"""

from fastmcp import FastMCP
import requests
from typing import Dict, Any
import logging
import math
import sys


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = FastMCP("AGS Boreholes API")

# API Configuration
OGC_API_BASE_URL = "https://ogcapi.bgs.ac.uk"
COLLECTION_NAME = "agsboreholeindex"

# UK geographic bounds for validation
UK_BOUNDS = {
    "min_lat": 49.0,
    "max_lat": 61.0, 
    "min_lon": -8.0,
    "max_lon": 2.0
}

def convert_bng_to_wgs84(easting: float, northing: float) -> tuple[float, float]:
    """Convert British National Grid coordinates to WGS84 lat/lon.
    
    Uses simplified approximation suitable for most geological applications.
    For precise surveying, use pyproj or similar projection library.
    
    Args:
        easting: BNG easting coordinate (meters)
        northing: BNG northing coordinate (meters)
        
    Returns:
        Tuple of (latitude, longitude) in decimal degrees
    """
    # Simplified conversion using linear approximation
    # Based on OSGB36 parameters with sufficient accuracy for geological work
    lat_approx = 49.0 + (northing - 100000) / 111000
    lon_approx = -2.0 + (easting - 400000) / (111000 * math.cos(math.radians(lat_approx)))
    
    return lat_approx, lon_approx

def validate_uk_coordinates(lat: float, lon: float) -> bool:
    """Validate coordinates are within UK territory bounds.
    
    Args:
        lat: Latitude in decimal degrees
        lon: Longitude in decimal degrees
        
    Returns:
        True if coordinates are within UK bounds
    """
    return (UK_BOUNDS["min_lat"] <= lat <= UK_BOUNDS["max_lat"] and 
            UK_BOUNDS["min_lon"] <= lon <= UK_BOUNDS["max_lon"])

def calculate_bbox(lat: float, lon: float, buffer_km: float) -> str:
    """Calculate bounding box around a point.
    
    Args:
        lat: Center latitude
        lon: Center longitude  
        buffer_km: Buffer radius in kilometers
        
    Returns:
        Comma-separated bbox string (min_lon,min_lat,max_lon,max_lat)
    """
    lat_buffer = buffer_km / 111.0
    lon_buffer = buffer_km / (111.0 * math.cos(math.radians(lat)))
    
    min_lon = lon - lon_buffer
    min_lat = lat - lat_buffer
    max_lon = lon + lon_buffer
    max_lat = lat + lat_buffer
    
    return f"{min_lon},{min_lat},{max_lon},{max_lat}"

def enhance_feature_properties(feature: Dict[str, Any], search_lat: float = None, search_lon: float = None) -> None:
    """Enhance feature properties with calculated coordinates and distance.
    
    Args:
        feature: GeoJSON feature to enhance
        search_lat: Optional search center latitude for distance calculation
        search_lon: Optional search center longitude for distance calculation
    """
    props = feature.get('properties', {})
    
    # Convert BNG coordinates to WGS84 if available
    if props.get('x') and props.get('y'):
        try:
            lat_calc, lon_calc = convert_bng_to_wgs84(props['x'], props['y'])
            props['calculated_latitude'] = round(lat_calc, 6)
            props['calculated_longitude'] = round(lon_calc, 6)
            
            # Calculate distance from search point if provided
            if search_lat is not None and search_lon is not None:
                distance = math.sqrt(
                    (lat_calc - search_lat) ** 2 + (lon_calc - search_lon) ** 2
                ) * 111  # Convert to km
                props['distance_km'] = round(distance, 2)
        except Exception as e:
            logger.warning(f"Coordinate conversion failed for feature {props.get('loca_id', 'unknown')}: {e}")

def make_api_request(bbox: str, limit: int = 100) -> Dict[str, Any]:
    """Make request to BGS OGC API.
    
    Args:
        bbox: Bounding box string
        limit: Maximum number of results
        
    Returns:
        API response dictionary or error dictionary
    """
    url = f"{OGC_API_BASE_URL}/collections/{COLLECTION_NAME}/items"
    params = {
        'bbox': bbox,
        'limit': limit,
        'f': 'json'
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code != 200:
            return {
                "error": f"API returned HTTP {response.status_code}",
                "message": response.text[:200],
                "request_url": response.url
            }
        
        return response.json()
        
    except Exception as e:
        return {
            "error": "Request failed",
            "message": str(e)
        }

@mcp.tool
def check_bgs_service_status() -> Dict[str, Any]:
    """Check if BGS OGC API service is available and responding.
    
    Returns:
        Dictionary with service status, metadata, and collection information
    """
    try:
        response = requests.get(f"{OGC_API_BASE_URL}/collections/{COLLECTION_NAME}", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return {
                "status": "healthy",
                "title": data.get("title", "Unknown"),
                "description": data.get("description", "No description")[:200],
                "api_url": f"{OGC_API_BASE_URL}/collections/{COLLECTION_NAME}"
            }
        else:
            return {
                "status": "error",
                "error": f"HTTP {response.status_code}",
                "message": response.text[:200]
            }
    except Exception as e:
        return {
            "status": "error", 
            "error": "Connection failed",
            "message": str(e)
        }

@mcp.tool
def get_boreholes_at_location(latitude: float, longitude: float, buffer_km: float = 1.0) -> Dict[str, Any]:
    """Get borehole data at a specific location with buffer radius.
    
    Args:
        latitude: Latitude in decimal degrees (WGS84)
        longitude: Longitude in decimal degrees (WGS84) 
        buffer_km: Search radius in kilometers (default: 1.0)
    
    Returns:
        Dictionary containing:
        - features: List of borehole GeoJSON features
        - count: Number of boreholes found
        - search_params: Search parameters used
        - links: API pagination links
    """
    # Validate coordinates
    if not validate_uk_coordinates(latitude, longitude):
        return {
            "error": "Coordinates outside UK bounds",
            "message": f"BGS data covers UK territory ({UK_BOUNDS['min_lat']}-{UK_BOUNDS['max_lat']}°N, {UK_BOUNDS['min_lon']}-{UK_BOUNDS['max_lon']}°E)",
            "provided_coords": {"lat": latitude, "lon": longitude}
        }
    
    # Calculate bounding box and make API request
    bbox = calculate_bbox(latitude, longitude, buffer_km)
    data = make_api_request(bbox, limit=100)
    
    if 'error' in data:
        data['search_params'] = {"latitude": latitude, "longitude": longitude, "buffer_km": buffer_km}
        return data
    
    # Enhance features with calculated coordinates and distances
    features = data.get('features', [])
    for feature in features:
        enhance_feature_properties(feature, latitude, longitude)
        
        # Add search context to each feature
        props = feature.get('properties', {})
        props['search_location'] = {'lat': latitude, 'lon': longitude}
        props['search_buffer_km'] = buffer_km
    
    return {
        "features": features,
        "count": len(features),
        "search_params": {
            "latitude": latitude,
            "longitude": longitude, 
            "buffer_km": buffer_km,
            "bbox": bbox
        },
        "links": data.get('links', [])
    }

@mcp.tool  
def search_boreholes_in_area(min_latitude: float, min_longitude: float, 
                           max_latitude: float, max_longitude: float) -> Dict[str, Any]:
    """Search for boreholes within a bounding box area.
    
    Args:
        min_latitude: Southern boundary in decimal degrees
        min_longitude: Western boundary in decimal degrees  
        max_latitude: Northern boundary in decimal degrees
        max_longitude: Eastern boundary in decimal degrees
    
    Returns:
        Dictionary containing:
        - features: List of borehole GeoJSON features  
        - count: Number of boreholes found
        - search_area: Search boundary parameters
        - links: API pagination links
    """
    # Validate all coordinates are within UK
    coords_valid = (
        validate_uk_coordinates(min_latitude, min_longitude) and
        validate_uk_coordinates(max_latitude, max_longitude)
    )
    
    if not coords_valid:
        return {
            "error": "Coordinates outside UK bounds",
            "message": f"BGS data covers UK territory ({UK_BOUNDS['min_lat']}-{UK_BOUNDS['max_lat']}°N, {UK_BOUNDS['min_lon']}-{UK_BOUNDS['max_lon']}°E)",
            "provided_bounds": {
                "min_lat": min_latitude, "min_lon": min_longitude,
                "max_lat": max_latitude, "max_lon": max_longitude
            }
        }
    
    # Make API request with area bounds
    bbox = f"{min_longitude},{min_latitude},{max_longitude},{max_latitude}"
    data = make_api_request(bbox, limit=1000)
    
    if 'error' in data:
        data['search_area'] = {
            "min_latitude": min_latitude, "min_longitude": min_longitude,
            "max_latitude": max_latitude, "max_longitude": max_longitude
        }
        return data
    
    # Enhance features with calculated coordinates
    features = data.get('features', [])
    for feature in features:
        enhance_feature_properties(feature)
    
    return {
        "features": features,
        "count": len(features),
        "search_area": {
            "min_latitude": min_latitude, "min_longitude": min_longitude,
            "max_latitude": max_latitude, "max_longitude": max_longitude,
            "bbox": bbox
        },
        "links": data.get('links', [])
    }

@mcp.tool
def get_borehole_summary(search_result: Dict[str, Any]) -> Dict[str, Any]:
    """Generate summary statistics from borehole search results.
    
    Args:
        search_result: Dictionary from get_boreholes_at_location or search_boreholes_in_area
        
    Returns:
        Dictionary with:
        - total_boreholes: Count of boreholes
        - depth_statistics: Min, max, average depths
        - projects: List of project names
        - locations_with_coords: Count of geolocated boreholes
        - borehole_logs_available: Count with detailed log links
    """
    if 'error' in search_result:
        return {
            "error": "Cannot analyze search result with errors", 
            "original_error": search_result['error']
        }
    
    features = search_result.get('features', [])
    if not features:
        return {"error": "No boreholes found to analyze"}
    
    # Initialize summary structure
    summary = {
        "total_boreholes": len(features),
        "depths": [],
        "depth_statistics": {},
        "projects": set(),
        "locations_with_coords": 0,
        "borehole_logs_available": 0
    }
    
    # Process each borehole feature
    for feature in features:
        props = feature.get('properties', {})
        
        # Extract depth information (loca_fdep = final depth of borehole)
        if props.get('loca_fdep') is not None:
            try:
                depth = float(props['loca_fdep'])
                summary["depths"].append(depth)
            except (ValueError, TypeError):
                pass
        
        # Count features with coordinates
        if props.get('x') and props.get('y'):
            summary["locations_with_coords"] += 1
        
        # Collect project information
        if props.get('proj_name'):
            summary["projects"].add(props['proj_name'])
        
        # Count features with detailed log data
        if props.get('ags_log_url'):
            summary["borehole_logs_available"] += 1
    
    # Calculate depth statistics
    if summary["depths"]:
        depths = summary["depths"]
        summary["depth_statistics"] = {
            "min_depth_m": round(min(depths), 2),
            "max_depth_m": round(max(depths), 2),
            "avg_depth_m": round(sum(depths) / len(depths), 2),
            "total_drilling_m": round(sum(depths), 2),
            "count_with_depth": len(depths)
        }
    
    # Convert set to list for JSON serialization
    summary["projects"] = list(summary["projects"])
    summary["search_info"] = search_result.get('search_params') or search_result.get('search_area', {})
    
    return summary

@mcp.tool
def find_deep_boreholes(latitude: float, longitude: float, buffer_km: float = 5.0, 
                       min_depth_m: float = 10.0) -> Dict[str, Any]:
    """Find boreholes deeper than specified depth near a location.
    
    Useful for bedrock analysis as deeper boreholes are more likely to reach bedrock.
    
    Args:
        latitude: Latitude in decimal degrees (WGS84)
        longitude: Longitude in decimal degrees (WGS84)
        buffer_km: Search radius in kilometers (default: 5.0)
        min_depth_m: Minimum depth in meters (default: 10.0)
    
    Returns:
        Dictionary containing:
        - deep_boreholes: List of boreholes meeting depth criteria
        - count: Number of deep boreholes found
        - total_searched: Total boreholes examined
        - criteria: Search criteria used
    """
    # Get all boreholes in search area
    search_result = get_boreholes_at_location(latitude, longitude, buffer_km)
    
    if 'error' in search_result:
        return search_result
    
    # Filter for deep boreholes
    features = search_result.get('features', [])
    deep_boreholes = []
    
    for feature in features:
        props = feature.get('properties', {})
        if props.get('loca_fdep'):
            try:
                depth = float(props['loca_fdep'])
                if depth >= min_depth_m:
                    deep_boreholes.append(feature)
            except (ValueError, TypeError):
                continue
    
    return {
        "deep_boreholes": deep_boreholes,
        "count": len(deep_boreholes),
        "total_searched": len(features),
        "criteria": {
            "min_depth_m": min_depth_m,
            "search_radius_km": buffer_km,
            "location": {"lat": latitude, "lon": longitude}
        },
        "note": "These boreholes may have reached bedrock. Check ags_log_url for detailed geological stratigraphy."
    }

if __name__ == "__main__":
    # Check if stdio mode is requested
    if "--stdio" in sys.argv:
        # Run in stdio mode for MCP clients like VS Code
        mcp.run()
    else:
        # Run in HTTP mode for web access via Cloudflare Tunnel
        mcp.run(
            transport="http",
            host="127.0.0.1", 
            port=8080,
            path="/mcp"
        )
