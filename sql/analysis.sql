-- Analysis queries for the indoor/outdoor IAQ readings table.
-- Each query is named with a "-- name:" marker so iaq/store.py can run them.

-- name: co2_band_share
-- Share of readings in each indoor CO2 band.
SELECT
    CASE
        WHEN in_co2_ppm < 800 THEN 'good (<800 ppm)'
        WHEN in_co2_ppm < 1200 THEN 'moderate (800-1200 ppm)'
        ELSE 'poor (>1200 ppm)'
    END AS co2_band,
    COUNT(*) AS readings,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM readings WHERE in_co2_ppm IS NOT NULL), 1) AS share_pct
FROM readings
WHERE in_co2_ppm IS NOT NULL
GROUP BY co2_band
ORDER BY MIN(in_co2_ppm);

-- name: hourly_profile
-- Average indoor and outdoor conditions by hour of day.
SELECT
    CAST(strftime('%H', timestamp) AS INTEGER) AS hour,
    ROUND(AVG(in_co2_ppm), 0) AS in_co2_ppm,
    ROUND(AVG(out_co2_ppm), 0) AS out_co2_ppm,
    ROUND(AVG(in_temp_c), 1) AS in_temp_c,
    ROUND(AVG(out_temp_c), 1) AS out_temp_c
FROM readings
GROUP BY hour
ORDER BY hour;

-- name: worst_days
-- Days with the highest peak indoor CO2.
SELECT
    date(timestamp) AS day,
    MAX(in_co2_ppm) AS peak_in_co2_ppm,
    ROUND(AVG(in_co2_ppm), 0) AS mean_in_co2_ppm,
    ROUND(MAX(in_temp_c), 1) AS peak_in_temp_c
FROM readings
GROUP BY day
ORDER BY peak_in_co2_ppm DESC
LIMIT 10;

-- name: indoor_outdoor_gap
-- How much warmer and more CO2-laden the room is than outside, by hour.
SELECT
    CAST(strftime('%H', timestamp) AS INTEGER) AS hour,
    ROUND(AVG(in_temp_c - out_temp_c), 2) AS temp_gap_c,
    ROUND(AVG(in_co2_ppm - out_co2_ppm), 0) AS co2_excess_ppm
FROM readings
GROUP BY hour
ORDER BY hour;
