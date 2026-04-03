from datetime import UTC, datetime, timedelta

import gpxpy
import gpxpy.gpx


def build_gpx_from_streams(activity, streams):
    """Build a GPX file (bytes) from Strava activity metadata and streams.

    ``activity`` is the dict from the Strava activities list API.
    ``streams`` is the dict (keyed by type) from the streams API.

    Returns UTF-8 encoded GPX XML bytes, or None if no GPS data.
    """
    latlng = streams.get("latlng", {}).get("data")
    if not latlng:
        return None

    time_offsets = streams.get("time", {}).get("data")
    altitude_data = streams.get("altitude", {}).get("data")

    start_date_str = activity.get("start_date")
    if start_date_str:
        start_date = datetime.fromisoformat(start_date_str.replace("Z", "+00:00"))
    else:
        start_date = datetime.now(UTC)

    gpx = gpxpy.gpx.GPX()
    gpx_track = gpxpy.gpx.GPXTrack()
    gpx_track.name = activity.get("name", "Strava Activity")
    gpx.tracks.append(gpx_track)

    gpx_segment = gpxpy.gpx.GPXTrackSegment()
    gpx_track.segments.append(gpx_segment)

    for i, (lat, lon) in enumerate(latlng):
        point = gpxpy.gpx.GPXTrackPoint(latitude=lat, longitude=lon)

        if time_offsets and i < len(time_offsets):
            point.time = start_date + timedelta(seconds=time_offsets[i])

        if altitude_data and i < len(altitude_data):
            point.elevation = altitude_data[i]

        gpx_segment.points.append(point)

    return gpx.to_xml().encode("utf-8")
