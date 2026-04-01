# database/tables_metadata.py

metadata = [

    # ── RAW TABLES — AUGUST ────────────────────────────────────────────
    {
        "table_name": "yellow_tripdata_2025_08",
        "schema_name": "raw",
        "description": "Raw trip-level data for yellow taxis in August 2025 including pickup/dropoff time, fare, distance, and payment details.",
        "key_columns": "vendorid, tpep_pickup_datetime, tpep_dropoff_datetime, passenger_count, trip_distance, pulocationid, dolocationid, fare_amount, total_amount, congestion_surcharge, airport_fee",
        "examples": "how many yellow taxi trips were completed in august? what is total fare for yellow taxis in august? what is average tip amount for yellow taxis in august? how many passengers travelled in yellow taxis in august?"
    },
    {
        "table_name": "green_tripdata_2025_08",
        "schema_name": "raw",
        "description": "Raw trip-level data for green taxis in August 2025 with similar structure to yellow taxis, including fares and trip metrics.",
        "key_columns": "vendorid, lpep_pickup_datetime, lpep_dropoff_datetime, passenger_count, trip_distance, pulocationid, dolocationid, fare_amount, total_amount, congestion_surcharge",
        "examples": "how many green taxi trips were completed in august? what is average fare for green taxis in august? what is total revenue for green taxis in august?"
    },
    {
        "table_name": "fhv_tripdata_2025_08",
        "schema_name": "raw",
"description": "Raw FHV (For-Hire Vehicle) trip data. Contains ONLY pickup/dropoff timestamps and location IDs. NO fare data, NO trip_distance, NO revenue, NO tips. Use ONLY for counting FHV dispatched trips or base number analysis. Do NOT use for any revenue or distance questions.",
        "key_columns": "dispatching_base_num, pickup_datetime, dropoff_datetime, pulocationid, dolocationid, sr_flag, affiliated_base_number",
        "examples": "how many for-hire vehicle trips were completed in august? which base dispatched the most trips in august? how many fhv trips were made from JFK airport in august?"
    },
    {
        "table_name": "fhvhv_tripdata_2025_08",
        "schema_name": "raw",
"description": "Raw high-volume FHV trip data for Uber and Lyft. Has driver_pay, base_passenger_fare, tips, trip_miles columns. No zone names — JOIN to analytics.taxi_zones using pulocationid = locationid. Use ONLY for Uber/Lyft specific analysis. Do NOT use for yellow/green taxi questions.",
        "key_columns": "hvfhs_license_num, dispatching_base_num, pickup_datetime, dropoff_datetime, pulocationid, dolocationid, trip_miles, base_passenger_fare, driver_pay, congestion_surcharge, tips",
        "examples": "what is total driver pay for uber trips in august? how many high volume for-hire trips were completed in august? what is average trip miles for hvfhv in august? what is total tips earned by drivers in august?"
    },

    # ── RAW TABLES — SEPTEMBER ─────────────────────────────────────────
    {
        "table_name": "yellow_tripdata_2025_09",
        "schema_name": "raw",
        "description": "Raw trip-level data for yellow taxis in September 2025 including pickup/dropoff time, fare, distance, and payment details.",
        "key_columns": "vendorid, tpep_pickup_datetime, tpep_dropoff_datetime, passenger_count, trip_distance, pulocationid, dolocationid, fare_amount, total_amount, congestion_surcharge, airport_fee",
        "examples": "how many yellow taxi trips were completed in september? what is total fare for yellow taxis in september? what is average tip amount for yellow taxis in september? how many passengers travelled in yellow taxis in september?"
    },
    {
        "table_name": "green_tripdata_2025_09",
        "schema_name": "raw",
        "description": "Raw trip-level data for green taxis in September 2025 with similar structure to yellow taxis, including fares and trip metrics.",
        "key_columns": "vendorid, lpep_pickup_datetime, lpep_dropoff_datetime, passenger_count, trip_distance, pulocationid, dolocationid, fare_amount, total_amount, congestion_surcharge",
        "examples": "how many green taxi trips were completed in september? what is average fare for green taxis in september? what is total revenue for green taxis in september?"
    },
    {
        "table_name": "fhv_tripdata_2025_09",
        "schema_name": "raw",
"description": "Raw FHV (For-Hire Vehicle) trip data. Contains ONLY pickup/dropoff timestamps and location IDs. NO fare data, NO trip_distance, NO revenue, NO tips. Use ONLY for counting FHV dispatched trips or base number analysis. Do NOT use for any revenue or distance questions.",
        "key_columns": "dispatching_base_num, pickup_datetime, dropoff_datetime, pulocationid, dolocationid, sr_flag, affiliated_base_number",
        "examples": "how many for-hire vehicle trips were completed in september? which base dispatched the most trips in september? how many fhv trips were made from JFK airport in september?"
    },
    {
        "table_name": "fhvhv_tripdata_2025_09",
        "schema_name": "raw",
"description": "Raw high-volume FHV trip data for Uber and Lyft. Has driver_pay, base_passenger_fare, tips, trip_miles columns. No zone names — JOIN to analytics.taxi_zones using pulocationid = locationid. Use ONLY for Uber/Lyft specific analysis. Do NOT use for yellow/green taxi questions.",
        "key_columns": "hvfhs_license_num, dispatching_base_num, pickup_datetime, dropoff_datetime, pulocationid, dolocationid, trip_miles, base_passenger_fare, driver_pay, congestion_surcharge, tips",
        "examples": "what is total driver pay for uber trips in september? how many high volume for-hire trips were completed in september? what is average trip miles for hvfhv in september? what is total tips earned by drivers in september?"
    },

    # ── STAGING TABLES ─────────────────────────────────────────────────
    {
        "table_name": "trips_unified_2025_08",
        "schema_name": "staging",
"description": "Unified staging table combining yellow and green taxi trips for September 2025. Use ONLY when you need raw service_type comparison without computed columns. PREFER analytics.fact_taxi_trips_2025_09 over this — it has pre-computed pickup_hour, avg_speed_mph, and better indexing.",
        "key_columns": "service_type, vendorid, pickup_datetime, dropoff_datetime, passenger_count, trip_distance, pulocationid, dolocationid, total_amount, tip_amount, congestion_surcharge",
        "examples": "how many total trips across yellow and green taxis in august? what is average trip distance in august? compare revenue between yellow and green taxis in august?"
    },
    {
        "table_name": "trips_unified_2025_09",
        "schema_name": "staging",
"description": "Unified staging table combining yellow and green taxi trips for September 2025. Use ONLY when you need raw service_type comparison without computed columns. PREFER analytics.fact_taxi_trips_2025_09 over this — it has pre-computed pickup_hour, avg_speed_mph, and better indexing.",
        "key_columns": "service_type, vendorid, pickup_datetime, dropoff_datetime, passenger_count, trip_distance, pulocationid, dolocationid, total_amount, tip_amount, congestion_surcharge",
        "examples": "how many total trips across yellow and green taxis in september? what is average trip distance in september? compare revenue between yellow and green taxis in september?"
    },

    # ── ANALYTICS TABLES ───────────────────────────────────────────────
    {
        "table_name": "fact_taxi_trips_2025_08",
        "schema_name": "analytics",
"description": "PRIMARY analytics table for August 2025. Use this for ANY trip count, revenue, distance, speed, tip, or time analysis for August specifically. Has pre-computed pickup_hour (integer), pickup_day_of_week (integer), avg_speed_mph (numeric). JOIN to analytics.taxi_zones using pulocationid = locationid for borough or zone names.",
        "key_columns": "service_type, pickup_datetime, dropoff_datetime, trip_distance, total_amount, tip_amount, passenger_count, pulocationid, dolocationid, pickup_hour, pickup_day_of_week, avg_speed_mph",
        "examples": "which zones had most revenue in august? how many trips per hour in august? what is average speed by time of day in august? which day of week has most trips in august?"
    },
    {
        "table_name": "fact_taxi_trips_2025_09",
        "schema_name": "analytics",
"description": "PRIMARY analytics table for September 2025. Use this for ANY trip count, revenue, distance, speed, tip, or time analysis for September. Has pre-computed pickup_hour (integer), pickup_day_of_week (integer), avg_speed_mph (numeric). JOIN to analytics.taxi_zones using pulocationid = locationid for borough or zone names. Use this over raw or staging tables.",
        "key_columns": "service_type, pickup_datetime, dropoff_datetime, trip_distance, total_amount, tip_amount, passenger_count, pulocationid, dolocationid, pickup_hour, pickup_day_of_week, avg_speed_mph",
        "examples": "which zones had most revenue in september? how many trips per hour in september? what is average speed by time of day in september? which day of week has most trips in september?"
    },
    {
        "table_name": "taxi_zones",
        "schema_name": "analytics",
        "description": "Geographic lookup table mapping location IDs to NYC boroughs and zone names. JOIN to fact tables using pulocationid = locationid for pickup zone or dolocationid = locationid for dropoff zone.",
        "key_columns": "locationid, borough, zone, service_zone",
        "examples": "which borough had most pickups? what zones are in manhattan? how many trips started in brooklyn? which service zone had highest revenue?"
    },
    {
        "table_name": "dim_date",
        "schema_name": "analytics",
        "description": "Shared date dimension table covering all months. Contains calendar attributes for each trip date including year, month, day, and day of week.",
        "key_columns": "trip_date, year, month, day, day_of_week",
        "examples": "how many trips on a specific date? which month had most trips? what day of week has highest trip volume? how many trips in august vs september?"
    },

    # ── VIEWS ──────────────────────────────────────────────────────────
    {
        "table_name": "fact_taxi_trips_all",
        "schema_name": "views",
        "description": "Unified view combining both August and September fact tables. Use this for any cross-month analysis, trends over time, or when the question does not specify a particular month. Includes a month_partition column ('2025-08' or '2025-09') for filtering.",
        "key_columns": "service_type, pickup_datetime, dropoff_datetime, trip_distance, total_amount, tip_amount, passenger_count, pulocationid, dolocationid, pickup_hour, pickup_day_of_week, avg_speed_mph, month_partition",
        "examples": "how did trips change from august to september? what is total revenue across both months? compare trip volume month over month? what are overall trends across august and september?"
    },
    {
        "table_name": "trips_with_zones",
        "schema_name": "views",
"description": "Pre-joined view with pickup_borough, pickup_zone, dropoff_borough, dropoff_zone already resolved. Query directly — NEVER JOIN this view to analytics.taxi_zones, that join is already done. Use for any question involving borough or zone names without manual JOIN. Contains month_partition column for filtering by month.",
        "key_columns": "service_type, pickup_datetime, dropoff_datetime, trip_distance, total_amount, tip_amount, pickup_hour, pickup_day_of_week, avg_speed_mph, month_partition, pickup_borough, pickup_zone, pickup_service_zone, dropoff_borough, dropoff_zone, dropoff_service_zone",
        "examples": "which pickup borough had most trips? what zones do people travel to most? show trips from manhattan to brooklyn? which dropoff zone generates highest tips? where are people traveling from and to?"
    },
    {
        "table_name": "revenue_by_borough",
        "schema_name": "views",
        "description": "Pre-aggregated revenue and trip metrics grouped by borough, month, and service type. Use for borough-level revenue comparisons. No JOIN or aggregation needed — query directly.",
        "key_columns": "borough, month_partition, service_type, total_trips, total_revenue, avg_revenue_per_trip, avg_tip, avg_distance",
        "examples": "which borough made the most revenue? compare revenue between manhattan and brooklyn? what is average fare per trip by borough? which borough had most trips in august vs september?"
    },
    {
        "table_name": "trips_by_hour",
        "schema_name": "views",
"description": "Pre-aggregated view grouped by pickup_hour, month_partition, service_type. Contains total_trips, avg_fare, avg_distance, avg_speed already calculated per hour. Query directly without GROUP BY or aggregation. NEVER use for borough-level hourly analysis — use fact tables with JOIN to taxi_zones for that.",
        "key_columns": "pickup_hour, month_partition, service_type, total_trips, avg_fare, avg_distance, avg_speed",
        "examples": "which hour has most trips? what is the peak hour for taxi rides? how does average fare change by hour? which hour has highest average speed? when is the busiest time of day?"
    },
    {
        "table_name": "trips_by_day_of_week",
        "schema_name": "views",
"description": "Pre-aggregated view grouped by day of week with human-readable day names. Contains total_trips, avg_fare, avg_tip, avg_distance already calculated per day. Query directly without GROUP BY. NEVER use for week-over-week calculations — use fact_taxi_trips_2025_09 with DATE_TRUNC for weekly aggregation.",
        "key_columns": "pickup_day_of_week, day_name, month_partition, service_type, total_trips, avg_fare, avg_tip, avg_distance",
        "examples": "which day of week has most trips? compare weekday vs weekend trips? what is average fare on fridays? which day has highest tips? do people travel more on weekends?"
    },
    {
        "table_name": "service_type_summary",
        "schema_name": "views",
        "description": "Pre-aggregated summary comparing yellow vs green taxi performance including total trips, revenue, average fare, tips, distance, passengers, speed, and congestion surcharge by month. Use for any yellow vs green comparison question.",
        "key_columns": "service_type, month_partition, total_trips, total_revenue, avg_fare, avg_tip, avg_distance, avg_passengers, avg_speed, total_congestion_surcharge",
        "examples": "compare yellow vs green taxis? which service type makes more revenue? what is average fare for yellow vs green? which cab type has higher tips? how do yellow and green taxis compare overall?"
    },
    {
        "table_name": "zone_performance",
        "schema_name": "views",
        "description": "Pre-aggregated performance metrics for every NYC taxi zone including total trips, revenue, average fare, tips, and speed grouped by zone, borough, month, and service type. Use for zone-level rankings and comparisons.",
        "key_columns": "zone, borough, service_zone, month_partition, service_type, total_trips, total_revenue, avg_fare, avg_tip, avg_speed",
        "examples": "which zone had highest revenue? top 10 zones by trip count? which zone has highest average tip? compare zone performance between august and september? which zones in queens perform best?"
    }
]