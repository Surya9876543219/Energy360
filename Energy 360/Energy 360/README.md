# Energy 360 – United States Energy Management Databricks App

This app is configured for US energy reporting. Populate `dim_state` with US states and territories, use US plant and asset records, and store energy-cost values in USD. The current physical cost-column names (`*_inr`) are legacy schema names; migrate them to `*_usd` when updating the table schema, or keep the aliases in the application queries aligned with your existing schema.

## Confirmed source tables and joins

- `fact_generation.datekey` -> `dim_date.datekey`
- `fact_generation.plantkey` -> `dim_power_plant.plantkey`
- `fact_generation.statekey` -> `dim_state.statekey`
- `fact_generation.sourcekey` -> `dim_energy_source.sourcekey`
- `fact_consumption.datekey` -> `dim_date.datekey`
- `fact_consumption.statekey` -> `dim_state.statekey`
- `fact_grid_performance.datekey` -> `dim_date.datekey`
- `fact_grid_performance.statekey` -> `dim_state.statekey`
- `fact_asset_performance.datekey` -> `dim_date.datekey`
- `fact_asset_performance.assetkey` -> `dim_asset.assetkey`
- `fact_asset_performance.plantkey` -> `dim_power_plant.plantkey`
- `fact_asset_performance.statekey` -> `dim_state.statekey`
- `fact_carbon_emissions.datekey` -> `dim_date.datekey`
- `fact_carbon_emissions.statekey` -> `dim_state.statekey`
- `fact_carbon_emissions.sourcekey` -> `dim_energy_source.sourcekey`
- `fact_energy_cost.datekey` -> `dim_date.datekey`
- `fact_energy_cost.statekey` -> `dim_state.statekey`
- `fact_energy_cost.sourcekey` -> `dim_energy_source.sourcekey`

## Configure
Default catalog/schema: `energy.energy`.

If different, set:
- `ENERGY360_CATALOG`
- `ENERGY360_SCHEMA`

Attach a SQL Warehouse as a Databricks App resource. The app uses its workload identity through the Databricks SDK.

## Permissions
Replace `<app-service-principal>` with the actual app service principal:

```sql
GRANT USE CATALOG ON CATALOG energy TO `<app-service-principal>`;
GRANT USE SCHEMA ON SCHEMA energy.energy TO `<app-service-principal>`;
GRANT SELECT ON ALL TABLES IN SCHEMA energy.energy TO `<app-service-principal>`;
```

## US sample-data requirements

- `dim_state` should contain US states with USPS codes and valid latitude/longitude coordinates (for example CA, TX, NY and FL).
- Use US-based power plants, energy assets, utility/grid records and consumption sectors.
- Cost, revenue and gross-margin values must be populated as USD amounts; set `currency` to `USD`.
- The application does not convert INR values into USD. Replace the existing India sample records in all 11 Unity Catalog tables before treating the dashboard as US reporting.

## Important data notes
- `fact_carbon_emissions` was supplied twice in the schema listing; it is treated as one table.
- No separate forecast fact table was included. Forecasting page therefore shows historical generation and clearly states that forecasts require a model/table.
- No separate distribution fact table was included. Transmission loss, outage, SAIDI and grid availability are sourced from `fact_grid_performance`.
- The app does not create, overwrite or insert into your tables.
- The state map uses `dim_state.latitude` and `dim_state.longitude`.
- Generation source is joined through `sourcekey`; consumption uses its existing `consumersector` field.
- Dashboard measures use the exact column names supplied.


## Property-centric energy management

The property model extends the existing portfolio/state-level Energy 360 model; it does not replace the original 11 dashboard tables.

### Deployment script

Run [property_energy_model_and_us_seed.sql](sql/property_energy_model_and_us_seed.sql) in a **development/test catalog first**. The script creates 20 Delta tables and then merges fictional US test data. It is additive and repeatable; it does not delete or overwrite existing rows.

### Included data model

- Property master and parent-property hierarchy
- Commodity master and property-commodity service relationships
- Utility accounts and meter / submeter master
- Interval meter readings and property-level energy usage
- Utility bill headers and tariff-component bill lines
- Vendor / utility / supplier master
- Rate classes, effective-dated rate schedules and rate components
- Supplier contracts and property-contract allocation bridge
- Procurement purchase orders, PO lines, vendor invoices, invoice lines and payments

### Synthetic US test data

The script seeds five fictional properties across Texas, Arizona, Illinois and New York; six commodity master records; seven fictional vendors; 15 utility accounts; 20 meters; three rate classes and schedules; supplier contracts; monthly energy usage and meter readings for January–November 2026; utility bills with split tariff components; and example procurement transactions.

The generated usage is tagged with `source_system = 'SYNTHETIC_US_SEED'`. All sample property names, addresses, account numbers, meter IDs, supplier names, rates, contracts, bills, purchase orders and payments are fictional. The sample data is for development and demonstration only and must not be treated as real customer records or real utility tariffs.

### Deployment steps

1. Open a Databricks SQL editor or SQL notebook attached to the intended SQL Warehouse.
2. Confirm the target catalog/schema at the beginning of the script (default `energy.energy`).
3. Run the complete SQL script.
4. Review the row-count, property-energy summary and relationship-check queries at the end.
5. Load approved actual property, meter, account, vendor, contract and procurement records from source systems using ETL / MERGE logic and their real source-system keys.
6. Keep synthetic test records separate from production data. Prefer a dedicated development catalog/schema for the synthetic seed.

### Relationship and measurement notes

- One property can have multiple commodity services, utility accounts and meters.
- One utility account can have multiple meters.
- One contract can cover multiple properties; `bridge_property_contract` stores the relationship and allocation percentage.
- Rate schedules are effective-dated and split into supply, delivery, demand, usage and other rate components.
- Utility bills are separate from procurement vendor invoices and purchase orders.
- Delta Lake does not enforce conventional foreign keys. Validate logical IDs in ETL and use the relationship checks included in the SQL script.
- Energy quantities retain their units. Do not sum kWh, therms and CCF together without converting them to a common unit.
- Currency is stored explicitly; synthetic US financial records use USD.
