"""
PRAGATI - Seed Data Generator
Generates realistic India HMIS-style health data for AlloyDB
"""
import asyncio
import asyncpg
import random
import os
from dotenv import load_dotenv

load_dotenv()

# Real Indian states and sample districts
STATES_DISTRICTS = {
    "Uttar Pradesh": ["Lucknow", "Kanpur", "Varanasi", "Agra", "Allahabad", "Meerut"],
    "Maharashtra": ["Mumbai", "Pune", "Nagpur", "Nashik", "Aurangabad", "Solapur"],
    "Bihar": ["Patna", "Gaya", "Muzaffarpur", "Bhagalpur", "Darbhanga", "Arrah"],
    "West Bengal": ["Kolkata", "Howrah", "Asansol", "Siliguri", "Durgapur", "Bardhaman"],
    "Rajasthan": ["Jaipur", "Jodhpur", "Kota", "Bikaner", "Ajmer", "Udaipur"],
    "Tamil Nadu": ["Chennai", "Coimbatore", "Madurai", "Tiruchirappalli", "Salem", "Tirunelveli"],
    "Karnataka": ["Bengaluru", "Mysuru", "Hubballi", "Mangaluru", "Belagavi", "Kalaburagi"],
    "Gujarat": ["Ahmedabad", "Surat", "Vadodara", "Rajkot", "Bhavnagar", "Jamnagar"],
    "Madhya Pradesh": ["Bhopal", "Indore", "Jabalpur", "Gwalior", "Ujjain", "Sagar"],
    "Andhra Pradesh": ["Visakhapatnam", "Vijayawada", "Guntur", "Nellore", "Kurnool", "Rajahmundry"],
}

HEALTH_INDICATORS = [
    ("Infant Mortality Rate", "per 1000 live births", "maternal_child", 20, 60),
    ("Maternal Mortality Ratio", "per 100000 live births", "maternal_child", 50, 200),
    ("Under-5 Mortality Rate", "per 1000 live births", "maternal_child", 25, 80),
    ("Full Immunization Coverage", "percentage", "immunization", 55, 95),
    ("Institutional Delivery Rate", "percentage", "maternal_child", 60, 99),
    ("Stunting Prevalence", "percentage", "nutrition", 25, 55),
    ("Wasting Prevalence", "percentage", "nutrition", 10, 30),
    ("Anaemia in Women", "percentage", "nutrition", 40, 75),
    ("OPD Attendance per 1000", "per 1000 population", "service_utilization", 200, 800),
    ("TB Detection Rate", "percentage", "disease_control", 50, 90),
    ("Malaria API", "annual parasite index", "disease_control", 0.1, 5.0),
    ("Contraceptive Prevalence Rate", "percentage", "family_planning", 45, 80),
    ("ANC Coverage", "percentage", "maternal_child", 65, 98),
    ("Skilled Birth Attendance", "percentage", "maternal_child", 65, 99),
    ("Hand Hygiene Access", "percentage", "sanitation", 30, 85),
]

FACILITY_TYPES = ["PHC", "CHC", "District Hospital", "Sub-Centre", "UCHC", "Medical College Hospital"]
DISEASES = ["Malaria", "Dengue", "Tuberculosis", "Typhoid", "Diarrhea", "COVID-19",
            "Chikungunya", "Japanese Encephalitis", "Leptospirosis", "Cholera"]


async def seed(conn):
    print("Seeding health_indicators...")
    hi_rows = []
    for state, districts in STATES_DISTRICTS.items():
        for district in districts:
            for year in [2021, 2022, 2023, 2024]:
                for name, unit, category, lo, hi in HEALTH_INDICATORS:
                    val = round(random.uniform(lo, hi), 2)
                    hi_rows.append((state, district, year, name, val, unit, category))

    await conn.executemany(
        """INSERT INTO health_indicators (state, district, year, indicator_name, value, unit, category)
           VALUES ($1,$2,$3,$4,$5,$6,$7) ON CONFLICT DO NOTHING""",
        hi_rows
    )
    print(f"  Inserted {len(hi_rows)} health indicator rows")

    print("Seeding facilities...")
    fac_rows = []
    fid = 1
    for state, districts in STATES_DISTRICTS.items():
        for district in districts:
            n = random.randint(4, 8)
            for _ in range(n):
                ftype = random.choice(FACILITY_TYPES)
                beds = random.randint(10, 500) if ftype != "Sub-Centre" else 0
                staff = random.randint(3, beds // 2 + 5)
                fac_rows.append((
                    f"{ftype} {district} {fid}",
                    state, district, ftype, beds, staff, random.random() > 0.05
                ))
                fid += 1

    await conn.executemany(
        """INSERT INTO facilities (name, state, district, facility_type, beds, staff_count, is_functional)
           VALUES ($1,$2,$3,$4,$5,$6,$7) ON CONFLICT DO NOTHING""",
        fac_rows
    )
    print(f"  Inserted {len(fac_rows)} facility rows")

    print("Seeding disease_reports...")
    dr_rows = []
    for state, districts in STATES_DISTRICTS.items():
        for district in districts:
            for disease in random.sample(DISEASES, 5):
                for year in [2022, 2023, 2024]:
                    for month in random.sample(range(1, 13), 6):
                        cases = random.randint(0, 500)
                        deaths = random.randint(0, max(1, cases // 50))
                        dr_rows.append((state, district, disease, cases, deaths, year, month))

    await conn.executemany(
        """INSERT INTO disease_reports (state, district, disease, cases, deaths, year, month)
           VALUES ($1,$2,$3,$4,$5,$6,$7) ON CONFLICT DO NOTHING""",
        dr_rows
    )
    print(f"  Inserted {len(dr_rows)} disease report rows")
    print("Seeding complete!")


async def main():
    dsn = (
        f"postgresql://{os.getenv('ALLOYDB_USER', 'postgres')}:"
        f"{os.getenv('ALLOYDB_PASS', 'postgres')}@"
        f"{os.getenv('ALLOYDB_HOST', '127.0.0.1')}:"
        f"{os.getenv('ALLOYDB_PORT', '5432')}/"
        f"{os.getenv('ALLOYDB_DB', 'pragati')}"
    )
    conn = await asyncpg.connect(dsn)
    try:
        await seed(conn)
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
