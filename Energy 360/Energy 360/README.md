# Energy 360 – Schema-aligned Databricks App

This app is aligned to the table and column names supplied for catalog `energy`, schema `energy`.

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

## Important data notes
- `fact_carbon_emissions` was supplied twice in the schema listing; it is treated as one table.
- No separate forecast fact table was included. Forecasting page therefore shows historical generation and clearly states that forecasts require a model/table.
- No separate distribution fact table was included. Transmission loss, outage, SAIDI and grid availability are sourced from `fact_grid_performance`.
- The app does not create, overwrite or insert into your tables.
- The state map uses `dim_state.latitude` and `dim_state.longitude`.
- Generation source is joined through `sourcekey`; consumption uses its existing `consumersector` field.
- Dashboard measures use the exact column names supplied.
