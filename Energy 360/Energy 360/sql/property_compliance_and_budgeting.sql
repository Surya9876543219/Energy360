-- ENERGY 360 | PROPERTY ENERGY COMPLIANCE + BUDGETS + SAVINGS
-- Target catalog/schema: energy.energy
-- Additive DDL only. No legal thresholds or sample compliance obligations are seeded.
-- Populate standards and obligations only from verified authority publications.
-- Existing property energy actuals continue to come from fact_property_energy_usage.

CREATE SCHEMA IF NOT EXISTS energy.energy;
USE CATALOG energy;
USE SCHEMA energy;

-- 1. Verified municipal, state, regional or national benchmarking standards.
CREATE TABLE IF NOT EXISTS dim_compliance_standard (
    standard_id STRING NOT NULL,
    standard_code STRING,
    standard_name STRING NOT NULL,
    jurisdiction_level STRING NOT NULL, -- Municipal, County, State, Regional, Federal
    jurisdiction_name STRING NOT NULL,
    program_type STRING,                 -- Benchmarking, Building Performance Standard, Disclosure
    metric_name STRING NOT NULL,         -- Site Energy Use, Source EUI, Water Use, GHG Emissions
    metric_unit STRING,
    threshold_operator STRING,           -- <=, >=, <, >, =, DISCLOSE
    threshold_value DECIMAL(20,6),
    effective_start_date DATE,
    effective_end_date DATE,
    reporting_frequency STRING,
    source_authority STRING,
    source_url STRING,
    is_active BOOLEAN,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
) USING DELTA;

-- 2. Which verified standards apply to each property.
CREATE TABLE IF NOT EXISTS bridge_property_compliance_obligation (
    obligation_id STRING NOT NULL,
    property_id STRING NOT NULL,
    standard_id STRING NOT NULL,
    reporting_frequency STRING,
    reporting_start_date DATE,
    reporting_end_date DATE,
    compliance_status STRING,            -- Not Started, In Progress, Compliant, Non-Compliant, Exempt
    responsible_owner STRING,
    next_submission_due_date DATE,
    exemption_reason STRING,
    notes STRING,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
) USING DELTA;

-- 3. Period-level benchmarking results / disclosure submissions.
-- Store source metrics and calculated intensities separately for auditability.
CREATE TABLE IF NOT EXISTS fact_property_compliance_report (
    report_id STRING NOT NULL,
    obligation_id STRING NOT NULL,
    property_id STRING NOT NULL,
    reporting_period_start DATE NOT NULL,
    reporting_period_end DATE NOT NULL,
    energy_use_value DECIMAL(20,6),
    energy_use_unit STRING,
    water_use_value DECIMAL(20,6),
    water_use_unit STRING,
    emissions_tco2e DECIMAL(20,6),
    energy_use_intensity DECIMAL(20,8),
    energy_intensity_unit STRING,
    water_use_intensity DECIMAL(20,8),
    water_intensity_unit STRING,
    report_status STRING,                -- Draft, In Review, Submitted, Accepted, Rejected
    submission_date DATE,
    submission_reference STRING,
    prepared_by STRING,
    notes STRING,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
) USING DELTA;

-- 4. Property energy budgets. Actuals are calculated from fact_property_energy_usage.
CREATE TABLE IF NOT EXISTS fact_property_energy_budget (
    budget_id STRING NOT NULL,
    property_id STRING NOT NULL,
    budget_name STRING NOT NULL,
    fiscal_year INT NOT NULL,
    commodity_id STRING,
    period_start_date DATE NOT NULL,
    period_end_date DATE NOT NULL,
    budget_amount DECIMAL(20,2) NOT NULL,
    currency_code STRING NOT NULL,
    approval_status STRING,               -- Draft, Submitted, Approved, Rejected
    approved_by STRING,
    notes STRING,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
) USING DELTA;

-- 5. Savings initiatives and measurement/verification outcomes.
CREATE TABLE IF NOT EXISTS fact_property_savings_initiative (
    initiative_id STRING NOT NULL,
    property_id STRING NOT NULL,
    initiative_name STRING NOT NULL,
    initiative_category STRING,           -- Lighting, HVAC, Controls, Water, Renewables, Operations
    target_savings_amount DECIMAL(20,2),
    realized_savings_amount DECIMAL(20,2),
    currency_code STRING,
    target_energy_savings DECIMAL(20,6),
    realized_energy_savings DECIMAL(20,6),
    energy_unit STRING,
    initiative_status STRING,             -- Planned, In Progress, Completed, On Hold
    start_date DATE,
    target_completion_date DATE,
    measurement_method STRING,
    measurement_period_start DATE,
    measurement_period_end DATE,
    notes STRING,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
) USING DELTA;

-- Validate property IDs before inserting obligations, reports, budgets or initiatives.
-- Example standard insert template (replace with a verified local authority requirement):
-- INSERT INTO dim_compliance_standard
-- (standard_id, standard_code, standard_name, jurisdiction_level, jurisdiction_name,
--  program_type, metric_name, metric_unit, threshold_operator, threshold_value,
--  effective_start_date, effective_end_date, reporting_frequency, source_authority,
--  source_url, is_active, created_at, updated_at)
-- VALUES
-- ('STD-VERIFIED-001', 'AUTHORITY-CODE', 'Verified standard name', 'Municipal',
--  'City / Jurisdiction', 'Benchmarking', 'Site Energy Use', 'kBtu/sq.ft.',
--  'DISCLOSE', NULL, DATE'2026-01-01', NULL, 'Annual', 'Authority name',
--  'https://official-authority.example', TRUE, current_timestamp(), current_timestamp());

-- Example property obligation template:
-- INSERT INTO bridge_property_compliance_obligation
-- (obligation_id, property_id, standard_id, reporting_frequency, reporting_start_date,
--  reporting_end_date, compliance_status, responsible_owner, next_submission_due_date,
--  notes, created_at, updated_at)
-- VALUES ('OBL-001', 'EXISTING-PROPERTY-ID', 'STD-VERIFIED-001', 'Annual',
--  DATE'2026-01-01', DATE'2026-12-31', 'Not Started', 'Facilities Manager',
--  DATE'2027-05-01', 'Confirm deadline with authority', current_timestamp(), current_timestamp());


-- SYNTHETIC DEMONSTRATION RECORDS FOR ALL FIVE PROPERTIES.
-- These are planning examples, not approved financial budgets or legal compliance claims.
-- IDs and MERGE keys are deterministic so this block is safe to rerun.
MERGE INTO fact_property_energy_budget t
USING (
  SELECT * FROM VALUES
    ('BUD-HOU-2026','PROP-HOU-001','2026 Energy Budget - Houston Office Center',2026,NULL,DATE'2026-01-01',DATE'2026-11-30',185000.00,'USD','Approved'),
    ('BUD-DAL-2026','PROP-DAL-001','2026 Energy Budget - Dallas Distribution Campus',2026,NULL,DATE'2026-01-01',DATE'2026-11-30',310000.00,'USD','Approved'),
    ('BUD-PHX-2026','PROP-PHX-001','2026 Energy Budget - Phoenix Retail Plaza',2026,NULL,DATE'2026-01-01',DATE'2026-11-30',168000.00,'USD','Approved'),
    ('BUD-CHI-2026','PROP-CHI-001','2026 Energy Budget - Chicago Residential Tower',2026,NULL,DATE'2026-01-01',DATE'2026-11-30',225000.00,'USD','Approved'),
    ('BUD-NYC-2026','PROP-NYC-001','2026 Energy Budget - New York Business Center',2026,NULL,DATE'2026-01-01',DATE'2026-11-30',142000.00,'USD','Approved')
  AS s(budget_id,property_id,budget_name,fiscal_year,commodity_id,period_start_date,period_end_date,budget_amount,currency_code,approval_status)
) s ON t.budget_id=s.budget_id
WHEN MATCHED THEN UPDATE SET
 t.budget_name=s.budget_name,t.fiscal_year=s.fiscal_year,t.commodity_id=s.commodity_id,
 t.period_start_date=s.period_start_date,t.period_end_date=s.period_end_date,
 t.budget_amount=s.budget_amount,t.currency_code=s.currency_code,
 t.approval_status=s.approval_status,
 t.notes='Synthetic demonstration budget for dashboard validation; not a real finance approval.',
 t.updated_at=current_timestamp()
WHEN NOT MATCHED THEN INSERT
 (budget_id,property_id,budget_name,fiscal_year,commodity_id,period_start_date,period_end_date,budget_amount,currency_code,approval_status,notes,created_at,updated_at)
VALUES
 (s.budget_id,s.property_id,s.budget_name,s.fiscal_year,s.commodity_id,s.period_start_date,s.period_end_date,s.budget_amount,s.currency_code,s.approval_status,
  'Synthetic demonstration budget for dashboard validation; not a real finance approval.',current_timestamp(),current_timestamp());

MERGE INTO fact_property_savings_initiative t
USING (
  SELECT * FROM VALUES
    ('SAV-HOU-LIGHT','PROP-HOU-001','LED Lighting Retrofit','Lighting',12000.00,2500.00,'USD','In Progress','2026-02-01',DATE'2026-12-15'),
    ('SAV-HOU-HVAC','PROP-HOU-001','HVAC Optimization','HVAC',18000.00,4000.00,'USD','In Progress','2026-03-01',DATE'2026-12-31'),
    ('SAV-DAL-LIGHT','PROP-DAL-001','Warehouse LED Upgrade','Lighting',22000.00,6000.00,'USD','In Progress','2026-01-15',DATE'2026-11-30'),
    ('SAV-DAL-CONTROL','PROP-DAL-001','Building Controls Optimization','Controls',16000.00,3500.00,'USD','In Progress','2026-03-01',DATE'2026-12-31'),
    ('SAV-PHX-SOLAR','PROP-PHX-001','Rooftop Solar Optimization','Renewables',15000.00,4200.00,'USD','In Progress','2026-01-01',DATE'2026-12-31'),
    ('SAV-PHX-WATER','PROP-PHX-001','Water Fixture Efficiency','Water',5000.00,1800.00,'USD','In Progress','2026-02-01',DATE'2026-10-31'),
    ('SAV-CHI-LIGHT','PROP-CHI-001','Common Area LED Upgrade','Lighting',14000.00,3200.00,'USD','In Progress','2026-02-01',DATE'2026-12-15'),
    ('SAV-CHI-HVAC','PROP-CHI-001','Heating Controls Tuning','HVAC',19000.00,5100.00,'USD','In Progress','2026-01-15',DATE'2026-12-31'),
    ('SAV-NYC-LIGHT','PROP-NYC-001','Office Lighting Controls','Controls',11000.00,2900.00,'USD','In Progress','2026-02-01',DATE'2026-11-30'),
    ('SAV-NYC-HVAC','PROP-NYC-001','Chiller Plant Optimization','HVAC',24000.00,5300.00,'USD','In Progress','2026-03-01',DATE'2026-12-31')
  AS s(initiative_id,property_id,initiative_name,initiative_category,target_savings_amount,realized_savings_amount,currency_code,initiative_status,start_date,target_completion_date)
) s ON t.initiative_id=s.initiative_id
WHEN MATCHED THEN UPDATE SET
 t.initiative_name=s.initiative_name,t.initiative_category=s.initiative_category,
 t.target_savings_amount=s.target_savings_amount,t.realized_savings_amount=s.realized_savings_amount,
 t.currency_code=s.currency_code,t.initiative_status=s.initiative_status,
 t.start_date=s.start_date,t.target_completion_date=s.target_completion_date,
 t.notes='Synthetic demonstration initiative; replace estimates with measured and verified results.',
 t.updated_at=current_timestamp()
WHEN NOT MATCHED THEN INSERT
 (initiative_id,property_id,initiative_name,initiative_category,target_savings_amount,realized_savings_amount,currency_code,initiative_status,start_date,target_completion_date,notes,created_at,updated_at)
VALUES
 (s.initiative_id,s.property_id,s.initiative_name,s.initiative_category,s.target_savings_amount,s.realized_savings_amount,s.currency_code,s.initiative_status,s.start_date,s.target_completion_date,
  'Synthetic demonstration initiative; replace estimates with measured and verified results.',current_timestamp(),current_timestamp());

-- Post-deployment checks
SELECT 'dim_compliance_standard' AS table_name, COUNT(*) AS row_count FROM dim_compliance_standard
UNION ALL SELECT 'bridge_property_compliance_obligation', COUNT(*) FROM bridge_property_compliance_obligation
UNION ALL SELECT 'fact_property_compliance_report', COUNT(*) FROM fact_property_compliance_report
UNION ALL SELECT 'fact_property_energy_budget', COUNT(*) FROM fact_property_energy_budget
UNION ALL SELECT 'fact_property_savings_initiative', COUNT(*) FROM fact_property_savings_initiative;

-- Validate that configured property obligations point to existing properties and standards.
SELECT o.obligation_id, o.property_id, o.standard_id
FROM bridge_property_compliance_obligation o
LEFT JOIN dim_property p ON p.property_id = o.property_id
LEFT JOIN dim_compliance_standard s ON s.standard_id = o.standard_id
WHERE p.property_id IS NULL OR s.standard_id IS NULL;
