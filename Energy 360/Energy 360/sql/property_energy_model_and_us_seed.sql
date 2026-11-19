-- ENERGY 360 | PROPERTY-CENTRIC ENERGY MODEL + SYNTHETIC US TEST DATA
-- Target catalog/schema: energy.energy
-- Run in a DEVELOPMENT/TEST schema first. All sample entities, account IDs,
-- meter IDs, rates, contracts, bills and purchase orders are fictional.
-- Additive + repeatable: CREATE TABLE IF NOT EXISTS and MERGE; no deletes.
-- Delta does not enforce foreign keys: validate logical ID relationships in ETL.

CREATE SCHEMA IF NOT EXISTS energy.energy;
USE CATALOG energy;
USE SCHEMA energy;

-- 01 PROPERTY MASTER
CREATE TABLE IF NOT EXISTS dim_property (
 property_id STRING NOT NULL, property_code STRING, property_name STRING NOT NULL,
 parent_property_id STRING, property_type STRING, ownership_type STRING,
 address_line_1 STRING, address_line_2 STRING, city STRING, county STRING,
 state_code STRING, state_name STRING, postal_code STRING, country_code STRING,
 country_name STRING, timezone STRING, latitude DOUBLE, longitude DOUBLE,
 gross_area_sqft DECIMAL(18,2), rentable_area_sqft DECIMAL(18,2), year_built INT,
 operating_status STRING, acquisition_date DATE, disposition_date DATE,
 property_manager STRING, created_at TIMESTAMP, updated_at TIMESTAMP
) USING DELTA;

-- 02 COMMODITY MASTER
CREATE TABLE IF NOT EXISTS dim_commodity (
 commodity_id STRING NOT NULL, commodity_code STRING, commodity_name STRING NOT NULL,
 commodity_category STRING, base_unit STRING, reporting_unit STRING,
 energy_conversion_kbtu DOUBLE, emissions_factor_kg_co2e_per_unit DOUBLE,
 is_energy_commodity BOOLEAN, is_active BOOLEAN, created_at TIMESTAMP
) USING DELTA;

-- 03 VENDOR / UTILITY / SUPPLIER MASTER
CREATE TABLE IF NOT EXISTS dim_vendor (
 vendor_id STRING NOT NULL, vendor_code STRING, vendor_name STRING NOT NULL,
 vendor_type STRING, parent_vendor_id STRING, tax_identifier STRING,
 remit_to_name STRING, remit_address STRING, remit_city STRING, remit_state STRING,
 remit_postal_code STRING, remit_country_code STRING, contact_name STRING,
 contact_email STRING, contact_phone STRING, website STRING, payment_terms STRING,
 vendor_status STRING, diversity_category STRING, created_at TIMESTAMP, updated_at TIMESTAMP
) USING DELTA;

-- 04 RATE CODE / RATE CLASS MASTER
CREATE TABLE IF NOT EXISTS dim_rate_class (
 rate_class_id STRING NOT NULL, rate_class_code STRING NOT NULL, rate_class_name STRING NOT NULL,
 utility_vendor_id STRING, commodity_id STRING, customer_segment STRING, voltage_level STRING,
 demand_threshold_kw DOUBLE, description STRING, effective_start_date DATE,
 effective_end_date DATE, is_active BOOLEAN, created_at TIMESTAMP
) USING DELTA;

-- 05 PROPERTY-COMMODITY SERVICE BRIDGE
CREATE TABLE IF NOT EXISTS bridge_property_commodity_service (
 property_service_id STRING NOT NULL, property_id STRING NOT NULL, commodity_id STRING NOT NULL,
 service_location_code STRING, service_address STRING, utility_vendor_id STRING,
 service_start_date DATE, service_end_date DATE, service_status STRING,
 is_common_area BOOLEAN, notes STRING, created_at TIMESTAMP
) USING DELTA;

-- 06 UTILITY ACCOUNTS
CREATE TABLE IF NOT EXISTS dim_utility_account (
 utility_account_id STRING NOT NULL, account_number STRING NOT NULL, account_name STRING,
 property_id STRING NOT NULL, property_service_id STRING, commodity_id STRING NOT NULL,
 utility_vendor_id STRING NOT NULL, billing_address STRING, billing_city STRING,
 billing_state STRING, billing_postal_code STRING, billing_country_code STRING,
 rate_class_id STRING, payment_method STRING, payment_terms STRING,
 account_open_date DATE, account_close_date DATE, account_status STRING,
 tax_exempt_flag BOOLEAN, cost_center STRING, general_ledger_account STRING,
 currency_code STRING, created_at TIMESTAMP, updated_at TIMESTAMP
) USING DELTA;

-- 07 METERS / SUBMETERS
CREATE TABLE IF NOT EXISTS dim_meter (
 meter_id STRING NOT NULL, meter_number STRING NOT NULL, meter_name STRING,
 property_id STRING NOT NULL, property_service_id STRING, utility_account_id STRING,
 commodity_id STRING NOT NULL, meter_type STRING, meter_role STRING, unit_of_measure STRING,
 multiplier DOUBLE, meter_manufacturer STRING, meter_model STRING, meter_serial_number STRING,
 installation_date DATE, removal_date DATE, last_calibration_date DATE,
 next_calibration_date DATE, interval_minutes INT, is_smart_meter BOOLEAN,
 meter_status STRING, parent_meter_id STRING, tenant_space STRING, floor_or_area STRING,
 created_at TIMESTAMP, updated_at TIMESTAMP
) USING DELTA;

-- 08 EFFECTIVE-DATED RATE SCHEDULES
CREATE TABLE IF NOT EXISTS dim_rate_schedule (
 rate_schedule_id STRING NOT NULL, rate_code STRING NOT NULL, rate_name STRING,
 rate_class_id STRING NOT NULL, utility_vendor_id STRING NOT NULL, commodity_id STRING NOT NULL,
 contract_id STRING, rate_basis STRING, currency_code STRING, effective_start_date DATE,
 effective_end_date DATE, billing_cycle STRING, demand_charge_applicable BOOLEAN,
 tax_applicable BOOLEAN, rate_status STRING, source_reference STRING, created_at TIMESTAMP
) USING DELTA;

-- 09 INDIVIDUAL RATE COMPONENTS
CREATE TABLE IF NOT EXISTS fact_rate_component (
 rate_component_id STRING NOT NULL, rate_schedule_id STRING NOT NULL,
 component_code STRING, component_name STRING, charge_type STRING,
 calculation_basis STRING, unit_rate DECIMAL(18,8), unit_of_measure STRING,
 currency_code STRING, effective_start_date DATE, effective_end_date DATE,
 tier_number INT, tier_lower_bound DECIMAL(18,4), tier_upper_bound DECIMAL(18,4),
 created_at TIMESTAMP
) USING DELTA;

-- 10 SUPPLIER CONTRACTS
CREATE TABLE IF NOT EXISTS dim_contract (
 contract_id STRING NOT NULL, contract_number STRING NOT NULL, contract_name STRING,
 supplier_vendor_id STRING NOT NULL, broker_vendor_id STRING, contract_type STRING,
 commodity_id STRING, rate_class_id STRING, rate_schedule_id STRING,
 contract_start_date DATE, contract_end_date DATE, auto_renewal_flag BOOLEAN,
 renewal_notice_days INT, termination_notice_days INT, pricing_type STRING,
 currency_code STRING, estimated_annual_volume DECIMAL(20,4), volume_unit STRING,
 estimated_annual_value DECIMAL(20,2), payment_terms STRING, contract_status STRING,
 signed_date DATE, document_uri STRING, notes STRING, created_at TIMESTAMP, updated_at TIMESTAMP
) USING DELTA;

-- 11 MANY-TO-MANY PROPERTY / CONTRACT COVERAGE
CREATE TABLE IF NOT EXISTS bridge_property_contract (
 property_contract_id STRING NOT NULL, property_id STRING NOT NULL, contract_id STRING NOT NULL,
 property_service_id STRING, allocation_pct DECIMAL(9,4),
 effective_start_date DATE, effective_end_date DATE, created_at TIMESTAMP
) USING DELTA;

-- 12 RAW / INTERVAL METER READINGS
CREATE TABLE IF NOT EXISTS fact_meter_reading (
 meter_reading_id STRING NOT NULL, property_id STRING NOT NULL, meter_id STRING NOT NULL,
 utility_account_id STRING, commodity_id STRING NOT NULL, reading_start_ts TIMESTAMP,
 reading_end_ts TIMESTAMP, reading_date DATE, reading_type STRING, reading_source STRING,
 previous_reading DECIMAL(20,6), current_reading DECIMAL(20,6),
 consumption_quantity DECIMAL(20,6), unit_of_measure STRING, multiplier DOUBLE,
 demand_quantity DECIMAL(20,6), demand_unit STRING, data_quality_status STRING,
 ingestion_timestamp TIMESTAMP, source_record_id STRING
) USING DELTA;

-- 13 PROPERTY ENERGY USAGE (PRIMARY PROPERTY-LEVEL ANALYTICS FACT)
CREATE TABLE IF NOT EXISTS fact_property_energy_usage (
 property_energy_usage_id STRING NOT NULL, property_id STRING NOT NULL, meter_id STRING,
 utility_account_id STRING, commodity_id STRING NOT NULL, vendor_id STRING,
 contract_id STRING, rate_schedule_id STRING, period_start_date DATE NOT NULL,
 period_end_date DATE NOT NULL, usage_quantity DECIMAL(20,6), usage_unit STRING,
 peak_demand_quantity DECIMAL(20,6), peak_demand_unit STRING, power_factor DECIMAL(9,6),
 load_factor_pct DECIMAL(9,4), cost_amount DECIMAL(20,2), currency_code STRING,
 emissions_kg_co2e DECIMAL(20,6), is_estimated BOOLEAN, source_system STRING,
 source_record_id STRING, created_at TIMESTAMP
) USING DELTA;

-- 14 UTILITY BILL HEADER
CREATE TABLE IF NOT EXISTS fact_energy_bill (
 energy_bill_id STRING NOT NULL, bill_number STRING, property_id STRING NOT NULL,
 utility_account_id STRING NOT NULL, vendor_id STRING NOT NULL, contract_id STRING,
 bill_period_start DATE, bill_period_end DATE, invoice_date DATE, due_date DATE,
 total_usage_quantity DECIMAL(20,6), usage_unit STRING, subtotal_amount DECIMAL(20,2),
 tax_amount DECIMAL(20,2), total_amount DECIMAL(20,2), currency_code STRING,
 amount_paid DECIMAL(20,2), balance_amount DECIMAL(20,2), payment_status STRING,
 bill_status STRING, source_document_uri STRING, created_at TIMESTAMP
) USING DELTA;

-- 15 UTILITY BILL LINE ITEMS
CREATE TABLE IF NOT EXISTS fact_energy_bill_line (
 energy_bill_line_id STRING NOT NULL, energy_bill_id STRING NOT NULL,
 property_id STRING NOT NULL, meter_id STRING, commodity_id STRING,
 rate_schedule_id STRING, rate_component_id STRING, charge_code STRING,
 charge_description STRING, charge_type STRING, quantity DECIMAL(20,6),
 unit_of_measure STRING, unit_rate DECIMAL(20,8), line_amount DECIMAL(20,2),
 currency_code STRING, created_at TIMESTAMP
) USING DELTA;

-- 16 PURCHASE ORDER HEADER
CREATE TABLE IF NOT EXISTS fact_purchase_order (
 purchase_order_id STRING NOT NULL, purchase_order_number STRING NOT NULL,
 property_id STRING, vendor_id STRING NOT NULL, contract_id STRING, order_date DATE,
 requested_delivery_date DATE, approved_date DATE, currency_code STRING,
 subtotal_amount DECIMAL(20,2), tax_amount DECIMAL(20,2), total_amount DECIMAL(20,2),
 buyer_name STRING, department STRING, cost_center STRING, approval_status STRING,
 purchase_order_status STRING, description STRING, created_at TIMESTAMP
) USING DELTA;

-- 17 PURCHASE ORDER LINES
CREATE TABLE IF NOT EXISTS fact_purchase_order_line (
 purchase_order_line_id STRING NOT NULL, purchase_order_id STRING NOT NULL,
 property_id STRING, commodity_id STRING, meter_id STRING, item_code STRING,
 item_description STRING, procurement_category STRING, quantity DECIMAL(20,4),
 unit_of_measure STRING, unit_price DECIMAL(20,4), line_amount DECIMAL(20,2),
 currency_code STRING, requested_start_date DATE, requested_end_date DATE, created_at TIMESTAMP
) USING DELTA;

-- 18 VENDOR INVOICE HEADER
CREATE TABLE IF NOT EXISTS fact_vendor_invoice (
 vendor_invoice_id STRING NOT NULL, vendor_invoice_number STRING NOT NULL,
 vendor_id STRING NOT NULL, property_id STRING, contract_id STRING, purchase_order_id STRING,
 invoice_date DATE, due_date DATE, subtotal_amount DECIMAL(20,2), tax_amount DECIMAL(20,2),
 total_amount DECIMAL(20,2), currency_code STRING, invoice_status STRING,
 approval_status STRING, document_uri STRING, created_at TIMESTAMP
) USING DELTA;

-- 19 VENDOR INVOICE LINES
CREATE TABLE IF NOT EXISTS fact_vendor_invoice_line (
 vendor_invoice_line_id STRING NOT NULL, vendor_invoice_id STRING NOT NULL,
 purchase_order_line_id STRING, property_id STRING, commodity_id STRING,
 description STRING, quantity DECIMAL(20,4), unit_of_measure STRING,
 unit_price DECIMAL(20,4), line_amount DECIMAL(20,2), currency_code STRING, created_at TIMESTAMP
) USING DELTA;

-- 20 VENDOR PAYMENTS
CREATE TABLE IF NOT EXISTS fact_vendor_payment (
 vendor_payment_id STRING NOT NULL, vendor_invoice_id STRING NOT NULL,
 vendor_id STRING NOT NULL, property_id STRING, payment_date DATE,
 payment_reference STRING, payment_method STRING, payment_amount DECIMAL(20,2),
 currency_code STRING, payment_status STRING, created_at TIMESTAMP
) USING DELTA;

-- SYNTHETIC US MASTER DATA (fictional test records only)
MERGE INTO dim_commodity t
USING (SELECT * FROM VALUES
 ('COM-ELEC','ELEC','Electricity','Energy','kWh','MWh',3.412,0.386,TRUE,TRUE),
 ('COM-GAS','GAS','Natural Gas','Fuel','therm','MMBtu',100.0,5.30,TRUE,TRUE),
 ('COM-WATER','WATER','Water','Water','CCF','CCF',NULL,NULL,FALSE,TRUE),
 ('COM-STEAM','STEAM','Steam','Thermal','klb','klb',NULL,NULL,TRUE,TRUE),
 ('COM-CHW','CHW','Chilled Water','Thermal','ton-hour','ton-hour',NULL,NULL,TRUE,TRUE),
 ('COM-SOLAR','SOLAR','Solar','Energy','kWh','MWh',3.412,0.040,TRUE,TRUE)
 AS s(commodity_id,commodity_code,commodity_name,commodity_category,base_unit,reporting_unit,
 energy_conversion_kbtu,emissions_factor_kg_co2e_per_unit,is_energy_commodity,is_active)
) s ON t.commodity_id=s.commodity_id
WHEN NOT MATCHED THEN INSERT (commodity_id,commodity_code,commodity_name,commodity_category,base_unit,reporting_unit,
 energy_conversion_kbtu,emissions_factor_kg_co2e_per_unit,is_energy_commodity,is_active,created_at)
VALUES (s.commodity_id,s.commodity_code,s.commodity_name,s.commodity_category,s.base_unit,s.reporting_unit,
 s.energy_conversion_kbtu,s.emissions_factor_kg_co2e_per_unit,s.is_energy_commodity,s.is_active,current_timestamp());

MERGE INTO dim_property t
USING (SELECT * FROM VALUES
 ('PROP-HOU-001','HOU-001','Houston Office Center','Office','Owned','1000 Main Street','Houston','Harris','TX','Texas','77002','America/Chicago',29.7604,-95.3698,185000),
 ('PROP-DAL-001','DAL-001','Dallas Distribution Campus','Industrial','Leased','2500 Commerce Drive','Dallas','Dallas','TX','Texas','75201','America/Chicago',32.7767,-96.7970,310000),
 ('PROP-PHX-001','PHX-001','Phoenix Retail Plaza','Retail','Managed','500 Central Avenue','Phoenix','Maricopa','AZ','Arizona','85004','America/Phoenix',33.4484,-112.0740,96000),
 ('PROP-CHI-001','CHI-001','Chicago Residential Tower','Multifamily','Owned','200 Lake Shore Drive','Chicago','Cook','IL','Illinois','60601','America/Chicago',41.8781,-87.6298,225000),
 ('PROP-NYC-001','NYC-001','New York Business Center','Office','Leased','350 Fifth Avenue','New York','New York','NY','New York','10001','America/New_York',40.7506,-73.9972,142000)
 AS s(property_id,property_code,property_name,property_type,ownership_type,address_line_1,city,county,state_code,state_name,
 postal_code,timezone,latitude,longitude,gross_area_sqft)
) s ON t.property_id=s.property_id
WHEN NOT MATCHED THEN INSERT (property_id,property_code,property_name,property_type,ownership_type,address_line_1,city,county,
 state_code,state_name,postal_code,country_code,country_name,timezone,latitude,longitude,gross_area_sqft,
 rentable_area_sqft,operating_status,created_at,updated_at)
VALUES (s.property_id,s.property_code,s.property_name,s.property_type,s.ownership_type,s.address_line_1,s.city,s.county,
 s.state_code,s.state_name,s.postal_code,'US','United States',s.timezone,s.latitude,s.longitude,s.gross_area_sqft,
 s.gross_area_sqft*0.90,'Active',current_timestamp(),current_timestamp());

MERGE INTO dim_vendor t
USING (SELECT * FROM VALUES
 ('VEND-UTIL-ELEC','UTIL-ELEC','Example US Electric Utility','Utility','Net 30'),
 ('VEND-UTIL-GAS','UTIL-GAS','Example US Natural Gas Utility','Utility','Net 30'),
 ('VEND-UTIL-WATER','UTIL-WATER','Example Municipal Water Utility','Utility','Net 30'),
 ('VEND-ESCO','ESCO-001','Example Energy Services Supplier','ESCO','Net 45'),
 ('VEND-BROKER','BROKER-001','Example Energy Procurement Broker','Broker','Net 30'),
 ('VEND-METER','METER-001','Example Metering Services','Meter Provider','Net 30'),
 ('VEND-CONTRACTOR','CONTR-001','Example Energy Controls Contractor','Contractor','Net 30')
 AS s(vendor_id,vendor_code,vendor_name,vendor_type,payment_terms)
) s ON t.vendor_id=s.vendor_id
WHEN NOT MATCHED THEN INSERT (vendor_id,vendor_code,vendor_name,vendor_type,payment_terms,vendor_status,remit_country_code,created_at,updated_at)
VALUES (s.vendor_id,s.vendor_code,s.vendor_name,s.vendor_type,s.payment_terms,'Active','US',current_timestamp(),current_timestamp());

MERGE INTO dim_rate_class t
USING (SELECT * FROM VALUES
 ('RC-ELEC-COM','COMM-TOU','Commercial Time-of-Use','VEND-UTIL-ELEC','COM-ELEC','Commercial','Medium Voltage',500.0),
 ('RC-GAS-COM','COMM-GAS','Commercial Natural Gas','VEND-UTIL-GAS','COM-GAS','Commercial','N/A',NULL),
 ('RC-WATER-COM','COMM-WATER','Commercial Water Service','VEND-UTIL-WATER','COM-WATER','Commercial','N/A',NULL)
 AS s(rate_class_id,rate_class_code,rate_class_name,utility_vendor_id,commodity_id,customer_segment,voltage_level,demand_threshold_kw)
) s ON t.rate_class_id=s.rate_class_id
WHEN NOT MATCHED THEN INSERT (rate_class_id,rate_class_code,rate_class_name,utility_vendor_id,commodity_id,customer_segment,
 voltage_level,demand_threshold_kw,description,effective_start_date,effective_end_date,is_active,created_at)
VALUES (s.rate_class_id,s.rate_class_code,s.rate_class_name,s.utility_vendor_id,s.commodity_id,s.customer_segment,
 s.voltage_level,s.demand_threshold_kw,'Synthetic US commercial tariff class',DATE'2026-01-01',DATE'2026-12-31',TRUE,current_timestamp());

-- One electricity, gas and water service/account per property.
MERGE INTO bridge_property_commodity_service t
USING (
 SELECT p.property_id,p.address_line_1,c.commodity_id,
        CASE c.commodity_id WHEN 'COM-ELEC' THEN 'VEND-UTIL-ELEC'
             WHEN 'COM-GAS' THEN 'VEND-UTIL-GAS' ELSE 'VEND-UTIL-WATER' END utility_vendor_id,
        concat('PS-',p.property_id,'-',c.commodity_id) property_service_id
 FROM dim_property p
 CROSS JOIN (SELECT 'COM-ELEC' commodity_id UNION ALL SELECT 'COM-GAS' UNION ALL SELECT 'COM-WATER') c
 WHERE p.property_id LIKE 'PROP-%'
) s ON t.property_service_id=s.property_service_id
WHEN NOT MATCHED THEN INSERT (property_service_id,property_id,commodity_id,service_location_code,service_address,
 utility_vendor_id,service_start_date,service_status,is_common_area,created_at)
VALUES (s.property_service_id,s.property_id,s.commodity_id,'MAIN',s.address_line_1,
 s.utility_vendor_id,DATE'2026-01-01','Active',TRUE,current_timestamp());

MERGE INTO dim_utility_account t
USING (
 SELECT p.property_id,p.property_code,p.address_line_1,p.city,p.state_code,p.postal_code,
        c.commodity_id,c.commodity_code,c.commodity_name,
        concat('UA-',p.property_id,'-',c.commodity_code) utility_account_id,
        concat('TEST-',p.property_code,'-',c.commodity_code) account_number,
        concat(p.property_name,' ',c.commodity_name,' account') account_name,
        concat('PS-',p.property_id,'-',c.commodity_id) property_service_id,
        CASE c.commodity_id WHEN 'COM-ELEC' THEN 'VEND-UTIL-ELEC'
             WHEN 'COM-GAS' THEN 'VEND-UTIL-GAS' ELSE 'VEND-UTIL-WATER' END utility_vendor_id,
        CASE c.commodity_id WHEN 'COM-ELEC' THEN 'RC-ELEC-COM'
             WHEN 'COM-GAS' THEN 'RC-GAS-COM' ELSE 'RC-WATER-COM' END rate_class_id
 FROM dim_property p
 CROSS JOIN (SELECT 'COM-ELEC' commodity_id,'ELEC' commodity_code,'Electricity' commodity_name
             UNION ALL SELECT 'COM-GAS','GAS','Natural Gas'
             UNION ALL SELECT 'COM-WATER','WATER','Water') c
 WHERE p.property_id LIKE 'PROP-%'
) s ON t.utility_account_id=s.utility_account_id
WHEN NOT MATCHED THEN INSERT (utility_account_id,account_number,account_name,property_id,property_service_id,commodity_id,
 utility_vendor_id,billing_address,billing_city,billing_state,billing_postal_code,billing_country_code,rate_class_id,
 payment_method,payment_terms,account_open_date,account_status,cost_center,general_ledger_account,currency_code,created_at,updated_at)
VALUES (s.utility_account_id,s.account_number,s.account_name,s.property_id,s.property_service_id,s.commodity_id,
 s.utility_vendor_id,s.address_line_1,s.city,s.state_code,s.postal_code,'US',s.rate_class_id,'ACH','Net 30',
 DATE'2026-01-01','Active',concat('CC-',s.property_code),
 CASE s.commodity_id WHEN 'COM-ELEC' THEN '610100' WHEN 'COM-GAS' THEN '610200' ELSE '610300' END,
 'USD',current_timestamp(),current_timestamp());

-- Two electricity meters + one gas meter + one water meter per property.
MERGE INTO dim_meter t
USING (
 SELECT p.property_id,p.property_code,p.property_name,c.commodity_id,c.unit_of_measure,
        a.utility_account_id,a.property_service_id,
        concat('MTR-',p.property_code,'-',c.meter_suffix) meter_id,
        concat('US-',p.property_code,'-',c.meter_suffix) meter_number,
        concat(p.property_name,' ',c.meter_label) meter_name,c.meter_type,c.meter_role,
        c.interval_minutes,c.tenant_space
 FROM dim_property p
 CROSS JOIN (
   SELECT 'COM-ELEC' commodity_id,'kWh' unit_of_measure,'ELEC-MAIN' meter_suffix,'Electric Main Meter' meter_label,'Interval' meter_type,'Revenue' meter_role,60 interval_minutes,'House' tenant_space,'ELEC' account_suffix
   UNION ALL SELECT 'COM-ELEC','kWh','ELEC-HVAC','HVAC Electricity Meter','Submeter','Tenant Allocation',60,'HVAC','ELEC'
   UNION ALL SELECT 'COM-GAS','therm','GAS-MAIN','Gas Main Meter','Interval','Revenue',1440,'House','GAS'
   UNION ALL SELECT 'COM-WATER','CCF','WATER-MAIN','Water Main Meter','Interval','Revenue',1440,'House','WATER'
 ) c
 JOIN (
   SELECT property_id,'COM-ELEC' commodity_id,concat('UA-',property_id,'-ELEC') utility_account_id,concat('PS-',property_id,'-COM-ELEC') property_service_id FROM dim_property
   UNION ALL SELECT property_id,'COM-GAS',concat('UA-',property_id,'-GAS'),concat('PS-',property_id,'-COM-GAS') FROM dim_property
   UNION ALL SELECT property_id,'COM-WATER',concat('UA-',property_id,'-WATER'),concat('PS-',property_id,'-COM-WATER') FROM dim_property
 ) a ON a.property_id=p.property_id AND a.commodity_id=c.commodity_id
 WHERE p.property_id LIKE 'PROP-%' AND a.utility_account_id=concat('UA-',p.property_id,'-',c.account_suffix)
) s ON t.meter_id=s.meter_id
WHEN NOT MATCHED THEN INSERT (meter_id,meter_number,meter_name,property_id,property_service_id,utility_account_id,
 commodity_id,meter_type,meter_role,unit_of_measure,multiplier,meter_manufacturer,meter_model,meter_serial_number,
 installation_date,interval_minutes,is_smart_meter,meter_status,tenant_space,created_at,updated_at)
VALUES (s.meter_id,s.meter_number,s.meter_name,s.property_id,s.property_service_id,s.utility_account_id,
 s.commodity_id,s.meter_type,s.meter_role,s.unit_of_measure,1.0,'Synthetic Meter Co.','SM-100',
 concat('SN-',s.meter_id),DATE'2026-01-01',s.interval_minutes,TRUE,'Active',s.tenant_space,current_timestamp(),current_timestamp());

-- Effective-dated rate schedules and rate components.
MERGE INTO dim_rate_schedule t
USING (SELECT * FROM VALUES
 ('RS-ELEC-2026','COMM-TOU-2026','Commercial Electricity TOU 2026','RC-ELEC-COM','VEND-UTIL-ELEC','COM-ELEC','Time of Use'),
 ('RS-GAS-2026','COMM-GAS-2026','Commercial Gas 2026','RC-GAS-COM','VEND-UTIL-GAS','COM-GAS','Fixed'),
 ('RS-WATER-2026','COMM-WATER-2026','Commercial Water 2026','RC-WATER-COM','VEND-UTIL-WATER','COM-WATER','Fixed')
 AS s(rate_schedule_id,rate_code,rate_name,rate_class_id,utility_vendor_id,commodity_id,rate_basis)
) s ON t.rate_schedule_id=s.rate_schedule_id
WHEN NOT MATCHED THEN INSERT (rate_schedule_id,rate_code,rate_name,rate_class_id,utility_vendor_id,commodity_id,
 rate_basis,currency_code,effective_start_date,effective_end_date,billing_cycle,demand_charge_applicable,tax_applicable,rate_status,created_at)
VALUES (s.rate_schedule_id,s.rate_code,s.rate_name,s.rate_class_id,s.utility_vendor_id,s.commodity_id,
 s.rate_basis,'USD',DATE'2026-01-01',DATE'2026-12-31','Monthly',s.commodity_id='COM-ELEC',TRUE,'Active',current_timestamp());

MERGE INTO fact_rate_component t
USING (SELECT * FROM VALUES
 ('RC-ELEC-SUPPLY','RS-ELEC-2026','SUPPLY','Electricity Supply','Supply','Per kWh',0.085,'kWh'),
 ('RC-ELEC-DELIVERY','RS-ELEC-2026','DELIVERY','Electricity Delivery','Delivery','Per kWh',0.045,'kWh'),
 ('RC-ELEC-DEMAND','RS-ELEC-2026','DEMAND','Monthly Demand','Demand','Per kW',12.50,'kW'),
 ('RC-GAS-SUPPLY','RS-GAS-2026','GAS-SUPPLY','Natural Gas Supply','Supply','Per therm',0.72,'therm'),
 ('RC-GAS-DELIVERY','RS-GAS-2026','GAS-DELIVERY','Natural Gas Delivery','Delivery','Per therm',0.31,'therm'),
 ('RC-WATER-USAGE','RS-WATER-2026','WATER-USAGE','Water Usage','Usage','Per CCF',4.25,'CCF'),
 ('RC-WATER-SEWER','RS-WATER-2026','SEWER','Sewer Service','Delivery','Per CCF',3.10,'CCF')
 AS s(rate_component_id,rate_schedule_id,component_code,component_name,charge_type,calculation_basis,unit_rate,unit_of_measure)
) s ON t.rate_component_id=s.rate_component_id
WHEN NOT MATCHED THEN INSERT (rate_component_id,rate_schedule_id,component_code,component_name,charge_type,
 calculation_basis,unit_rate,unit_of_measure,currency_code,effective_start_date,effective_end_date,created_at)
VALUES (s.rate_component_id,s.rate_schedule_id,s.component_code,s.component_name,s.charge_type,s.calculation_basis,
 s.unit_rate,s.unit_of_measure,'USD',DATE'2026-01-01',DATE'2026-12-31',current_timestamp());

-- Supplier agreements and many-to-many property contract coverage.
MERGE INTO dim_contract t
USING (SELECT * FROM VALUES
 ('CON-ELEC-2026','CTR-ELEC-2026','Electricity Supply Agreement - Test','VEND-ESCO','VEND-BROKER','Retail Supply','COM-ELEC','RC-ELEC-COM','RS-ELEC-2026',2500000.00),
 ('CON-GAS-2026','CTR-GAS-2026','Natural Gas Supply Agreement - Test','VEND-UTIL-GAS','VEND-BROKER','Utility Supply','COM-GAS','RC-GAS-COM','RS-GAS-2026',450000.00),
 ('CON-WATER-2026','CTR-WATER-2026','Municipal Water Service Agreement - Test','VEND-UTIL-WATER',NULL,'Utility Service','COM-WATER','RC-WATER-COM','RS-WATER-2026',125000.00)
 AS s(contract_id,contract_number,contract_name,supplier_vendor_id,broker_vendor_id,contract_type,commodity_id,rate_class_id,rate_schedule_id,estimated_annual_value)
) s ON t.contract_id=s.contract_id
WHEN NOT MATCHED THEN INSERT (contract_id,contract_number,contract_name,supplier_vendor_id,broker_vendor_id,contract_type,
 commodity_id,rate_class_id,rate_schedule_id,contract_start_date,contract_end_date,auto_renewal_flag,renewal_notice_days,
 termination_notice_days,pricing_type,currency_code,estimated_annual_value,payment_terms,contract_status,signed_date,notes,created_at,updated_at)
VALUES (s.contract_id,s.contract_number,s.contract_name,s.supplier_vendor_id,s.broker_vendor_id,s.contract_type,
 s.commodity_id,s.rate_class_id,s.rate_schedule_id,DATE'2026-01-01',DATE'2026-12-31',FALSE,60,30,'Fixed','USD',
 s.estimated_annual_value,'Net 30','Active',DATE'2025-12-15','Fictional test contract only.',current_timestamp(),current_timestamp());

MERGE INTO bridge_property_contract t
USING (SELECT p.property_id,c.contract_id,concat('PC-',p.property_id,'-',c.contract_id) property_contract_id
       FROM dim_property p CROSS JOIN dim_contract c WHERE p.property_id LIKE 'PROP-%') s
ON t.property_contract_id=s.property_contract_id
WHEN NOT MATCHED THEN INSERT (property_contract_id,property_id,contract_id,allocation_pct,effective_start_date,effective_end_date,created_at)
VALUES (s.property_contract_id,s.property_id,s.contract_id,100.0000,DATE'2026-01-01',DATE'2026-12-31',current_timestamp());

-- Generate 11 months of deterministic test usage per meter (Jan-Nov 2026).
MERGE INTO fact_property_energy_usage t
USING (
 WITH months AS (SELECT explode(sequence(DATE'2026-01-01',DATE'2026-11-01',INTERVAL 1 MONTH)) month_start),
 meter_base AS (
   SELECT m.meter_id,m.property_id,m.utility_account_id,m.commodity_id,a.utility_vendor_id vendor_id,
          CASE m.commodity_id WHEN 'COM-ELEC' THEN 'CON-ELEC-2026' WHEN 'COM-GAS' THEN 'CON-GAS-2026' ELSE 'CON-WATER-2026' END contract_id,
          CASE m.commodity_id WHEN 'COM-ELEC' THEN 'RS-ELEC-2026' WHEN 'COM-GAS' THEN 'RS-GAS-2026' ELSE 'RS-WATER-2026' END rate_schedule_id,
          m.unit_of_measure
   FROM dim_meter m JOIN dim_utility_account a ON m.utility_account_id=a.utility_account_id
   WHERE m.meter_status='Active' AND m.property_id LIKE 'PROP-%'
 ),
 generated AS (
   SELECT b.*,mo.month_start,
     CASE b.commodity_id
       WHEN 'COM-ELEC' THEN CAST(18000+pmod(abs(hash(concat(b.meter_id,CAST(mo.month_start AS STRING)))),12000) AS DECIMAL(20,6))
       WHEN 'COM-GAS' THEN CAST(800+pmod(abs(hash(concat(b.meter_id,CAST(mo.month_start AS STRING)))),900) AS DECIMAL(20,6))
       ELSE CAST(120+pmod(abs(hash(concat(b.meter_id,CAST(mo.month_start AS STRING)))),160) AS DECIMAL(20,6))
     END usage_quantity
   FROM meter_base b CROSS JOIN months mo
 )
 SELECT concat('USAGE-',meter_id,'-',date_format(month_start,'yyyyMM')) property_energy_usage_id,
        property_id,meter_id,utility_account_id,commodity_id,vendor_id,contract_id,rate_schedule_id,
        month_start period_start_date,last_day(month_start) period_end_date,usage_quantity,unit_of_measure usage_unit,
        CASE WHEN commodity_id='COM-ELEC' THEN usage_quantity/720.0 WHEN commodity_id='COM-GAS' THEN usage_quantity/30.0 END peak_demand_quantity,
        CASE WHEN commodity_id='COM-ELEC' THEN 'kW' WHEN commodity_id='COM-GAS' THEN 'therm/day' END peak_demand_unit,
        CAST(NULL AS DECIMAL(9,6)) power_factor,
        CAST(CASE WHEN commodity_id='COM-ELEC' THEN 68.0 END AS DECIMAL(9,4)) load_factor_pct,
        CAST(CASE commodity_id WHEN 'COM-ELEC' THEN usage_quantity*0.13 WHEN 'COM-GAS' THEN usage_quantity*1.03 ELSE usage_quantity*7.35 END AS DECIMAL(20,2)) cost_amount,
        'USD' currency_code,
        CAST(CASE commodity_id WHEN 'COM-ELEC' THEN usage_quantity*0.386 WHEN 'COM-GAS' THEN usage_quantity*5.30 ELSE 0 END AS DECIMAL(20,6)) emissions_kg_co2e,
        FALSE is_estimated,'SYNTHETIC_US_SEED' source_system,
        concat('SYN-',meter_id,'-',date_format(month_start,'yyyyMM')) source_record_id,current_timestamp() created_at
 FROM generated
) s ON t.property_energy_usage_id=s.property_energy_usage_id
WHEN NOT MATCHED THEN INSERT (property_energy_usage_id,property_id,meter_id,utility_account_id,commodity_id,vendor_id,
 contract_id,rate_schedule_id,period_start_date,period_end_date,usage_quantity,usage_unit,peak_demand_quantity,
 peak_demand_unit,power_factor,load_factor_pct,cost_amount,currency_code,emissions_kg_co2e,is_estimated,
 source_system,source_record_id,created_at)
VALUES (s.property_energy_usage_id,s.property_id,s.meter_id,s.utility_account_id,s.commodity_id,s.vendor_id,
 s.contract_id,s.rate_schedule_id,s.period_start_date,s.period_end_date,s.usage_quantity,s.usage_unit,
 s.peak_demand_quantity,s.peak_demand_unit,s.power_factor,s.load_factor_pct,s.cost_amount,s.currency_code,
 s.emissions_kg_co2e,s.is_estimated,s.source_system,s.source_record_id,s.created_at);

-- Monthly cumulative meter register reads corresponding to usage facts.
MERGE INTO fact_meter_reading t
USING (
 WITH cumulative AS (
   SELECT u.*,SUM(u.usage_quantity) OVER (PARTITION BY u.meter_id ORDER BY u.period_start_date
      ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) cumulative_reading
   FROM fact_property_energy_usage u WHERE u.source_system='SYNTHETIC_US_SEED'
 )
 SELECT concat('READ-',meter_id,'-',date_format(period_start_date,'yyyyMM')) meter_reading_id,
        property_id,meter_id,utility_account_id,commodity_id,CAST(period_start_date AS TIMESTAMP) reading_start_ts,
        CAST(date_add(period_end_date,1) AS TIMESTAMP) reading_end_ts,period_end_date reading_date,
        'Actual' reading_type,'Synthetic AMI' reading_source,
        CAST(cumulative_reading-usage_quantity AS DECIMAL(20,6)) previous_reading,
        CAST(cumulative_reading AS DECIMAL(20,6)) current_reading,usage_quantity consumption_quantity,
        usage_unit unit_of_measure,1.0 multiplier,peak_demand_quantity demand_quantity,peak_demand_unit demand_unit,
        'Validated' data_quality_status,current_timestamp() ingestion_timestamp,source_record_id
 FROM cumulative
) s ON t.meter_reading_id=s.meter_reading_id
WHEN NOT MATCHED THEN INSERT (meter_reading_id,property_id,meter_id,utility_account_id,commodity_id,reading_start_ts,
 reading_end_ts,reading_date,reading_type,reading_source,previous_reading,current_reading,consumption_quantity,
 unit_of_measure,multiplier,demand_quantity,demand_unit,data_quality_status,ingestion_timestamp,source_record_id)
VALUES (s.meter_reading_id,s.property_id,s.meter_id,s.utility_account_id,s.commodity_id,s.reading_start_ts,
 s.reading_end_ts,s.reading_date,s.reading_type,s.reading_source,s.previous_reading,s.current_reading,
 s.consumption_quantity,s.unit_of_measure,s.multiplier,s.demand_quantity,s.demand_unit,s.data_quality_status,
 s.ingestion_timestamp,s.source_record_id);

-- Utility bill headers: one account / billing month.
MERGE INTO fact_energy_bill t
USING (
 SELECT concat('BILL-',utility_account_id,'-',date_format(period_start_date,'yyyyMM')) energy_bill_id,
        concat('INV-',utility_account_id,'-',date_format(period_start_date,'yyyyMM')) bill_number,
        property_id,utility_account_id,vendor_id,contract_id,period_start_date bill_period_start,
        period_end_date bill_period_end,date_add(period_end_date,5) invoice_date,date_add(period_end_date,35) due_date,
        SUM(usage_quantity) total_usage_quantity,usage_unit,
        CAST(SUM(cost_amount)*0.94 AS DECIMAL(20,2)) subtotal_amount,
        CAST(SUM(cost_amount)*0.06 AS DECIMAL(20,2)) tax_amount,
        CAST(SUM(cost_amount) AS DECIMAL(20,2)) total_amount,'USD' currency_code,
        CASE WHEN month(period_start_date)<=10 THEN CAST(SUM(cost_amount) AS DECIMAL(20,2)) ELSE 0 END amount_paid,
        CASE WHEN month(period_start_date)<=10 THEN 0 ELSE CAST(SUM(cost_amount) AS DECIMAL(20,2)) END balance_amount,
        CASE WHEN month(period_start_date)<=10 THEN 'Paid' ELSE 'Open' END payment_status,
        'Posted' bill_status,current_timestamp() created_at
 FROM fact_property_energy_usage WHERE source_system='SYNTHETIC_US_SEED'
 GROUP BY utility_account_id,property_id,vendor_id,contract_id,period_start_date,period_end_date,usage_unit
) s ON t.energy_bill_id=s.energy_bill_id
WHEN NOT MATCHED THEN INSERT (energy_bill_id,bill_number,property_id,utility_account_id,vendor_id,contract_id,
 bill_period_start,bill_period_end,invoice_date,due_date,total_usage_quantity,usage_unit,subtotal_amount,tax_amount,
 total_amount,currency_code,amount_paid,balance_amount,payment_status,bill_status,created_at)
VALUES (s.energy_bill_id,s.bill_number,s.property_id,s.utility_account_id,s.vendor_id,s.contract_id,
 s.bill_period_start,s.bill_period_end,s.invoice_date,s.due_date,s.total_usage_quantity,s.usage_unit,s.subtotal_amount,
 s.tax_amount,s.total_amount,s.currency_code,s.amount_paid,s.balance_amount,s.payment_status,s.bill_status,s.created_at);

-- Bill lines split by rate components; blended line totals reconcile to bill usage amounts.
MERGE INTO fact_energy_bill_line t
USING (
 SELECT concat('BL-E-S-',meter_id,'-',date_format(period_start_date,'yyyyMM')) energy_bill_line_id,
        concat('BILL-',utility_account_id,'-',date_format(period_start_date,'yyyyMM')) energy_bill_id,
        property_id,meter_id,commodity_id,rate_schedule_id,'RC-ELEC-SUPPLY' rate_component_id,
        'ELEC-SUPPLY' charge_code,'Electricity supply' charge_description,'Supply' charge_type,
        usage_quantity quantity,usage_unit unit_of_measure,0.085 unit_rate,
        CAST(usage_quantity*0.085 AS DECIMAL(20,2)) line_amount,'USD' currency_code,current_timestamp() created_at
 FROM fact_property_energy_usage WHERE source_system='SYNTHETIC_US_SEED' AND commodity_id='COM-ELEC'
 UNION ALL
 SELECT concat('BL-E-D-',meter_id,'-',date_format(period_start_date,'yyyyMM')),
        concat('BILL-',utility_account_id,'-',date_format(period_start_date,'yyyyMM')),
        property_id,meter_id,commodity_id,rate_schedule_id,'RC-ELEC-DELIVERY','ELEC-DELIVERY',
        'Electricity delivery','Delivery',usage_quantity,usage_unit,0.045,
        CAST(usage_quantity*0.045 AS DECIMAL(20,2)),'USD',current_timestamp()
 FROM fact_property_energy_usage WHERE source_system='SYNTHETIC_US_SEED' AND commodity_id='COM-ELEC'
 UNION ALL
 SELECT concat('BL-G-S-',meter_id,'-',date_format(period_start_date,'yyyyMM')),
        concat('BILL-',utility_account_id,'-',date_format(period_start_date,'yyyyMM')),
        property_id,meter_id,commodity_id,rate_schedule_id,'RC-GAS-SUPPLY','GAS-SUPPLY',
        'Natural gas supply','Supply',usage_quantity,usage_unit,0.72,
        CAST(usage_quantity*0.72 AS DECIMAL(20,2)),'USD',current_timestamp()
 FROM fact_property_energy_usage WHERE source_system='SYNTHETIC_US_SEED' AND commodity_id='COM-GAS'
 UNION ALL
 SELECT concat('BL-G-D-',meter_id,'-',date_format(period_start_date,'yyyyMM')),
        concat('BILL-',utility_account_id,'-',date_format(period_start_date,'yyyyMM')),
        property_id,meter_id,commodity_id,rate_schedule_id,'RC-GAS-DELIVERY','GAS-DELIVERY',
        'Natural gas delivery','Delivery',usage_quantity,usage_unit,0.31,
        CAST(usage_quantity*0.31 AS DECIMAL(20,2)),'USD',current_timestamp()
 FROM fact_property_energy_usage WHERE source_system='SYNTHETIC_US_SEED' AND commodity_id='COM-GAS'
 UNION ALL
 SELECT concat('BL-W-U-',meter_id,'-',date_format(period_start_date,'yyyyMM')),
        concat('BILL-',utility_account_id,'-',date_format(period_start_date,'yyyyMM')),
        property_id,meter_id,commodity_id,rate_schedule_id,'RC-WATER-USAGE','WATER-USAGE',
        'Water usage','Usage',usage_quantity,usage_unit,4.25,
        CAST(usage_quantity*4.25 AS DECIMAL(20,2)),'USD',current_timestamp()
 FROM fact_property_energy_usage WHERE source_system='SYNTHETIC_US_SEED' AND commodity_id='COM-WATER'
 UNION ALL
 SELECT concat('BL-W-S-',meter_id,'-',date_format(period_start_date,'yyyyMM')),
        concat('BILL-',utility_account_id,'-',date_format(period_start_date,'yyyyMM')),
        property_id,meter_id,commodity_id,rate_schedule_id,'RC-WATER-SEWER','WATER-SEWER',
        'Sewer service','Delivery',usage_quantity,usage_unit,3.10,
        CAST(usage_quantity*3.10 AS DECIMAL(20,2)),'USD',current_timestamp()
 FROM fact_property_energy_usage WHERE source_system='SYNTHETIC_US_SEED' AND commodity_id='COM-WATER'
) s ON t.energy_bill_line_id=s.energy_bill_line_id
WHEN NOT MATCHED THEN INSERT (energy_bill_line_id,energy_bill_id,property_id,meter_id,commodity_id,rate_schedule_id,
 rate_component_id,charge_code,charge_description,charge_type,quantity,unit_of_measure,unit_rate,line_amount,currency_code,created_at)
VALUES (s.energy_bill_line_id,s.energy_bill_id,s.property_id,s.meter_id,s.commodity_id,s.rate_schedule_id,
 s.rate_component_id,s.charge_code,s.charge_description,s.charge_type,s.quantity,s.unit_of_measure,s.unit_rate,
 s.line_amount,s.currency_code,s.created_at);

-- Sample procurement: five POs, one for each property.
MERGE INTO fact_purchase_order t
USING (SELECT * FROM VALUES
 ('PO-HOU-001','PO-2026-HOU-001','PROP-HOU-001','VEND-CONTRACTOR','CON-ELEC-2026',DATE'2026-02-10','Energy controls upgrade',18500.00),
 ('PO-DAL-001','PO-2026-DAL-001','PROP-DAL-001','VEND-METER','CON-ELEC-2026',DATE'2026-03-12','Smart meter installation',24600.00),
 ('PO-PHX-001','PO-2026-PHX-001','PROP-PHX-001','VEND-ESCO','CON-ELEC-2026',DATE'2026-04-08','Lighting and HVAC efficiency',31200.00),
 ('PO-CHI-001','PO-2026-CHI-001','PROP-CHI-001','VEND-CONTRACTOR','CON-GAS-2026',DATE'2026-05-18','Boiler controls maintenance',12800.00),
 ('PO-NYC-001','PO-2026-NYC-001','PROP-NYC-001','VEND-METER','CON-ELEC-2026',DATE'2026-06-22','Submeter installation',21900.00)
 AS s(purchase_order_id,purchase_order_number,property_id,vendor_id,contract_id,order_date,description,total_amount)
) s ON t.purchase_order_id=s.purchase_order_id
WHEN NOT MATCHED THEN INSERT (purchase_order_id,purchase_order_number,property_id,vendor_id,contract_id,order_date,
 requested_delivery_date,approved_date,currency_code,subtotal_amount,tax_amount,total_amount,buyer_name,department,
 cost_center,approval_status,purchase_order_status,description,created_at)
VALUES (s.purchase_order_id,s.purchase_order_number,s.property_id,s.vendor_id,s.contract_id,s.order_date,
 date_add(s.order_date,30),date_add(s.order_date,2),'USD',s.total_amount*0.94,s.total_amount*0.06,s.total_amount,
 'Energy Procurement Team','Facilities',concat('CC-',s.property_id),'Approved','Closed',s.description,current_timestamp());

MERGE INTO fact_purchase_order_line t
USING (SELECT * FROM VALUES
 ('POL-HOU-001','PO-HOU-001','PROP-HOU-001','COM-ELEC','MTR-HOU-001-ELEC-MAIN','Building automation controller','Energy Controls',1,18500.00),
 ('POL-DAL-001','PO-DAL-001','PROP-DAL-001','COM-ELEC','MTR-DAL-001-ELEC-MAIN','Smart electricity meter','Metering Equipment',4,24600.00),
 ('POL-PHX-001','PO-PHX-001','PROP-PHX-001','COM-ELEC','MTR-PHX-001-ELEC-MAIN','LED and HVAC efficiency package','Energy Efficiency',1,31200.00),
 ('POL-CHI-001','PO-CHI-001','PROP-CHI-001','COM-GAS','MTR-CHI-001-GAS-MAIN','Boiler control service','Maintenance',1,12800.00),
 ('POL-NYC-001','PO-NYC-001','PROP-NYC-001','COM-ELEC','MTR-NYC-001-ELEC-HVAC','Tenant submeter','Metering Equipment',2,21900.00)
 AS s(purchase_order_line_id,purchase_order_id,property_id,commodity_id,meter_id,item_description,procurement_category,quantity,line_amount)
) s ON t.purchase_order_line_id=s.purchase_order_line_id
WHEN NOT MATCHED THEN INSERT (purchase_order_line_id,purchase_order_id,property_id,commodity_id,meter_id,item_description,
 procurement_category,quantity,unit_of_measure,unit_price,line_amount,currency_code,created_at)
VALUES (s.purchase_order_line_id,s.purchase_order_id,s.property_id,s.commodity_id,s.meter_id,s.item_description,
 s.procurement_category,s.quantity,'Each',s.line_amount/s.quantity,s.line_amount,'USD',current_timestamp());

MERGE INTO fact_vendor_invoice t
USING (SELECT po.purchase_order_id,po.purchase_order_number,po.vendor_id,po.property_id,po.contract_id,po.order_date,po.total_amount,
       concat('VINV-',po.purchase_order_id) vendor_invoice_id,concat('SUP-',po.purchase_order_number) vendor_invoice_number
       FROM fact_purchase_order po WHERE po.purchase_order_id LIKE 'PO-%') s
ON t.vendor_invoice_id=s.vendor_invoice_id
WHEN NOT MATCHED THEN INSERT (vendor_invoice_id,vendor_invoice_number,vendor_id,property_id,contract_id,purchase_order_id,
 invoice_date,due_date,subtotal_amount,tax_amount,total_amount,currency_code,invoice_status,approval_status,created_at)
VALUES (s.vendor_invoice_id,s.vendor_invoice_number,s.vendor_id,s.property_id,s.contract_id,s.purchase_order_id,
 date_add(s.order_date,10),date_add(s.order_date,40),s.total_amount*0.94,s.total_amount*0.06,s.total_amount,
 'USD','Approved','Approved',current_timestamp());

MERGE INTO fact_vendor_invoice_line t
USING (SELECT vi.vendor_invoice_id,pol.purchase_order_line_id,pol.property_id,pol.commodity_id,
       pol.item_description,pol.quantity,pol.unit_of_measure,pol.unit_price,pol.line_amount
       FROM fact_vendor_invoice vi JOIN fact_purchase_order_line pol ON vi.purchase_order_id=pol.purchase_order_id
       WHERE vi.vendor_invoice_id LIKE 'VINV-PO-%') s
ON t.vendor_invoice_line_id=concat('VIL-',s.purchase_order_line_id)
WHEN NOT MATCHED THEN INSERT (vendor_invoice_line_id,vendor_invoice_id,purchase_order_line_id,property_id,commodity_id,
 description,quantity,unit_of_measure,unit_price,line_amount,currency_code,created_at)
VALUES (concat('VIL-',s.purchase_order_line_id),s.vendor_invoice_id,s.purchase_order_line_id,s.property_id,s.commodity_id,
 s.item_description,s.quantity,s.unit_of_measure,s.unit_price,s.line_amount,'USD',current_timestamp());

MERGE INTO fact_vendor_payment t
USING (SELECT vi.vendor_invoice_id,vi.vendor_id,vi.property_id,vi.total_amount,
       concat('PAY-',vi.vendor_invoice_id) vendor_payment_id
       FROM fact_vendor_invoice vi WHERE vi.vendor_invoice_id LIKE 'VINV-PO-%') s
ON t.vendor_payment_id=s.vendor_payment_id
WHEN NOT MATCHED THEN INSERT (vendor_payment_id,vendor_invoice_id,vendor_id,property_id,payment_date,
 payment_reference,payment_method,payment_amount,currency_code,payment_status,created_at)
VALUES (s.vendor_payment_id,s.vendor_invoice_id,s.vendor_id,s.property_id,DATE'2026-11-15',
 concat('ACH-',s.vendor_payment_id),'ACH',s.total_amount,'USD','Paid',current_timestamp());

-- VALIDATION: row counts, property inventory, energy totals, contract coverage.
SELECT 'dim_property' table_name,COUNT(*) row_count FROM dim_property WHERE property_id LIKE 'PROP-%'
UNION ALL SELECT 'dim_commodity',COUNT(*) FROM dim_commodity WHERE commodity_id LIKE 'COM-%'
UNION ALL SELECT 'dim_vendor',COUNT(*) FROM dim_vendor WHERE vendor_id LIKE 'VEND-%'
UNION ALL SELECT 'dim_utility_account',COUNT(*) FROM dim_utility_account WHERE utility_account_id LIKE 'UA-%'
UNION ALL SELECT 'dim_meter',COUNT(*) FROM dim_meter WHERE meter_id LIKE 'MTR-%'
UNION ALL SELECT 'fact_property_energy_usage',COUNT(*) FROM fact_property_energy_usage WHERE source_system='SYNTHETIC_US_SEED'
UNION ALL SELECT 'fact_meter_reading',COUNT(*) FROM fact_meter_reading WHERE source_record_id LIKE 'SYN-%'
UNION ALL SELECT 'fact_energy_bill',COUNT(*) FROM fact_energy_bill WHERE energy_bill_id LIKE 'BILL-UA-%'
UNION ALL SELECT 'fact_purchase_order',COUNT(*) FROM fact_purchase_order WHERE purchase_order_id LIKE 'PO-%'
UNION ALL SELECT 'fact_vendor_invoice',COUNT(*) FROM fact_vendor_invoice WHERE vendor_invoice_id LIKE 'VINV-PO-%'
UNION ALL SELECT 'fact_vendor_payment',COUNT(*) FROM fact_vendor_payment WHERE vendor_payment_id LIKE 'PAY-VINV-PO-%'
ORDER BY table_name;

SELECT p.property_code,p.property_name,p.city,p.state_code,c.commodity_name,u.period_start_date,
       SUM(u.usage_quantity) total_usage,u.usage_unit,SUM(u.cost_amount) total_cost,u.currency_code,
       SUM(u.emissions_kg_co2e) emissions_kg_co2e
FROM fact_property_energy_usage u
JOIN dim_property p ON u.property_id=p.property_id
JOIN dim_commodity c ON u.commodity_id=c.commodity_id
WHERE u.source_system='SYNTHETIC_US_SEED'
GROUP BY p.property_code,p.property_name,p.city,p.state_code,c.commodity_name,u.period_start_date,u.usage_unit,u.currency_code
ORDER BY p.property_name,u.period_start_date,c.commodity_name;

-- Relationship checks should return zero.
SELECT 'meter_without_property' check_name,COUNT(*) issue_count
FROM dim_meter m LEFT JOIN dim_property p ON m.property_id=p.property_id WHERE p.property_id IS NULL
UNION ALL
SELECT 'meter_without_commodity',COUNT(*)
FROM dim_meter m LEFT JOIN dim_commodity c ON m.commodity_id=c.commodity_id WHERE c.commodity_id IS NULL
UNION ALL
SELECT 'account_without_vendor',COUNT(*)
FROM dim_utility_account a LEFT JOIN dim_vendor v ON a.utility_vendor_id=v.vendor_id WHERE v.vendor_id IS NULL
UNION ALL
SELECT 'usage_without_property',COUNT(*)
FROM fact_property_energy_usage u LEFT JOIN dim_property p ON u.property_id=p.property_id WHERE p.property_id IS NULL;
