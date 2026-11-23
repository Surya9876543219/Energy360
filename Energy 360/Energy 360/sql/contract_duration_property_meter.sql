-- ENERGY 360 | PROPERTY- AND METER-LEVEL CONTRACT DURATION
-- Target catalog/schema: energy.energy
-- Additive and repeatable: creates a bridge table and MERGEs missing meter links.
-- Existing property contracts and source data are not deleted or overwritten.

CREATE SCHEMA IF NOT EXISTS energy.energy;
USE CATALOG energy;
USE SCHEMA energy;

-- A meter can be covered by a commodity-specific supplier contract.
-- Effective dates preserve meter-level coverage independently from property coverage.
CREATE TABLE IF NOT EXISTS bridge_meter_contract (
    meter_contract_id STRING NOT NULL,
    property_id STRING NOT NULL,
    meter_id STRING NOT NULL,
    contract_id STRING NOT NULL,
    effective_start_date DATE,
    effective_end_date DATE,
    allocation_pct DECIMAL(9,4),
    created_at TIMESTAMP
) USING DELTA;

-- Seed meter-contract relationships from the existing property contract coverage.
-- Match by property and commodity so electricity meters receive electricity
-- contracts, gas meters receive gas contracts, and water meters receive water contracts.
MERGE INTO bridge_meter_contract AS target
USING (
    SELECT
        concat('MC-', m.meter_id, '-', c.contract_id) AS meter_contract_id,
        m.property_id,
        m.meter_id,
        c.contract_id,
        coalesce(b.effective_start_date, c.contract_start_date) AS effective_start_date,
        coalesce(b.effective_end_date, c.contract_end_date) AS effective_end_date,
        coalesce(b.allocation_pct, 100.0000) AS allocation_pct
    FROM dim_meter m
    INNER JOIN bridge_property_contract b
        ON b.property_id = m.property_id
    INNER JOIN dim_contract c
        ON c.contract_id = b.contract_id
       AND c.commodity_id = m.commodity_id
) AS source
ON target.meter_contract_id = source.meter_contract_id
WHEN NOT MATCHED THEN INSERT (
    meter_contract_id, property_id, meter_id, contract_id,
    effective_start_date, effective_end_date, allocation_pct, created_at
)
VALUES (
    source.meter_contract_id, source.property_id, source.meter_id, source.contract_id,
    source.effective_start_date, source.effective_end_date, source.allocation_pct,
    current_timestamp()
);

-- Validation: all rows should have a valid property, meter and contract.
SELECT
    COUNT(*) AS meter_contract_links,
    SUM(CASE WHEN p.property_id IS NULL THEN 1 ELSE 0 END) AS missing_property,
    SUM(CASE WHEN m.meter_id IS NULL THEN 1 ELSE 0 END) AS missing_meter,
    SUM(CASE WHEN c.contract_id IS NULL THEN 1 ELSE 0 END) AS missing_contract
FROM bridge_meter_contract b
LEFT JOIN dim_property p ON b.property_id = p.property_id
LEFT JOIN dim_meter m ON b.meter_id = m.meter_id
LEFT JOIN dim_contract c ON b.contract_id = c.contract_id;

-- Preview contract term, remaining days and lifecycle status by property and meter.
SELECT
    p.property_name,
    m.meter_number,
    co.commodity_name,
    c.contract_number,
    v.vendor_name AS supplier_name,
    b.effective_start_date AS contract_start_date,
    b.effective_end_date AS contract_end_date,
    datediff(b.effective_end_date, b.effective_start_date) + 1 AS contract_duration_days,
    datediff(b.effective_end_date, current_date()) AS days_remaining,
    CASE
        WHEN b.effective_start_date > current_date() THEN 'Upcoming'
        WHEN b.effective_end_date < current_date() THEN 'Expired'
        WHEN datediff(b.effective_end_date, current_date()) <= 90 THEN 'Expiring Soon'
        ELSE 'Active'
    END AS duration_status,
    c.auto_renewal_flag
FROM bridge_meter_contract b
JOIN dim_property p ON b.property_id = p.property_id
JOIN dim_meter m ON b.meter_id = m.meter_id
JOIN dim_contract c ON b.contract_id = c.contract_id
LEFT JOIN dim_commodity co ON m.commodity_id = co.commodity_id
LEFT JOIN dim_vendor v ON c.supplier_vendor_id = v.vendor_id
ORDER BY p.property_name, m.meter_number, b.effective_end_date;
