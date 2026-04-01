# rag/seed_examples.py

SQL_SAMPLES = [

    # ─────────────────────────────────────────────
    # DOMAIN: trip_analysis — SIMPLE
    # ─────────────────────────────────────────────
    {
        "question": "What is the average trip distance for yellow taxi trips in September 2025?",
        "sql_answer": """
SELECT AVG(trip_distance) AS avg_distance
FROM views.fact_taxi_trips_all
WHERE service_type = 'yellow'
  AND month_partition = '2025-09';
""".strip(),
        "domain": "trip_analysis",
        "difficulty": "simple",
    },
    {
        "question": "How many trips had more than 3 passengers across both months?",
        "sql_answer": """
SELECT COUNT(*) AS trips_above_3_passengers
FROM views.fact_taxi_trips_all
WHERE passenger_count > 3;
""".strip(),
        "domain": "trip_analysis",
        "difficulty": "simple",
    },
    {
        "question": "What is the average trip speed by service type in August 2025?",
        "sql_answer": """
SELECT service_type, avg_speed
FROM views.service_type_summary
WHERE month_partition = '2025-08';
""".strip(),
        "domain": "trip_analysis",
        "difficulty": "simple",
    },
    {
        "question": "What is the average number of passengers per trip for each service type?",
        "sql_answer": """
SELECT service_type, month_partition, avg_passengers
FROM views.service_type_summary
ORDER BY month_partition, service_type;
""".strip(),
        "domain": "trip_analysis",
        "difficulty": "simple",
    },
    {
        "question": "Find the top 5 fastest trips by average speed in September 2025.",
        "sql_answer": """
SELECT service_type, pickup_datetime, dropoff_datetime,
       trip_distance, avg_speed_mph
FROM analytics.fact_taxi_trips_2025_09
WHERE avg_speed_mph IS NOT NULL
  AND avg_speed_mph < 100
ORDER BY avg_speed_mph DESC
LIMIT 5;
""".strip(),
        "domain": "trip_analysis",
        "difficulty": "medium",
    },
    {
        "question": "Compare average trip distance between yellow and green taxis for each month.",
        "sql_answer": """
SELECT service_type, month_partition, avg_distance
FROM views.service_type_summary
WHERE service_type IN ('yellow', 'green')
ORDER BY month_partition, service_type;
""".strip(),
        "domain": "trip_analysis",
        "difficulty": "medium",
    },
    {
        "question": "What percentage of trips had zero or null trip distance?",
        "sql_answer": """
SELECT
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE trip_distance = 0 OR trip_distance IS NULL)
        / COUNT(*), 2
    ) AS pct_zero_distance
FROM views.fact_taxi_trips_all;
""".strip(),
        "domain": "trip_analysis",
        "difficulty": "medium",
    },

    # ─── PATTERN: avg_speed_mph correct usage ────────────────────────────────
    # Teaches: avg_speed_mph is pre-computed, filter nulls and outliers
    # Golden tests: speed during rush hours by borough (harder — adds time + weekday filter)
    {
        "question": "What is the average trip speed for each service type in September 2025?",
        "sql_answer": """
SELECT service_type,
       ROUND(AVG(avg_speed_mph)::numeric, 2) AS avg_speed
FROM analytics.fact_taxi_trips_2025_09
WHERE avg_speed_mph IS NOT NULL
  AND avg_speed_mph < 100
GROUP BY service_type
ORDER BY avg_speed DESC;
""".strip(),
        "domain": "trip_analysis",
        "difficulty": "simple",
    },

    # ─── PATTERN: CASE WHEN bucketing ────────────────────────────────────────
    # Teaches: CASE WHEN for creating categories
    # Golden tests: short/medium/long trip classes with avg revenue (harder — adds avg revenue)
    {
        "question": "How many trips fall into each passenger count category in September 2025?",
        "sql_answer": """
SELECT CASE
           WHEN passenger_count = 1 THEN 'solo'
           WHEN passenger_count BETWEEN 2 AND 3 THEN 'small group'
           ELSE 'large group'
       END AS passenger_category,
       COUNT(*) AS trip_count
FROM analytics.fact_taxi_trips_2025_09
WHERE passenger_count > 0
GROUP BY passenger_category
ORDER BY trip_count DESC;
""".strip(),
        "domain": "trip_analysis",
        "difficulty": "simple",
    },

    # ─── PATTERN: views.fact_taxi_trips_all basic cross-month ────────────────
    # Teaches: month_partition column usage
    # Golden tests: rolling avg, rank change across months (harder)
    {
        "question": "How many total trips happened in each month?",
        "sql_answer": """
SELECT month_partition, COUNT(*) AS total_trips
FROM views.fact_taxi_trips_all
GROUP BY month_partition
ORDER BY month_partition;
""".strip(),
        "domain": "trip_analysis",
        "difficulty": "simple",
    },

    # ─────────────────────────────────────────────
    # DOMAIN: location_analysis — SIMPLE
    # ─────────────────────────────────────────────
    {
        "question": "How many trips originated from Manhattan?",
        "sql_answer": """
SELECT COUNT(*) AS trips_from_manhattan
FROM views.trips_with_zones
WHERE pickup_borough = 'Manhattan';
""".strip(),
        "domain": "location_analysis",
        "difficulty": "simple",
    },
    {
        "question": "What is the average fare for trips that started in Brooklyn?",
        "sql_answer": """
SELECT ROUND(AVG(total_amount)::NUMERIC, 2) AS avg_fare
FROM views.trips_with_zones
WHERE pickup_borough = 'Brooklyn';
""".strip(),
        "domain": "location_analysis",
        "difficulty": "simple",
    },
    {
        "question": "Which pickup zone had the most trips in September 2025?",
        "sql_answer": """
SELECT zone, total_trips
FROM views.zone_performance
WHERE month_partition = '2025-09'
ORDER BY total_trips DESC
LIMIT 1;
""".strip(),
        "domain": "location_analysis",
        "difficulty": "simple",
    },
    {
        "question": "What are the top 5 pickup zones by total revenue in August 2025?",
        "sql_answer": """
SELECT zone, borough, total_revenue
FROM views.zone_performance
WHERE month_partition = '2025-08'
ORDER BY total_revenue DESC
LIMIT 5;
""".strip(),
        "domain": "location_analysis",
        "difficulty": "simple",
    },
    {
        "question": "Which dropoff borough received the most trips across all months?",
        "sql_answer": """
SELECT dropoff_borough,
       COUNT(*) AS total_dropoffs
FROM views.trips_with_zones
WHERE dropoff_borough IS NOT NULL
GROUP BY dropoff_borough
ORDER BY total_dropoffs DESC
LIMIT 5;
""".strip(),
        "domain": "location_analysis",
        "difficulty": "simple",
    },

    # ─── PATTERN: views.trips_with_zones correct usage — no extra JOIN ────────
    # Teaches: borough and zone columns already resolved, query directly
    # Golden tests: top dropoff zones from Manhattan, borough pair distances (harder)
    {
        "question": "How many trips started in each borough?",
        "sql_answer": """
SELECT pickup_borough, COUNT(*) AS trip_count
FROM views.trips_with_zones
GROUP BY pickup_borough
ORDER BY trip_count DESC;
""".strip(),
        "domain": "location_analysis",
        "difficulty": "simple",
    },
    {
        "question": "Show trips that went from Manhattan to Brooklyn.",
        "sql_answer": """
SELECT service_type, pickup_datetime, trip_distance, total_amount
FROM views.trips_with_zones
WHERE pickup_borough = 'Manhattan'
  AND dropoff_borough = 'Brooklyn'
ORDER BY pickup_datetime;
""".strip(),
        "domain": "location_analysis",
        "difficulty": "medium",
    },
    {
        "question": "Show total trips and average tip grouped by pickup borough.",
        "sql_answer": """
SELECT pickup_borough,
       COUNT(*)                                  AS total_trips,
       ROUND(AVG(tip_amount)::NUMERIC, 2)        AS avg_tip
FROM views.trips_with_zones
GROUP BY pickup_borough
ORDER BY total_trips DESC;
""".strip(),
        "domain": "location_analysis",
        "difficulty": "medium",
    },
    {
        "question": "Show average speed for trips between each borough pair.",
        "sql_answer": """
SELECT pickup_borough,
       dropoff_borough,
       ROUND(AVG(avg_speed_mph)::numeric, 2) AS avg_speed
FROM views.trips_with_zones
WHERE avg_speed_mph IS NOT NULL
  AND avg_speed_mph < 100
GROUP BY pickup_borough, dropoff_borough
ORDER BY avg_speed DESC;
""".strip(),
        "domain": "location_analysis",
        "difficulty": "medium",
    },

    # ─── PATTERN: two fact table JOIN to taxi_zones ───────────────────────────
    # Teaches: how to join taxi_zones twice for pickup and dropoff
    # Golden tests: borough pairs above avg distance, top zone pairs (harder)
    {
        "question": "How many trips started and ended in the same borough in September 2025?",
        "sql_answer": """
SELECT COUNT(*) AS same_borough_trips
FROM analytics.fact_taxi_trips_2025_09 f
JOIN analytics.taxi_zones pu ON f.pulocationid = pu.locationid
JOIN analytics.taxi_zones do ON f.dolocationid = do.locationid
WHERE pu.borough = do.borough;
""".strip(),
        "domain": "location_analysis",
        "difficulty": "medium",
    },

    # ─── PATTERN: cross-month zone comparison ────────────────────────────────
    # Teaches: CTE per month + JOIN on zone name
    # Golden tests: top 3 zones by growth % (harder — adds % calc and LIMIT 3)
    {
        "question": "Which zones had more trips in September than August 2025?",
        "sql_answer": """
WITH aug AS (
    SELECT z.zone, COUNT(*) AS aug_trips
    FROM analytics.fact_taxi_trips_2025_08 f
    JOIN analytics.taxi_zones z ON f.pulocationid = z.locationid
    GROUP BY z.zone
),
sep AS (
    SELECT z.zone, COUNT(*) AS sep_trips
    FROM analytics.fact_taxi_trips_2025_09 f
    JOIN analytics.taxi_zones z ON f.pulocationid = z.locationid
    GROUP BY z.zone
)
SELECT a.zone, a.aug_trips, s.sep_trips
FROM aug a
JOIN sep s ON a.zone = s.zone
WHERE s.sep_trips > a.aug_trips
ORDER BY s.sep_trips DESC;
""".strip(),
        "domain": "location_analysis",
        "difficulty": "medium",
    },

    # ─────────────────────────────────────────────
    # DOMAIN: revenue_analysis — SIMPLE
    # ─────────────────────────────────────────────
    {
        "question": "What is the total revenue collected by borough in September 2025?",
        "sql_answer": """
SELECT borough, total_revenue
FROM views.revenue_by_borough
WHERE month_partition = '2025-09'
ORDER BY total_revenue DESC;
""".strip(),
        "domain": "revenue_analysis",
        "difficulty": "simple",
    },
    {
        "question": "What is the average tip amount per trip for green taxis?",
        "sql_answer": """
SELECT month_partition, avg_tip
FROM views.service_type_summary
WHERE service_type = 'green'
ORDER BY month_partition;
""".strip(),
        "domain": "revenue_analysis",
        "difficulty": "simple",
    },
    {
        "question": "Which zones have the highest average fare per trip in September?",
        "sql_answer": """
SELECT zone, borough, avg_fare
FROM views.zone_performance
WHERE month_partition = '2025-09'
ORDER BY avg_fare DESC
LIMIT 10;
""".strip(),
        "domain": "revenue_analysis",
        "difficulty": "simple",
    },
    {
        "question": "Which borough has the highest revenue per trip?",
        "sql_answer": """
SELECT borough, month_partition,
       ROUND(avg_revenue_per_trip::numeric, 2) AS avg_revenue_per_trip
FROM views.revenue_by_borough
ORDER BY avg_revenue_per_trip DESC
LIMIT 5;
""".strip(),
        "domain": "revenue_analysis",
        "difficulty": "simple",
    },
    {
        "question": "What is the total congestion surcharge collected by service type?",
        "sql_answer": """
SELECT service_type,
       SUM(total_congestion_surcharge) AS total_congestion
FROM views.service_type_summary
GROUP BY service_type
ORDER BY total_congestion DESC;
""".strip(),
        "domain": "revenue_analysis",
        "difficulty": "medium",
    },
    {
        "question": "Show average fare amount before surcharges for yellow taxi trips in September 2025.",
        "sql_answer": """
SELECT ROUND(AVG(fare_amount)::NUMERIC, 2) AS avg_fare_amount
FROM analytics.fact_taxi_trips_2025_09
WHERE service_type = 'yellow';
""".strip(),
        "domain": "revenue_analysis",
        "difficulty": "medium",
    },
    {
        "question": "Show month over month change in average revenue per trip by borough.",
        "sql_answer": """
SELECT borough,
       MAX(CASE WHEN month_partition = '2025-08' THEN avg_revenue_per_trip END) AS aug_avg,
       MAX(CASE WHEN month_partition = '2025-09' THEN avg_revenue_per_trip END) AS sep_avg
FROM views.revenue_by_borough
GROUP BY borough
ORDER BY borough;
""".strip(),
        "domain": "revenue_analysis",
        "difficulty": "complex",
    },

    # ─── PATTERN: tip percentage calculation ─────────────────────────────────
    # Teaches: tip_amount / NULLIF(total_amount, 0) * 100 pattern
    # Golden tests: tip pct by zone with total_amount filter (harder — adds WHERE + LIMIT)
    {
        "question": "What is the average tip percentage for each service type in September 2025?",
        "sql_answer": """
SELECT service_type,
       ROUND(AVG(tip_amount / NULLIF(total_amount, 0) * 100)::numeric, 2) AS avg_tip_pct
FROM analytics.fact_taxi_trips_2025_09
WHERE total_amount > 0
GROUP BY service_type
ORDER BY avg_tip_pct DESC;
""".strip(),
        "domain": "revenue_analysis",
        "difficulty": "simple",
    },

    # ─── PATTERN: revenue per mile ────────────────────────────────────────────
    # Teaches: SUM(amount) / NULLIF(SUM(distance), 0) pattern
    # Golden tests: revenue per mile by service type AND borough (harder — adds JOIN + borough)
    {
        "question": "What is the revenue per mile for each service type in September 2025?",
        "sql_answer": """
SELECT service_type,
       ROUND(
           (SUM(total_amount) / NULLIF(SUM(trip_distance), 0))::numeric, 2
       ) AS revenue_per_mile
FROM analytics.fact_taxi_trips_2025_09
WHERE trip_distance > 0
GROUP BY service_type
ORDER BY revenue_per_mile DESC;
""".strip(),
        "domain": "revenue_analysis",
        "difficulty": "simple",
    },

    # ─── PATTERN: subquery for overall average comparison ────────────────────
    # Teaches: HAVING with subquery for global metric comparison
    # Golden tests: borough pairs above overall avg distance (harder — adds two JOINs)
    {
        "question": "Which boroughs have above average revenue per trip in September 2025?",
        "sql_answer": """
SELECT z.borough,
       ROUND(AVG(f.total_amount)::numeric, 2) AS avg_revenue
FROM analytics.fact_taxi_trips_2025_09 f
JOIN analytics.taxi_zones z ON f.pulocationid = z.locationid
GROUP BY z.borough
HAVING AVG(f.total_amount) > (
    SELECT AVG(total_amount)
    FROM analytics.fact_taxi_trips_2025_09
)
ORDER BY avg_revenue DESC;
""".strip(),
        "domain": "revenue_analysis",
        "difficulty": "medium",
    },

    # ─── PATTERN: CROSS JOIN for global metric comparison ────────────────────
    # Teaches: CROSS JOIN subquery to bring overall metric into every row
    # Golden tests: congestion surcharge per borough vs overall avg (harder — adds borough JOIN)
    {
        "question": "Show each service type revenue compared to the overall average revenue per trip.",
        "sql_answer": """
SELECT f.service_type,
       ROUND(AVG(f.total_amount)::numeric, 2) AS avg_revenue,
       ROUND(overall.avg_all::numeric, 2) AS overall_avg,
       ROUND((AVG(f.total_amount) - overall.avg_all)::numeric, 2) AS diff
FROM analytics.fact_taxi_trips_2025_09 f
CROSS JOIN (
    SELECT AVG(total_amount) AS avg_all
    FROM analytics.fact_taxi_trips_2025_09
) overall
GROUP BY f.service_type, overall.avg_all
ORDER BY avg_revenue DESC;
""".strip(),
        "domain": "revenue_analysis",
        "difficulty": "medium",
    },

    # ─── PATTERN: FILTER clause for conditional counting ─────────────────────
    # Teaches: COUNT(*) FILTER (WHERE ...) pattern
    # Golden tests: % zero tip trips by borough (harder — adds JOIN + % calculation)
    {
        "question": "How many trips had zero tip and how many had a tip in September 2025?",
        "sql_answer": """
SELECT COUNT(*) FILTER (WHERE tip_amount = 0)  AS zero_tip_trips,
       COUNT(*) FILTER (WHERE tip_amount > 0)  AS tipped_trips,
       COUNT(*)                                AS total_trips
FROM analytics.fact_taxi_trips_2025_09;
""".strip(),
        "domain": "revenue_analysis",
        "difficulty": "simple",
    },

    # ─── PATTERN: raw.fhvhv queries ──────────────────────────────────────────
    # Teaches: fhvhv table structure, driver_pay and base_passenger_fare columns
    # Golden tests: driver pay efficiency ratio (harder — adds ratio calculation)
    {
        "question": "What is the total driver pay for FHVHV trips in September 2025?",
        "sql_answer": """
SELECT hvfhs_license_num,
       ROUND(SUM(driver_pay)::numeric, 2) AS total_driver_pay,
       COUNT(*) AS trip_count
FROM raw.fhvhv_tripdata_2025_09
GROUP BY hvfhs_license_num
ORDER BY total_driver_pay DESC;
""".strip(),
        "domain": "revenue_analysis",
        "difficulty": "simple",
    },

    # ─────────────────────────────────────────────
    # DOMAIN: time_analysis — SIMPLE
    # ─────────────────────────────────────────────
    {
        "question": "What hour of the day has the highest number of trips?",
        "sql_answer": """
SELECT pickup_hour, SUM(total_trips) AS trips
FROM views.trips_by_hour
GROUP BY pickup_hour
ORDER BY trips DESC
LIMIT 1;
""".strip(),
        "domain": "time_analysis",
        "difficulty": "simple",
    },
    {
        "question": "Show average fare by hour of day for yellow taxis in September 2025.",
        "sql_answer": """
SELECT pickup_hour, avg_fare
FROM views.trips_by_hour
WHERE service_type = 'yellow'
  AND month_partition = '2025-09'
ORDER BY pickup_hour;
""".strip(),
        "domain": "time_analysis",
        "difficulty": "simple",
    },
    {
        "question": "Which day of the week has the highest average tip amount?",
        "sql_answer": """
SELECT day_name, ROUND(AVG(avg_tip)::NUMERIC, 2) AS avg_tip
FROM views.trips_by_day_of_week
GROUP BY day_name, pickup_day_of_week
ORDER BY avg_tip DESC
LIMIT 1;
""".strip(),
        "domain": "time_analysis",
        "difficulty": "simple",
    },
    {
        "question": "Which hour has the most trips on average?",
        "sql_answer": """
SELECT pickup_hour, total_trips,
       ROUND(avg_fare::numeric, 2) AS avg_fare
FROM views.trips_by_hour
ORDER BY total_trips DESC
LIMIT 5;
""".strip(),
        "domain": "time_analysis",
        "difficulty": "simple",
    },
    {
        "question": "Show total trips by day of week for green taxis in August 2025.",
        "sql_answer": """
SELECT day_name, total_trips
FROM views.trips_by_day_of_week
WHERE service_type = 'green'
  AND month_partition = '2025-08'
ORDER BY pickup_day_of_week;
""".strip(),
        "domain": "time_analysis",
        "difficulty": "simple",
    },
    {
        "question": "Compare trip volumes between weekdays and weekends across both months.",
        "sql_answer": """
SELECT
    CASE WHEN pickup_day_of_week IN (0, 6) THEN 'Weekend' ELSE 'Weekday' END AS day_type,
    month_partition,
    SUM(total_trips) AS total_trips
FROM views.trips_by_day_of_week
GROUP BY day_type, month_partition
ORDER BY month_partition, day_type;
""".strip(),
        "domain": "time_analysis",
        "difficulty": "medium",
    },
    {
        "question": "What is the average trip distance during peak hours 7 to 9 AM and 5 to 7 PM?",
        "sql_answer": """
SELECT pickup_hour, SUM(total_trips) AS trips,
       AVG(avg_distance) AS avg_distance
FROM views.trips_by_hour
WHERE pickup_hour IN (7, 8, 9, 17, 18, 19)
GROUP BY pickup_hour
ORDER BY pickup_hour;
""".strip(),
        "domain": "time_analysis",
        "difficulty": "medium",
    },

    # ─── PATTERN: LAG window function ────────────────────────────────────────
    # Teaches: LAG() basic previous row comparison
    # Golden tests: week-over-week % change with LAG (harder — adds DATE_TRUNC week + % calc)
    {
        "question": "Show daily trip count with previous day comparison for September 2025.",
        "sql_answer": """
WITH daily AS (
    SELECT pickup_datetime::date AS trip_date,
           COUNT(*) AS total_trips
    FROM analytics.fact_taxi_trips_2025_09
    GROUP BY 1
)
SELECT trip_date,
       total_trips,
       LAG(total_trips) OVER (ORDER BY trip_date) AS prev_day_trips
FROM daily
ORDER BY trip_date;
""".strip(),
        "domain": "time_analysis",
        "difficulty": "medium",
    },

    # ─── PATTERN: RANK() window function ─────────────────────────────────────
    # Teaches: RANK() basic usage
    # Golden tests: RANK() with PARTITION BY borough per hour (harder)
    {
        "question": "Rank pickup zones by total trips in September 2025.",
        "sql_answer": """
SELECT z.zone,
       COUNT(*) AS trip_count,
       RANK() OVER (ORDER BY COUNT(*) DESC) AS zone_rank
FROM analytics.fact_taxi_trips_2025_09 f
JOIN analytics.taxi_zones z ON f.pulocationid = z.locationid
GROUP BY z.zone
LIMIT 20;
""".strip(),
        "domain": "time_analysis",
        "difficulty": "medium",
    },

    # ─── PATTERN: CTE basic structure ────────────────────────────────────────
    # Teaches: WITH clause, daily aggregation as a CTE
    # Golden tests: multi-CTE cross-month rank comparison, cumulative revenue (harder)
    {
        "question": "What is the daily revenue for September 2025?",
        "sql_answer": """
WITH daily AS (
    SELECT pickup_datetime::date AS trip_date,
           SUM(total_amount) AS daily_revenue
    FROM analytics.fact_taxi_trips_2025_09
    GROUP BY 1
)
SELECT trip_date,
       ROUND(daily_revenue::numeric, 2) AS daily_revenue
FROM daily
ORDER BY trip_date;
""".strip(),
        "domain": "time_analysis",
        "difficulty": "simple",
    },

    # ─── PATTERN: rolling window (ROWS BETWEEN) ──────────────────────────────
    # Teaches: ROWS BETWEEN syntax for rolling calculations
    # Golden tests: 7-day rolling avg revenue across both months (harder — uses views + revenue)
    {
        "question": "What is the 3-day rolling average of daily trips in September 2025?",
        "sql_answer": """
WITH daily AS (
    SELECT pickup_datetime::date AS trip_date,
           COUNT(*) AS daily_trips
    FROM analytics.fact_taxi_trips_2025_09
    GROUP BY 1
)
SELECT trip_date,
       daily_trips,
       AVG(daily_trips) OVER (
           ORDER BY trip_date
           ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
       ) AS rolling_3day_avg
FROM daily
ORDER BY trip_date;
""".strip(),
        "domain": "time_analysis",
        "difficulty": "medium",
    },

    # ─── PATTERN: cumulative SUM window ──────────────────────────────────────
    # Teaches: SUM() OVER (ORDER BY ...) running total on trips
    # Golden tests: cumulative revenue by day Sep 2025 (harder — uses revenue not trips)
    {
        "question": "Show cumulative trip count by day in September 2025.",
        "sql_answer": """
WITH daily AS (
    SELECT pickup_datetime::date AS trip_date,
           COUNT(*) AS daily_trips
    FROM analytics.fact_taxi_trips_2025_09
    GROUP BY 1
)
SELECT trip_date,
       daily_trips,
       SUM(daily_trips) OVER (ORDER BY trip_date) AS cumulative_trips
FROM daily
ORDER BY trip_date;
""".strip(),
        "domain": "time_analysis",
        "difficulty": "medium",
    },

    # ─────────────────────────────────────────────
    # DOMAIN: general
    # ─────────────────────────────────────────────
    {
        "question": "How many total trips are there across all service types and both months?",
        "sql_answer": """
SELECT COUNT(*) AS total_trips
FROM views.fact_taxi_trips_all;
""".strip(),
        "domain": "general",
        "difficulty": "simple",
    },
    {
        "question": "Show a summary of total trips and total revenue by service type for all months.",
        "sql_answer": """
SELECT service_type,
       SUM(total_trips)   AS total_trips,
       SUM(total_revenue) AS total_revenue
FROM views.service_type_summary
GROUP BY service_type
ORDER BY total_revenue DESC;
""".strip(),
        "domain": "general",
        "difficulty": "simple",
    },
]