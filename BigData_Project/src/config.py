"""
Centralized configuration for the NYC Taxi EV Charging Analysis project.
"""

import os


class Config:
    """All project-wide settings in one place."""

    # ------------------------------------------------------------------ paths
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_DIR          = os.path.join(PROJECT_ROOT, "data")
    RAW_DATA_DIR      = os.path.join(DATA_DIR, "raw")
    PROCESSED_DATA_DIR = os.path.join(DATA_DIR, "processed")
    SAMPLE_DATA_DIR   = os.path.join(DATA_DIR, "sample")
    OUTPUT_DIR        = os.path.join(PROJECT_ROOT, "outputs")
    CHARTS_DIR        = os.path.join(OUTPUT_DIR, "charts")
    MODELS_DIR        = os.path.join(OUTPUT_DIR, "models")
    RESULTS_DIR       = os.path.join(OUTPUT_DIR, "results")

    # --------------------------------------------------------- data file paths
    RAW_DATA_PATH       = os.path.join(RAW_DATA_DIR,       "nyc_taxi_data.csv")
    PROCESSED_DATA_PATH = os.path.join(PROCESSED_DATA_DIR, "taxi_features.parquet")
    ZONE_AGG_PATH       = os.path.join(PROCESSED_DATA_DIR, "zone_aggregates.parquet")

    # ------------------------------------------------------- dataset settings
    SYNTHETIC_RECORDS = 100_000       # default number of rows to generate
    SAMPLE_FRACTIONS  = [0.05, 0.25, 0.75, 1.0]  # for scalability test

    # ---------------------------------------------------------- Spark settings
    SPARK_DRIVER_MEMORY   = "4g"
    SPARK_EXECUTOR_MEMORY = "4g"
    SPARK_SHUFFLE_PARTS   = "50"

    # ------------------------------------------------------------ ML settings
    NUM_CLUSTERS      = 8
    KMEANS_MAX_ITER   = 50
    KMEANS_SEED       = 42
    TRAIN_RATIO       = 0.8
    TEST_RATIO        = 0.2
    RANDOM_SEED       = 42

    # ---------------------------------------------------- EV station settings
    EV_COVERAGE_RADIUS_KM  = 1.0    # radius (km) considered "served"
    MIN_TRIPS_FOR_HOTSPOT  = 500    # trips per zone to be considered a hotspot
    TOP_N_RECOMMENDATIONS  = 10

    # ----------------------------------------------- visualisation settings
    FIGURE_DPI    = 150
    FIGURE_SIZE   = (12, 8)
    COLOR_PALETTE = "viridis"

    # ---------------------------------------------- scalability test sizes
    SCALABILITY_SIZES = [5_000, 25_000, 75_000, 150_000]

    # ----------------------------------------------------- CO2 constants
    # grams of CO2 per mile
    GASOLINE_CO2_PER_MILE = 404.0   # NYC taxi average (EPA estimate)
    EV_CO2_PER_MILE       =  80.0   # EV equivalent (NYC grid mix)

    def __init__(self, args=None):
        if args:
            if getattr(args, "num_records", None):
                self.SYNTHETIC_RECORDS = args.num_records
            if getattr(args, "num_clusters", None):
                self.NUM_CLUSTERS = args.num_clusters
            if getattr(args, "data_path", None):
                self.RAW_DATA_PATH = args.data_path

        # Ensure all directories exist
        for d in [
            self.RAW_DATA_DIR, self.PROCESSED_DATA_DIR, self.SAMPLE_DATA_DIR,
            self.CHARTS_DIR, self.MODELS_DIR, self.RESULTS_DIR,
        ]:
            os.makedirs(d, exist_ok=True)

    # Convenience properties so callers can use snake_case attributes
    @property
    def raw_data_path(self):        return self.RAW_DATA_PATH

    @property
    def processed_data_path(self):  return self.PROCESSED_DATA_PATH

    @property
    def zone_agg_path(self):        return self.ZONE_AGG_PATH

    @property
    def output_dir(self):           return self.OUTPUT_DIR

    @property
    def charts_dir(self):           return self.CHARTS_DIR

    @property
    def results_dir(self):          return self.RESULTS_DIR

    @property
    def num_records(self):          return self.SYNTHETIC_RECORDS


# ---------------------------------------------------------------------------
# NYC Taxi Zone lookup  (zone_id → name, borough, lat, lon, demand_weight 1-10)
# ---------------------------------------------------------------------------
NYC_ZONES = {
    # Manhattan — very high demand
    161: ("Midtown Center",          "Manhattan",    40.7549, -73.9840, 10),
    162: ("Midtown East",            "Manhattan",    40.7549, -73.9680,  9),
    163: ("Midtown North",           "Manhattan",    40.7680, -73.9880,  9),
    224: ("Times Sq/Theatre Dist",   "Manhattan",    40.7590, -73.9845, 10),
    186: ("Penn Station/Madison Sq", "Manhattan",    40.7505, -73.9934,  9),
    100: ("Garment District",        "Manhattan",    40.7540, -73.9960,  8),
    232: ("Union Square",            "Manhattan",    40.7359, -73.9911,  8),
    261: ("World Trade Center",      "Manhattan",    40.7127, -74.0134,  8),
    234: ("Upper East Side South",   "Manhattan",    40.7680, -73.9590,  8),
    237: ("Upper West Side South",   "Manhattan",    40.7789, -73.9835,  7),
    # Manhattan — high demand
    87:  ("Flatiron",                "Manhattan",    40.7410, -73.9897,  7),
    45:  ("Chelsea",                 "Manhattan",    40.7465, -74.0014,  7),
    79:  ("East Village",            "Manhattan",    40.7264, -73.9805,  7),
    202: ("SoHo",                    "Manhattan",    40.7230, -74.0024,  7),
    114: ("Greenwich Village South", "Manhattan",    40.7286, -74.0013,  6),
    113: ("Greenwich Village North", "Manhattan",    40.7333, -74.0016,  6),
    158: ("Meatpacking/West Village","Manhattan",    40.7395, -74.0075,  6),
    170: ("Murray Hill",             "Manhattan",    40.7490, -73.9780,  6),
    128: ("Kips Bay",                "Manhattan",    40.7434, -73.9768,  6),
    # Manhattan — medium demand
    246: ("Washington Heights N",    "Manhattan",    40.8589, -73.9350,  4),
    247: ("Washington Heights S",    "Manhattan",    40.8492, -73.9330,  4),
    120: ("Harlem North",            "Manhattan",    40.8076, -73.9481,  5),
    116: ("Hamilton Heights",        "Manhattan",    40.8228, -73.9494,  4),
    151: ("Manhattan Valley",        "Manhattan",    40.8005, -73.9647,  5),
    236: ("Upper West Side North",   "Manhattan",    40.7887, -73.9757,  6),
    # Brooklyn
    17:  ("Bedford-Stuyvesant",      "Brooklyn",     40.6872, -73.9418,  5),
    97:  ("Greenpoint",              "Brooklyn",     40.7295, -73.9514,  5),
    67:  ("East Williamsburg",       "Brooklyn",     40.7137, -73.9338,  5),
    29:  ("Brooklyn Heights",        "Brooklyn",     40.6960, -73.9936,  6),
    25:  ("Boerum Hill",             "Brooklyn",     40.6877, -73.9857,  5),
    76:  ("Fort Greene",             "Brooklyn",     40.6920, -73.9752,  5),
    89:  ("Gowanus",                 "Brooklyn",     40.6771, -73.9928,  4),
    63:  ("DUMBO/Vinegar Hill",      "Brooklyn",     40.7030, -73.9893,  5),
    36:  ("Carroll Gardens",         "Brooklyn",     40.6800, -73.9990,  4),
    54:  ("Coney Island",            "Brooklyn",     40.5755, -73.9707,  3),
    33:  ("Bushwick North",          "Brooklyn",     40.7061, -73.9215,  4),
    72:  ("Flatlands",               "Brooklyn",     40.6234, -73.9318,  3),
    # Queens
    7:   ("Astoria",                 "Queens",       40.7721, -73.9301,  6),
    117: ("Long Island City",        "Queens",       40.7471, -73.9417,  6),
    121: ("Queens Plaza",            "Queens",       40.7481, -73.9435,  5),
    73:  ("Flushing",                "Queens",       40.7675, -73.8330,  5),
    101: ("Jackson Heights",         "Queens",       40.7554, -73.8830,  5),
    129: ("LaGuardia Airport",       "Queens",       40.7773, -73.8740,  8),
    132: ("JFK Airport",             "Queens",       40.6413, -73.7781,  8),
    86:  ("Forest Hills",            "Queens",       40.7176, -73.8448,  4),
    102: ("Jamaica",                 "Queens",       40.6938, -73.8055,  4),
    53:  ("Corona",                  "Queens",       40.7448, -73.8660,  4),
    # Bronx
    59:  ("Concourse/Concourse Vil", "Bronx",        40.8266, -73.9196,  3),
    78:  ("East Tremont",            "Bronx",        40.8416, -73.8790,  2),
    110: ("Melrose South/Mott Haven","Bronx",        40.8130, -73.9214,  3),
    103: ("Kingsbridge Heights",     "Bronx",        40.8699, -73.9043,  2),
    96:  ("Hunts Point",             "Bronx",        40.8132, -73.8902,  2),
    # Staten Island
    167: ("New Springville",         "Staten Island",40.5779, -74.1686,  2),
    223: ("Stapleton/Rosebank",      "Staten Island",40.6253, -74.0794,  2),
    250: ("West Brighton",           "Staten Island",40.6345, -74.1276,  1),
    # Airports / Special
    1:   ("Newark Airport",          "EWR",          40.6895, -74.1745,  5),
}

# Existing NYC EV charging station locations (synthetic but geographically realistic)
EXISTING_EV_STATIONS = [
    # (name, lat, lon, num_chargers)
    ("Midtown Manhattan Garage",      40.7540, -73.9870, 8),
    ("Times Square Charging Hub",     40.7580, -73.9855, 12),
    ("JFK Airport Lot E",             40.6390, -73.7760, 20),
    ("LaGuardia Central Garage",      40.7770, -73.8735, 15),
    ("Brooklyn Downtown Lot",         40.6950, -73.9900, 6),
    ("Long Island City Depot",        40.7460, -73.9430, 10),
    ("Astoria Park & Charge",         40.7710, -73.9310, 4),
    ("Penn Station Area Garage",      40.7500, -73.9940, 8),
    ("Flatiron Charging Station",     40.7405, -73.9895, 6),
    ("World Trade Center Garage",     40.7115, -74.0125, 10),
    ("Upper East Side Depot",         40.7740, -73.9600, 6),
    ("Harlem 125th Street",           40.8080, -73.9470, 4),
    ("Bronx Hub Terminal",            40.8270, -73.9200, 4),
    ("Staten Island Ferry Terminal",  40.6436, -74.0736, 3),
    ("Forest Hills Station",          40.7185, -73.8460, 4),
    ("Jamaica Center",                40.6945, -73.8060, 6),
    ("Flushing Main St",              40.7680, -73.8335, 4),
    ("Newark Airport Hub",            40.6900, -74.1750, 12),
    ("Greenpoint Depot",              40.7290, -73.9510, 4),
    ("SoHo Parking Garage",           40.7225, -74.0020, 6),
]
