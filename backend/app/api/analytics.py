"""Advanced analytics endpoints for SpaceX intelligence."""
from fastapi import APIRouter, Query, HTTPException
from datetime import datetime, timedelta, timezone
from typing import Optional
import httpx

from app.services.spacex_api import spacex_client
from app.services.cache import cache

router = APIRouter(prefix="/analytics", tags=["Analytics"])

# Launchpad coordinates for weather
LAUNCHPADS = {
    "5e9e4501f5090910d4566f83": {"name": "CCSFS SLC 40", "lat": 28.5618, "lon": -80.5777},
    "5e9e4502f509092b78566f87": {"name": "KSC LC 39A", "lat": 28.6084, "lon": -80.6043},
    "5e9e4502f509094188566f88": {"name": "VAFB SLC 4E", "lat": 34.6321, "lon": -120.6105},
    "5e9e4501f509094ba4566f84": {"name": "Kwajalein Atoll", "lat": 9.0477, "lon": 167.7431},
    "5e9e4502f5090927f8566f89": {"name": "Starbase", "lat": 25.9972, "lon": -97.1549},
}


@router.get("/turnaround-time")
async def get_turnaround_times():
    """
    Calculate turnaround time between flights for each booster.
    The holy grail KPI for SpaceX's reusability model.
    """
    cache_key = "analytics:turnaround"
    cached = await cache.get(cache_key)
    if cached:
        return cached
    
    # Get all cores with their launches
    cores = await spacex_client.get_cores(limit=100)
    launches = await spacex_client.get_launches(limit=200, upcoming=False)
    
    # Build launch lookup by ID
    launch_map = {l.id: l for l in launches}
    
    turnaround_data = []
    all_turnarounds = []
    
    for core in cores:
        if len(core.launches) < 2:
            continue
        
        # Get launch dates for this core
        core_launches = []
        for launch_id in core.launches:
            if launch_id in launch_map:
                launch = launch_map[launch_id]
                core_launches.append({
                    "id": launch.id,
                    "name": launch.name,
                    "date": launch.date_utc,
                    "success": launch.success
                })
        
        # Sort by date
        core_launches.sort(key=lambda x: x["date"])
        
        # Calculate turnaround times
        turnarounds = []
        for i in range(1, len(core_launches)):
            prev = core_launches[i - 1]
            curr = core_launches[i]
            days = (curr["date"] - prev["date"]).days
            turnarounds.append({
                "from_launch": prev["name"],
                "to_launch": curr["name"],
                "days": days,
                "from_date": prev["date"].isoformat(),
                "to_date": curr["date"].isoformat()
            })
            all_turnarounds.append(days)
        
        if turnarounds:
            avg_turnaround = sum(t["days"] for t in turnarounds) / len(turnarounds)
            min_turnaround = min(t["days"] for t in turnarounds)
            
            turnaround_data.append({
                "booster": core.serial,
                "status": core.status,
                "total_flights": len(core_launches),
                "average_turnaround_days": round(avg_turnaround, 1),
                "fastest_turnaround_days": min_turnaround,
                "turnarounds": turnarounds[-5:]  # Last 5
            })
    
    # Sort by fastest average
    turnaround_data.sort(key=lambda x: x["average_turnaround_days"])
    
    # Fleet-wide stats
    fleet_avg = sum(all_turnarounds) / len(all_turnarounds) if all_turnarounds else 0
    fleet_fastest = min(all_turnarounds) if all_turnarounds else 0
    
    result = {
        "fleet_stats": {
            "average_turnaround_days": round(fleet_avg, 1),
            "fastest_turnaround_days": fleet_fastest,
            "total_reflights": len(all_turnarounds)
        },
        "top_performers": turnaround_data[:10],
        "all_boosters": turnaround_data
    }
    
    await cache.set(cache_key, result, ttl=3600)
    return result


@router.get("/cross-mission")
async def get_cross_mission_analysis():
    """
    Analyze booster performance across different mission types.
    Correlates booster wear with mission profiles.
    """
    cache_key = "analytics:cross-mission"
    cached = await cache.get(cache_key)
    if cached:
        return cached
    
    cores = await spacex_client.get_cores(limit=100)
    launches = await spacex_client.get_launches(limit=300, upcoming=False)
    
    launch_map = {l.id: l for l in launches}
    
    # Categorize missions
    def categorize_mission(name: str) -> str:
        name_lower = name.lower()
        if "starlink" in name_lower:
            return "Starlink"
        elif "crew" in name_lower or "dragon" in name_lower:
            return "Crew/Dragon"
        elif "crs" in name_lower:
            return "Cargo (CRS)"
        elif "transporter" in name_lower or "rideshare" in name_lower:
            return "Rideshare"
        elif "gps" in name_lower or "nrol" in name_lower or "ussf" in name_lower:
            return "Government/Military"
        else:
            return "Commercial"
    
    booster_analysis = []
    mission_type_stats = {}
    
    for core in cores:
        if not core.launches:
            continue
        
        mission_breakdown = {}
        total_success = 0
        total_flights = 0
        
        for launch_id in core.launches:
            if launch_id not in launch_map:
                continue
            
            launch = launch_map[launch_id]
            mission_type = categorize_mission(launch.name)
            
            if mission_type not in mission_breakdown:
                mission_breakdown[mission_type] = {"count": 0, "success": 0}
            
            mission_breakdown[mission_type]["count"] += 1
            if launch.success:
                mission_breakdown[mission_type]["success"] += 1
                total_success += 1
            total_flights += 1
            
            # Track global stats
            if mission_type not in mission_type_stats:
                mission_type_stats[mission_type] = {
                    "total_launches": 0,
                    "successful": 0,
                    "boosters_used": set()
                }
            mission_type_stats[mission_type]["total_launches"] += 1
            if launch.success:
                mission_type_stats[mission_type]["successful"] += 1
            mission_type_stats[mission_type]["boosters_used"].add(core.serial)
        
        # Determine primary mission type
        primary_type = max(mission_breakdown.items(), key=lambda x: x[1]["count"])[0] if mission_breakdown else "Unknown"
        
        booster_analysis.append({
            "booster": core.serial,
            "status": core.status,
            "total_flights": total_flights,
            "success_rate": round(total_success / total_flights * 100, 1) if total_flights > 0 else 0,
            "primary_mission_type": primary_type,
            "mission_breakdown": mission_breakdown,
            "versatility_score": len(mission_breakdown)  # How many different mission types
        })
    
    # Convert sets to counts
    for mtype in mission_type_stats:
        mission_type_stats[mtype]["unique_boosters"] = len(mission_type_stats[mtype]["boosters_used"])
        del mission_type_stats[mtype]["boosters_used"]
        mission_type_stats[mtype]["success_rate"] = round(
            mission_type_stats[mtype]["successful"] / mission_type_stats[mtype]["total_launches"] * 100, 1
        ) if mission_type_stats[mtype]["total_launches"] > 0 else 0
    
    # Sort by versatility
    booster_analysis.sort(key=lambda x: (-x["versatility_score"], -x["total_flights"]))
    
    result = {
        "mission_type_stats": mission_type_stats,
        "most_versatile_boosters": booster_analysis[:10],
        "insight": _generate_cross_mission_insight(mission_type_stats, booster_analysis)
    }
    
    await cache.set(cache_key, result, ttl=3600)
    return result


def _generate_cross_mission_insight(mission_stats: dict, boosters: list) -> str:
    """Generate human-readable insights from cross-mission data."""
    starlink = mission_stats.get("Starlink", {})
    crew = mission_stats.get("Crew/Dragon", {})
    
    insights = []
    
    if starlink.get("total_launches", 0) > 0:
        pct = round(starlink["total_launches"] / sum(m["total_launches"] for m in mission_stats.values()) * 100)
        insights.append(f"Starlink missions represent {pct}% of all launches")
    
    if crew.get("success_rate", 0) == 100 and crew.get("total_launches", 0) > 5:
        insights.append(f"Crew missions maintain 100% success rate across {crew['total_launches']} flights")
    
    if boosters:
        top = boosters[0]
        insights.append(f"Most versatile booster {top['booster']} flew {top['versatility_score']} mission types")
    
    return ". ".join(insights) if insights else "Analysis complete."


@router.get("/anomaly-timeline")
async def get_anomaly_timeline():
    """
    Historical timeline of all anomalies and failures.
    Correlates with design changes and lessons learned.
    """
    cache_key = "analytics:anomaly-timeline"
    cached = await cache.get(cache_key)
    if cached:
        return cached
    
    launches = await spacex_client.get_launches(limit=300, upcoming=False)
    
    # Find failures and anomalies
    anomalies = []
    
    for launch in launches:
        if launch.success is False:
            anomalies.append({
                "date": launch.date_utc.isoformat(),
                "mission": launch.name,
                "type": "LAUNCH_FAILURE",
                "details": launch.details or "Launch failure - details not available",
                "severity": "critical"
            })
        elif launch.success is None and launch.date_utc < datetime.now(timezone.utc) - timedelta(days=7):
            # Old launch with unknown status - likely anomaly
            anomalies.append({
                "date": launch.date_utc.isoformat(),
                "mission": launch.name,
                "type": "STATUS_UNKNOWN",
                "details": launch.details or "Mission status unknown",
                "severity": "warning"
            })
    
    # Check for landing failures in cores
    cores = await spacex_client.get_cores(limit=100)
    landing_failures = []
    
    for core in cores:
        if core.status == "lost":
            landing_failures.append({
                "booster": core.serial,
                "last_update": core.last_update,
                "flights_before_loss": len(core.launches)
            })
    
    # Historical known events (hardcoded major events)
    historical_events = [
        {
            "date": "2015-06-28T00:00:00+00:00",
            "mission": "CRS-7",
            "type": "IN_FLIGHT_BREAKUP",
            "details": "Falcon 9 disintegrated 139 seconds after launch due to helium tank strut failure",
            "severity": "critical",
            "lesson_learned": "Redesigned helium tank struts with stronger materials"
        },
        {
            "date": "2016-09-01T00:00:00+00:00",
            "mission": "Amos-6",
            "type": "PAD_ANOMALY",
            "details": "Vehicle and payload destroyed during static fire test - COPV failure",
            "severity": "critical",
            "lesson_learned": "Redesigned composite overwrapped pressure vessels (COPV)"
        },
        {
            "date": "2020-02-17T00:00:00+00:00",
            "mission": "Starlink L4",
            "type": "ENGINE_SHUTDOWN",
            "details": "One Merlin engine shut down prematurely, mission still successful",
            "severity": "warning",
            "lesson_learned": "Engine redundancy proved effective"
        }
    ]
    
    # Combine all anomalies
    all_anomalies = sorted(
        anomalies + historical_events,
        key=lambda x: x["date"],
        reverse=True
    )
    
    # Statistics
    total_launches = len(launches)
    failures = len([a for a in anomalies if a["severity"] == "critical"])
    success_rate = round((total_launches - failures) / total_launches * 100, 2) if total_launches > 0 else 0
    
    result = {
        "summary": {
            "total_launches_analyzed": total_launches,
            "total_failures": failures,
            "success_rate": success_rate,
            "boosters_lost": len(landing_failures)
        },
        "timeline": all_anomalies[:20],
        "lost_boosters": landing_failures,
        "trend": "improving" if failures < 5 else "stable"
    }
    
    await cache.set(cache_key, result, ttl=3600)
    return result


@router.get("/weather-impact")
async def get_weather_impact_analysis(
    months: int = Query(12, ge=1, le=36, description="Months of data to analyze")
):
    """
    Analyze weather impact on launch operations.
    Correlates scrubs and delays with weather data from Open-Meteo.
    """
    cache_key = f"analytics:weather-impact:{months}"
    cached = await cache.get(cache_key)
    if cached:
        return cached
    
    # Get launches
    launches = await spacex_client.get_launches(limit=200, upcoming=False)
    
    # Get the most recent launch date and work backwards from there
    # (SpaceX API data may not be current)
    if launches:
        most_recent = max(l.date_utc for l in launches)
        cutoff = most_recent - timedelta(days=months * 30)
        launches = [l for l in launches if l.date_utc > cutoff]
    
    # Analyze by launchpad with real weather data
    launchpad_weather = {}
    all_weather_launches = []
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        for launchpad_id, pad_info in LAUNCHPADS.items():
            pad_launches = [l for l in launches if l.launchpad_id == launchpad_id]
            if not pad_launches:
                continue
            
            # Get historical weather for launches at this pad
            weather_samples = []
            weather_conditions = {"clear": 0, "cloudy": 0, "rain": 0, "wind": 0}
            
            # Sample up to 10 launches for weather data
            for launch in pad_launches[:10]:
                date_str = launch.date_utc.strftime("%Y-%m-%d")
                
                try:
                    # Fetch from Open-Meteo Archive API
                    weather_resp = await client.get(
                        "https://archive-api.open-meteo.com/v1/archive",
                        params={
                            "latitude": pad_info["lat"],
                            "longitude": pad_info["lon"],
                            "start_date": date_str,
                            "end_date": date_str,
                            "hourly": "temperature_2m,precipitation,wind_speed_10m,cloud_cover",
                            "timezone": "UTC"
                        }
                    )
                    
                    if weather_resp.status_code == 200:
                        weather_data = weather_resp.json()
                        hourly = weather_data.get("hourly", {})
                        
                        # Get weather at launch hour (approximate)
                        launch_hour = launch.date_utc.hour
                        
                        temp = hourly.get("temperature_2m", [None] * 24)[launch_hour]
                        precip = hourly.get("precipitation", [0] * 24)[launch_hour]
                        wind = hourly.get("wind_speed_10m", [0] * 24)[launch_hour]
                        clouds = hourly.get("cloud_cover", [0] * 24)[launch_hour]
                        
                        # Categorize weather
                        if precip and precip > 0.5:
                            condition = "rain"
                            weather_conditions["rain"] += 1
                        elif wind and wind > 40:
                            condition = "high_wind"
                            weather_conditions["wind"] += 1
                        elif clouds and clouds > 70:
                            condition = "cloudy"
                            weather_conditions["cloudy"] += 1
                        else:
                            condition = "clear"
                            weather_conditions["clear"] += 1
                        
                        weather_samples.append({
                            "date": date_str,
                            "mission": launch.name,
                            "success": launch.success,
                            "weather": {
                                "temperature_c": round(temp, 1) if temp else None,
                                "precipitation_mm": round(precip, 1) if precip else 0,
                                "wind_speed_kmh": round(wind, 1) if wind else 0,
                                "cloud_cover_pct": round(clouds) if clouds else 0,
                                "condition": condition
                            }
                        })
                        
                        all_weather_launches.append({
                            "mission": launch.name,
                            "pad": pad_info["name"],
                            "date": date_str,
                            "success": launch.success,
                            "wind_kmh": round(wind, 1) if wind else 0,
                            "precip_mm": round(precip, 1) if precip else 0
                        })
                        
                except Exception as e:
                    # If weather fetch fails, continue without it
                    weather_samples.append({
                        "date": date_str,
                        "mission": launch.name,
                        "success": launch.success,
                        "weather": None,
                        "error": str(e)[:50]
                    })
            
            # Calculate weather stats for this pad
            total_sampled = sum(weather_conditions.values())
            
            launchpad_weather[pad_info["name"]] = {
                "coordinates": {"lat": pad_info["lat"], "lon": pad_info["lon"]},
                "total_launches": len(pad_launches),
                "success_rate": round(
                    len([l for l in pad_launches if l.success]) / len(pad_launches) * 100, 1
                ) if pad_launches else 0,
                "weather_breakdown": {
                    "clear": weather_conditions["clear"],
                    "cloudy": weather_conditions["cloudy"],
                    "rain": weather_conditions["rain"],
                    "high_wind": weather_conditions["wind"],
                },
                "launches_with_weather": weather_samples
            }
    
    # Generate insights from real data
    weather_insights = []
    
    # Analyze wind correlation with success
    high_wind_launches = [l for l in all_weather_launches if l.get("wind_kmh", 0) > 30]
    if high_wind_launches:
        high_wind_success = len([l for l in high_wind_launches if l["success"]]) / len(high_wind_launches) * 100
        weather_insights.append({
            "insight": f"{len(high_wind_launches)} launches with wind >30 km/h",
            "detail": f"Success rate: {high_wind_success:.0f}%",
            "note": "SpaceX upper limit typically ~45 km/h at pad level"
        })
    
    # Precipitation analysis
    rain_launches = [l for l in all_weather_launches if l.get("precip_mm", 0) > 0]
    if rain_launches:
        weather_insights.append({
            "insight": f"{len(rain_launches)} launches with precipitation detected",
            "detail": f"Light rain doesn't always scrub - depends on lightning risk",
            "note": "Flight rules prohibit launch through precipitation if lightning within 10nm"
        })
    
    # Florida analysis
    florida_pads = ["CCSFS SLC 40", "KSC LC 39A"]
    florida_launches = [l for l in all_weather_launches if l.get("pad") in florida_pads]
    if florida_launches:
        florida_rain = len([l for l in florida_launches if l.get("precip_mm", 0) > 0])
        weather_insights.append({
            "insight": f"Florida: {len(florida_launches)} launches analyzed",
            "detail": f"{florida_rain} had precipitation at T-0",
            "note": "Afternoon thunderstorms common May-Oct, morning launches preferred"
        })
    
    # California analysis  
    vafb_launches = [l for l in all_weather_launches if l.get("pad") == "VAFB SLC 4E"]
    if vafb_launches:
        avg_wind = sum(l.get("wind_kmh", 0) for l in vafb_launches) / len(vafb_launches)
        weather_insights.append({
            "insight": f"Vandenberg: {len(vafb_launches)} launches, avg wind {avg_wind:.0f} km/h",
            "detail": "Coastal winds more consistent than Florida",
            "note": "Marine layer fog rarely impacts launches (burns off by afternoon)"
        })
    
    result = {
        "analysis_period_months": months,
        "total_launches_analyzed": len(launches),
        "launches_with_weather_data": len(all_weather_launches),
        "launchpad_stats": launchpad_weather,
        "weather_insights": weather_insights,
        "high_wind_launches": sorted(
            [l for l in all_weather_launches if l.get("wind_kmh", 0) > 25],
            key=lambda x: x.get("wind_kmh", 0),
            reverse=True
        )[:5],
        "data_source": "Open-Meteo Historical Archive API (open-meteo.com)",
        "note": "Real historical weather data at launch coordinates and time"
    }
    
    await cache.set(cache_key, result, ttl=7200)  # 2 hour cache
    return result


@router.get("/decision-recommendations")
async def get_decision_recommendations():
    """
    Generate actionable recommendations based on all analytics.
    Aggregates insights for ops team decision making.
    """
    # Gather data from other endpoints (using cache)
    turnaround = await get_turnaround_times()
    cross_mission = await get_cross_mission_analysis()
    anomalies = await get_anomaly_timeline()
    
    recommendations = []
    
    # Turnaround recommendations
    if turnaround["fleet_stats"]["average_turnaround_days"] > 60:
        recommendations.append({
            "category": "TURNAROUND",
            "priority": "medium",
            "recommendation": "Fleet turnaround averaging over 60 days - review refurbishment pipeline",
            "metric": f"{turnaround['fleet_stats']['average_turnaround_days']} day average"
        })
    
    # Top performers
    if turnaround["top_performers"]:
        top = turnaround["top_performers"][0]
        recommendations.append({
            "category": "BOOSTER_OPTIMIZATION",
            "priority": "info",
            "recommendation": f"Booster {top['booster']} achieving {top['average_turnaround_days']}-day turnaround - study for best practices",
            "metric": f"{top['total_flights']} flights"
        })
    
    # Mission mix
    mission_stats = cross_mission.get("mission_type_stats", {})
    starlink_pct = 0
    if mission_stats:
        total = sum(m["total_launches"] for m in mission_stats.values())
        starlink = mission_stats.get("Starlink", {}).get("total_launches", 0)
        starlink_pct = round(starlink / total * 100) if total > 0 else 0
    
    if starlink_pct > 70:
        recommendations.append({
            "category": "FLEET_DIVERSITY",
            "priority": "low",
            "recommendation": f"Starlink missions at {starlink_pct}% - consider fleet diversification for risk balance",
            "metric": f"{starlink_pct}% concentration"
        })
    
    # Anomaly trends
    if anomalies["summary"]["total_failures"] > 0:
        recommendations.append({
            "category": "RELIABILITY",
            "priority": "high" if anomalies["trend"] != "improving" else "info",
            "recommendation": f"Review {anomalies['summary']['total_failures']} historical failures for pattern analysis",
            "metric": f"{anomalies['summary']['success_rate']}% success rate"
        })
    
    # Sort by priority
    priority_order = {"high": 0, "medium": 1, "low": 2, "info": 3}
    recommendations.sort(key=lambda x: priority_order.get(x["priority"], 4))
    
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "recommendations": recommendations,
        "summary": {
            "high_priority": len([r for r in recommendations if r["priority"] == "high"]),
            "total": len(recommendations)
        }
    }
