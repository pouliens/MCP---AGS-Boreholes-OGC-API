# AGS Boreholes OGC API MCP

A Model Context Protocol (MCP) server for accessing British Geological Survey (BGS) borehole data via the modern OGC API. Provides clean, reliable access to geological drilling data for research and engineering applications.

## 🎯 Overview

This MCP enables Claude to access 70,000+ borehole records from the BGS database, supporting:
- **Geological research** and site investigations
- **Bedrock depth analysis** from drilling logs
- **Engineering ground assessments**  
- **Academic research** at universities like Edinburgh

## ✨ Features

### Available Tools

1. **`check_bgs_service_status`** - Verify BGS API availability
2. **`get_boreholes_at_location`** - Find boreholes near coordinates with distance calculations
3. **`search_boreholes_in_area`** - Search within bounding box regions
4. **`get_borehole_summary`** - Generate statistics and analysis
5. **`find_deep_boreholes`** - Find deep holes likely to reach bedrock

### Data Fields

Each borehole includes:
- **`loca_fdep`**: Final borehole depth (meters) 
- **`bgs_loca_id`**: BGS unique identifier
- **`ags_log_url`**: Link to detailed geological log data
- **`x`, `y`**: British National Grid coordinates (automatically converted to WGS84)
- **`calculated_latitude`, `calculated_longitude`**: WGS84 coordinates
- **`distance_km`**: Distance from search point
- **`proj_name`**: Associated project name

## 🚀 Quick Start

### 1. Installation

```bash
git clone <repository-url>
cd AGS-boreholes-mcp
pip install -e .
```

### 2. Configuration

#### Claude Desktop (stdio mode)

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ags-boreholes": {
      "command": "python",
      "args": ["server/main.py", "--stdio"],
      "cwd": "/path/to/AGS-boreholes-mcp"
    }
  }
}
```

#### Web/HTTP Mode

```bash
# Run HTTP server (default mode)
python server/main.py

# Access via: http://127.0.0.1:8080/mcp
```

Perfect for:
- **Cloudflare Tunnel** integration
- **Web development** and testing
- **Remote access** to geological data

### 3. Usage Examples

Ask Claude:
- *"Find boreholes near Edinburgh and summarize their depths"*
- *"Search for deep boreholes around Manchester that might have reached bedrock"*
- *"What geological drilling data is available in the Thames Valley?"*
- *"Check if the BGS service is working"*

## 🔍 Bedrock Depth Analysis

**Important**: The `loca_fdep` field shows **total borehole depth**, not depth to bedrock.

For bedrock analysis:
1. Use `find_deep_boreholes()` to find deeper holes more likely to reach bedrock
2. Access detailed logs via `ags_log_url` for geological stratigraphy
3. Parse lithological data in the detailed logs for actual bedrock contact depths

## 📊 Example Queries

### Research Applications
```
"Find boreholes deeper than 20 meters near the University of Edinburgh"
"Search for geological data around proposed construction sites in London"  
"What's the average drilling depth in the Scottish Highlands?"
```

### Engineering Applications
```
"Find site investigation data near Heathrow Airport"
"Search for foundation engineering data in central Manchester"
"Show me deep boreholes that might indicate bedrock depth around Birmingham"
```

## 🏗️ Architecture

### Version 2.0 Improvements

- **✅ OGC API**: Switched from unreliable WMS to modern REST API
- **✅ Error Handling**: Comprehensive error reporting and validation
- **✅ UK Bounds**: Geographic validation ensures queries within data coverage
- **✅ Coordinate Conversion**: Automatic BNG to WGS84 transformation
- **✅ Distance Calculations**: Shows proximity to search points
- **✅ Service Health**: Built-in API status monitoring

### Code Quality
- **Clean Architecture**: Separated concerns with helper functions  
- **Type Safety**: Full type hints for better IDE support
- **Documentation**: Comprehensive docstrings and examples
- **Zero Dependencies**: Only essential libraries (fastmcp, requests)

## 📡 Data Source

- **Provider**: British Geological Survey (BGS)
- **API**: https://ogcapi.bgs.ac.uk/collections/agsboreholeindex
- **Coverage**: United Kingdom (49-61°N, -8-2°E)  
- **Records**: ~70,000 borehole locations
- **License**: Contains British Geological Survey materials © NERC

## 🛠️ Requirements

```bash
pip install fastmcp>=0.5.0 requests>=2.31.0
```

## 🧪 Development & Testing

```bash
# Test stdio mode (Claude Desktop)
python server/main.py --stdio

# Test HTTP mode (web/tunnel)
python server/main.py
# Then visit: http://127.0.0.1:8080/mcp

# Test module import
PYTHONPATH=. python -c "import server.main; print('MCP loaded successfully')"
```

### Transport Modes

| Mode | Command | Use Case |
|------|---------|----------|
| **stdio** | `python server/main.py --stdio` | Claude Desktop, VS Code MCP |
| **HTTP** | `python server/main.py` | Cloudflare Tunnel, web access |

### Cloudflare Tunnel Setup

```bash
# Install cloudflared
# https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/

# Run MCP in HTTP mode
python server/main.py

# Create tunnel (in another terminal)
cloudflared tunnel --url http://127.0.0.1:8080/mcp
```

## 📞 Support

- **BGS Enquiries**: enquiries@bgs.ac.uk
- **API Issues**: Check service status with `check_bgs_service_status()`
- **Data Questions**: Refer to BGS data documentation

## 📄 License

This project provides an interface to BGS data. Please respect BGS data licensing terms and copyright notices when using geological data for research or commercial applications.

---

**Version**: 2.0.0 | **Author**: Claude Code | **Updated**: 2025-08-14