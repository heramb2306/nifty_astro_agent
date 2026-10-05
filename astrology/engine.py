import math
import ephem
from datetime import datetime
import pytz

NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni",
    "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
    "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha",
    "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"
]
ZODIAC_SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

class VedicAstrologyEngine:
    def __init__(self):
        self.obs = ephem.Observer()
        self.obs.lat, self.obs.lon, self.obs.elevation = "19.0760", "72.8777", 14

    def get_lahiri_ayanamsa(self, dt):
        t = (ephem.julian_date(dt) - 2451545.0) / 36525.0
        return 23.85 + (1.396 * t)

    def calculate_ephemeris(self, target_dt):
        utc = target_dt.astimezone(pytz.UTC)
        self.obs.date = ephem.Date(utc)
        ay = self.get_lahiri_ayanamsa(utc)
        bodies = {
            "Sun": ephem.Sun(self.obs), "Moon": ephem.Moon(self.obs),
            "Mercury": ephem.Mercury(self.obs), "Venus": ephem.Venus(self.obs),
            "Mars": ephem.Mars(self.obs), "Jupiter": ephem.Jupiter(self.obs), "Saturn": ephem.Saturn(self.obs)
        }
        res = {}
        for name, b in bodies.items():
            lon = (math.degrees(ephem.Ecliptic(b).lon) - ay) % 360.0
            res[name] = {
                "sign": ZODIAC_SIGNS[int(lon // 30)],
                "degree": round(lon % 30, 2),
                "nakshatra": NAKSHATRAS[int(lon // (360/27))],
                "retrograde": False
            }
        moon_lon = (math.degrees(ephem.Ecliptic(bodies["Moon"]).lon) - ay) % 360.0
        sun_lon = (math.degrees(ephem.Ecliptic(bodies["Sun"]).lon) - ay) % 360.0
        tithi_num = int(((moon_lon - sun_lon) % 360.0) // 12) + 1
        return {"positions": res, "tithi": f"Tithi {tithi_num}", "moon_nakshatra": res["Moon"]["nakshatra"]}

    def calculate_astro_score(self, ephem_data):
        score = 0
        factors = []
        nak = ephem_data["moon_nakshatra"]
        bullish = ["Rohini", "Pushya", "Hasta", "Shravana", "Revati"]
        bearish = ["Ardra", "Ashlesha", "Jyeshtha", "Mula", "Bharani"]
        if nak in bullish:
            score += 30; factors.append(f"Moon in expansive Nakshatra: {nak} (+30)")
        elif nak in bearish:
            score -= 30; factors.append(f"Moon in contractionary Nakshatra: {nak} (-30)")
        else:
            factors.append(f"Moon in neutral Nakshatra: {nak} (0)")
        return {"score": max(-100, min(100, score)), "factors": factors}
