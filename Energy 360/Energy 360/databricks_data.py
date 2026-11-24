import os
import re
from datetime import date
import pandas as pd
import numpy as np

class DataAccessError(RuntimeError):
    pass

class EnergyData:
    """
    SQL access for the exact Energy 360 schema supplied by the user.
    Expected catalog/schema defaults: energy.energy
    """

    def __init__(self, catalog="energy", schema="energy"):
        self.catalog = self._identifier(catalog)
        self.schema = self._identifier(schema)
        self.connection = None

    @staticmethod
    def _identifier(value):
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value or ""):
            raise DataAccessError(f"Invalid SQL identifier: {value!r}")
        return value

    def _connect(self):
        if self.connection is not None:
            try:
                with self.connection.cursor() as cur:
                    cur.execute("SELECT 1")
                return self.connection
            except Exception:
                self.connection = None
        try:
            from databricks.sdk import WorkspaceClient
            from databricks import sql

            w = WorkspaceClient()
            host = os.getenv("DATABRICKS_HOST") or w.config.host
            host = host.replace("https://", "").replace("http://", "").rstrip("/")
            warehouse_id = (
                os.getenv("DATABRICKS_WAREHOUSE_ID")
                or os.getenv("SQL_WAREHOUSE_ID")
                or os.getenv("ENERGY360_WAREHOUSE_ID")
            )
            http_path = os.getenv("DATABRICKS_HTTP_PATH") or os.getenv("SQL_WAREHOUSE_HTTP_PATH")
            if not http_path and warehouse_id:
                http_path = f"/sql/1.0/warehouses/{warehouse_id}"
            if not host or not http_path:
                raise DataAccessError(
                    "SQL Warehouse resource is not configured. Attach a SQL Warehouse to the app "
                    "and expose its warehouse ID, or set DATABRICKS_HTTP_PATH."
                )
            self.connection = sql.connect(
                server_hostname=host,
                http_path=http_path,
                credentials_provider=lambda: w.config.authenticate,
            )
            return self.connection
        except DataAccessError:
            raise
        except Exception as exc:
            raise DataAccessError(f"Databricks SQL connection failed: {exc}") from exc

    def query(self, sql_text):
        try:
            conn = self._connect()
            with conn.cursor() as cur:
                cur.execute(sql_text)
                rows = cur.fetchall()
                cols = [d[0] for d in cur.description] if cur.description else []
            return pd.DataFrame(rows, columns=cols)
        except DataAccessError:
            raise
        except Exception as exc:
            self.connection = None
            raise DataAccessError(f"SQL execution failed: {exc}") from exc

    def execute(self, sql_text):
        """Execute a DML statement that does not return a result set."""
        try:
            conn = self._connect()
            with conn.cursor() as cur:
                cur.execute(sql_text)
            return True
        except DataAccessError:
            raise
        except Exception as exc:
            self.connection = None
            raise DataAccessError(f"SQL execution failed: {exc}") from exc

    @property
    def qschema(self):
        return f"`{self.catalog}`.`{self.schema}`"

    def list_tables(self):
        df = self.query(f"SHOW TABLES IN {self.qschema}")
        if df.empty:
            return []
        col = next((c for c in df.columns if c.lower() in ("tablename","table_name")), df.columns[0])
        return sorted(df[col].astype(str).tolist())

    @staticmethod
    def _date_filter(start_date, end_date, alias="d"):
        if start_date is None or end_date is None:
            return ""
        return (
            f" AND CAST({alias}.date AS DATE) >= DATE'{start_date.isoformat()}'"
            f" AND CAST({alias}.date AS DATE) <= DATE'{end_date.isoformat()}'"
        )

    @staticmethod
    def _state_filter(state, alias="s"):
        if not state or state == "All US":
            return ""
        safe = state.replace("'", "''")
        return f" AND {alias}.statename = '{safe}'"

    def date_bounds(self):
        df = self.query(
            f"SELECT MIN(CAST(date AS DATE)) AS min_date, MAX(CAST(date AS DATE)) AS max_date "
            f"FROM {self.qschema}.dim_date"
        )
        if df.empty or pd.isna(df.iloc[0]["min_date"]):
            return None, None
        return pd.to_datetime(df.iloc[0]["min_date"]).date(), pd.to_datetime(df.iloc[0]["max_date"]).date()

    def state_names(self):
        df = self.query(f"SELECT statename FROM {self.qschema}.dim_state ORDER BY statename")
        return df["statename"].dropna().astype(str).tolist() if not df.empty else []

    def _filters(self, start_date, end_date, state, date_alias="d", state_alias="s"):
        return self._date_filter(start_date,end_date,date_alias) + self._state_filter(state,state_alias)

    def dashboard_data(self, start_date, end_date, state):
        q=self.qschema
        f_gen=self._filters(start_date,end_date,state,"d","s")
        f_cons=self._filters(start_date,end_date,state,"d","s")
        f_grid=self._filters(start_date,end_date,state,"d","s")
        f_em=self._filters(start_date,end_date,state,"d","s")
        f_cost=self._filters(start_date,end_date,state,"d","s")

        generation=self.query(f"""
            SELECT g.generationid, g.datekey, CAST(d.date AS DATE) AS date,
                   g.plantkey, g.statekey, s.statename, g.sourcekey,
                   es.sourcename AS energysource, g.generation_mwh,
                   g.targetgeneration_mwh, g.capacityutilizationpct,
                   g.curtailment_mwh, g.unplannedoutagehours
            FROM {q}.fact_generation g
            LEFT JOIN {q}.dim_date d ON g.datekey=d.datekey
            LEFT JOIN {q}.dim_state s ON g.statekey=s.statekey
            LEFT JOIN {q}.dim_energy_source es ON g.sourcekey=es.sourcekey
            WHERE 1=1 {f_gen}
        """)
        consumption=self.query(f"""
            SELECT c.consumptionid, c.datekey, CAST(d.date AS DATE) AS date,
                   c.statekey, COALESCE(c.statename,s.statename) AS statename,
                   c.consumersector, c.consumption_mwh, c.targetconsumption_mwh,
                   c.variancepct, c.peakdemandmw
            FROM {q}.fact_consumption c
            LEFT JOIN {q}.dim_date d ON c.datekey=d.datekey
            LEFT JOIN {q}.dim_state s ON c.statekey=s.statekey
            WHERE 1=1 {f_cons}
        """)
        grid=self.query(f"""
            SELECT gp.gridrecordid, gp.datekey, CAST(d.date AS DATE) AS date,
                   gp.statekey, COALESCE(gp.statename,s.statename) AS statename,
                   gp.gridavailabilitypct, gp.transmissionlosspct,
                   gp.outagecount, gp.saidi_hours, gp.peakloadfactorpct
            FROM {q}.fact_grid_performance gp
            LEFT JOIN {q}.dim_date d ON gp.datekey=d.datekey
            LEFT JOIN {q}.dim_state s ON gp.statekey=s.statekey
            WHERE 1=1 {f_grid}
        """)
        capacity=self.query(f"SELECT plantkey, installedcapacitymw FROM {q}.dim_power_plant WHERE plantstatus IS NULL OR LOWER(plantstatus) NOT IN ('retired','decommissioned')")
        emissions=self.query(f"""
            SELECT e.emissionrecordid,e.datekey,CAST(d.date AS DATE) AS date,e.statekey,
                   COALESCE(e.energysource,es.sourcename) AS energysource,
                   e.energygenerated_mwh,e.emissionfactor_tco2e_per_mwh,
                   e.emissions_tco2e,e.carbonreductiontargetpct
            FROM {q}.fact_carbon_emissions e
            LEFT JOIN {q}.dim_date d ON e.datekey=d.datekey
            LEFT JOIN {q}.dim_state s ON e.statekey=s.statekey
            LEFT JOIN {q}.dim_energy_source es ON e.sourcekey=es.sourcekey
            WHERE 1=1 {f_em}
        """)
        costs=self.query(f"""
            SELECT c.costrecordid,c.datekey,CAST(d.date AS DATE) AS date,c.statekey,
                   COALESCE(c.energysource,es.sourcename) AS energysource,
                   c.energypurchased_mwh,c.unitcost_inr_per_mwh,c.totalcost_inr,
                   c.revenue_inr,c.grossmargin_inr,c.currency
            FROM {q}.fact_energy_cost c
            LEFT JOIN {q}.dim_date d ON c.datekey=d.datekey
            LEFT JOIN {q}.dim_state s ON c.statekey=s.statekey
            LEFT JOIN {q}.dim_energy_source es ON c.sourcekey=es.sourcekey
            WHERE 1=1 {f_cost}
        """)
        # Aggregate trends after loading filtered fact records. The fact date is joined using datekey.
        trend_gen = generation.groupby("date",as_index=False)["generation_mwh"].sum() if not generation.empty else pd.DataFrame(columns=["date","generation_mwh"])
        trend_cons = consumption.groupby("date",as_index=False)["consumption_mwh"].sum() if not consumption.empty else pd.DataFrame(columns=["date","consumption_mwh"])
        trend = trend_gen.merge(trend_cons,on="date",how="outer").sort_values("date").fillna(0)
        by_source = generation.groupby("energysource",as_index=False)["generation_mwh"].sum() if not generation.empty else pd.DataFrame()
        by_state = generation.groupby(["statekey","statename"],as_index=False)["generation_mwh"].sum() if not generation.empty else pd.DataFrame()
        if not by_state.empty:
            coords=self.query(f"SELECT statekey,latitude,longitude FROM {q}.dim_state")
            by_state=by_state.merge(coords,on="statekey",how="left")
        grid_by_state=grid.groupby("statename",as_index=False)["gridavailabilitypct"].mean() if not grid.empty else pd.DataFrame()
        return {
            "generation":generation,"consumption":consumption,"grid":grid,
            "capacity":capacity,"emissions":emissions,"costs":costs,
            "trend":trend,"by_source":by_source,"by_state":by_state,
            "grid_by_state":grid_by_state,"recent_generation":generation.sort_values("date",ascending=False).head(100) if not generation.empty else generation
        }

    def generation_data(self,start_date,end_date,state):
        q=self.qschema
        f=self._filters(start_date,end_date,state,"d","s")
        return self.query(f"""
            SELECT g.generationid,g.datekey,CAST(d.date AS DATE) AS date,
                   g.plantkey,p.plantname,g.statekey,s.statename,g.sourcekey,
                   es.sourcename AS energysource,g.generation_mwh,g.targetgeneration_mwh,
                   g.capacityutilizationpct,g.curtailment_mwh,g.unplannedoutagehours
            FROM {q}.fact_generation g
            LEFT JOIN {q}.dim_date d ON g.datekey=d.datekey
            LEFT JOIN {q}.dim_power_plant p ON g.plantkey=p.plantkey
            LEFT JOIN {q}.dim_state s ON g.statekey=s.statekey
            LEFT JOIN {q}.dim_energy_source es ON g.sourcekey=es.sourcekey
            WHERE 1=1 {f}
        """)

    def consumption_data(self,start_date,end_date,state):
        q=self.qschema; f=self._filters(start_date,end_date,state,"d","s")
        return self.query(f"""
            SELECT c.consumptionid,c.datekey,CAST(d.date AS DATE) AS date,c.statekey,
                   COALESCE(c.statename,s.statename) AS statename,c.consumersector,
                   c.consumption_mwh,c.targetconsumption_mwh,c.variancepct,c.peakdemandmw
            FROM {q}.fact_consumption c
            LEFT JOIN {q}.dim_date d ON c.datekey=d.datekey
            LEFT JOIN {q}.dim_state s ON c.statekey=s.statekey
            WHERE 1=1 {f}
        """)

    def grid_data(self,start_date,end_date,state):
        q=self.qschema; f=self._filters(start_date,end_date,state,"d","s")
        return self.query(f"""
            SELECT gp.gridrecordid,gp.datekey,CAST(d.date AS DATE) AS date,gp.statekey,
                   COALESCE(gp.statename,s.statename) AS statename,gp.gridavailabilitypct,
                   gp.transmissionlosspct,gp.outagecount,gp.saidi_hours,gp.peakloadfactorpct
            FROM {q}.fact_grid_performance gp
            LEFT JOIN {q}.dim_date d ON gp.datekey=d.datekey
            LEFT JOIN {q}.dim_state s ON gp.statekey=s.statekey
            WHERE 1=1 {f}
        """)

    def asset_data(self,start_date,end_date,state):
        q=self.qschema; f=self._filters(start_date,end_date,state,"d","s")
        return self.query(f"""
            SELECT ap.assetperformanceid,ap.datekey,CAST(d.date AS DATE) AS date,
                   ap.assetkey,a.assetname,a.assettype,a.criticality,
                   ap.plantkey,p.plantname,ap.statekey,s.statename,
                   ap.availabilitypct,ap.assethealthscore,ap.downtimehours,
                   ap.maintenanceevents,ap.operationalstatus
            FROM {q}.fact_asset_performance ap
            LEFT JOIN {q}.dim_date d ON ap.datekey=d.datekey
            LEFT JOIN {q}.dim_asset a ON ap.assetkey=a.assetkey
            LEFT JOIN {q}.dim_power_plant p ON ap.plantkey=p.plantkey
            LEFT JOIN {q}.dim_state s ON ap.statekey=s.statekey
            WHERE 1=1 {f}
        """)

    def sustainability_data(self,start_date,end_date,state):
        q=self.qschema; f=self._filters(start_date,end_date,state,"d","s")
        return self.query(f"""
            SELECT e.emissionrecordid,e.datekey,CAST(d.date AS DATE) AS date,e.statekey,
                   COALESCE(e.energysource,es.sourcename) AS energysource,
                   e.energygenerated_mwh,e.emissionfactor_tco2e_per_mwh,
                   e.emissions_tco2e,e.carbonreductiontargetpct
            FROM {q}.fact_carbon_emissions e
            LEFT JOIN {q}.dim_date d ON e.datekey=d.datekey
            LEFT JOIN {q}.dim_state s ON e.statekey=s.statekey
            LEFT JOIN {q}.dim_energy_source es ON e.sourcekey=es.sourcekey
            WHERE 1=1 {f}
        """)

    def cost_data(self,start_date,end_date,state):
        q=self.qschema; f=self._filters(start_date,end_date,state,"d","s")
        return self.query(f"""
            SELECT c.costrecordid,c.datekey,CAST(d.date AS DATE) AS date,c.statekey,
                   COALESCE(c.energysource,es.sourcename) AS energysource,
                   c.energypurchased_mwh,c.unitcost_inr_per_mwh,c.totalcost_inr,
                   c.revenue_inr,c.grossmargin_inr,c.currency
            FROM {q}.fact_energy_cost c
            LEFT JOIN {q}.dim_date d ON c.datekey=d.datekey
            LEFT JOIN {q}.dim_state s ON c.statekey=s.statekey
            LEFT JOIN {q}.dim_energy_source es ON c.sourcekey=es.sourcekey
            WHERE 1=1 {f}
        """)

    def state_data(self,start_date,end_date):
        q=self.qschema
        gen=self.query(f"""
            SELECT statekey,SUM(generation_mwh) AS generation_mwh
            FROM {q}.fact_generation g
            LEFT JOIN {q}.dim_date d ON g.datekey=d.datekey
            WHERE 1=1 {self._date_filter(start_date,end_date,"d")}
            GROUP BY statekey
        """)
        cons=self.query(f"""
            SELECT statekey,SUM(consumption_mwh) AS consumption_mwh
            FROM {q}.fact_consumption c
            LEFT JOIN {q}.dim_date d ON c.datekey=d.datekey
            WHERE 1=1 {self._date_filter(start_date,end_date,"d")}
            GROUP BY statekey
        """)
        grid=self.query(f"""
            SELECT statekey,AVG(gridavailabilitypct) AS gridavailabilitypct
            FROM {q}.fact_grid_performance gp
            LEFT JOIN {q}.dim_date d ON gp.datekey=d.datekey
            WHERE 1=1 {self._date_filter(start_date,end_date,"d")}
            GROUP BY statekey
        """)
        states=self.query(f"SELECT statekey,statename,region,statecode,latitude,longitude FROM {q}.dim_state")
        return states.merge(gen,on="statekey",how="left").merge(cons,on="statekey",how="left").merge(grid,on="statekey",how="left").fillna(0)

    # ---------------- Property-centric Energy 360 module ----------------
    @staticmethod
    def _sql_string(value):
        return "'" + str(value).replace("'", "''") + "'"

    def property_list(self):
        q=self.qschema
        return self.query(f"""
            SELECT property_id,property_code,property_name,property_type,ownership_type,
                   address_line_1,address_line_2,city,county,state_code,state_name,
                   postal_code,country_code,country_name,timezone,latitude,longitude,
                   gross_area_sqft,rentable_area_sqft,year_built,operating_status,
                   acquisition_date,disposition_date,property_manager
            FROM {q}.dim_property
            WHERE operating_status IS NULL OR LOWER(operating_status) NOT IN ('disposed','inactive')
            ORDER BY property_name
        """)

    def property_energy_data(self,property_id):
        q=self.qschema; pid=self._sql_string(property_id)
        return self.query(f"""
            SELECT u.property_energy_usage_id,u.property_id,u.meter_id,m.meter_number,
                   u.utility_account_id,u.commodity_id,c.commodity_name,c.base_unit,
                   u.vendor_id,v.vendor_name,u.contract_id,u.rate_schedule_id,
                   u.period_start_date,u.period_end_date,u.usage_quantity,u.usage_unit,
                   u.peak_demand_quantity,u.peak_demand_unit,u.load_factor_pct,
                   u.cost_amount,u.currency_code,u.emissions_kg_co2e,u.is_estimated,u.source_system
            FROM {q}.fact_property_energy_usage u
            LEFT JOIN {q}.dim_commodity c ON u.commodity_id=c.commodity_id
            LEFT JOIN {q}.dim_meter m ON u.meter_id=m.meter_id
            LEFT JOIN {q}.dim_vendor v ON u.vendor_id=v.vendor_id
            WHERE u.property_id={pid}
            ORDER BY u.period_start_date,c.commodity_name,m.meter_number
        """)

    def property_meter_data(self,property_id):
        q=self.qschema; pid=self._sql_string(property_id)
        return self.query(f"""
            SELECT m.meter_id,m.meter_number,m.meter_name,c.commodity_name,m.meter_type,
                   m.meter_role,m.unit_of_measure,m.meter_manufacturer,m.meter_model,
                   m.meter_serial_number,m.installation_date,m.interval_minutes,
                   m.is_smart_meter,m.meter_status,m.parent_meter_id,m.tenant_space,
                   m.floor_or_area,a.account_number,v.vendor_name
            FROM {q}.dim_meter m
            LEFT JOIN {q}.dim_commodity c ON m.commodity_id=c.commodity_id
            LEFT JOIN {q}.dim_utility_account a ON m.utility_account_id=a.utility_account_id
            LEFT JOIN {q}.dim_vendor v ON a.utility_vendor_id=v.vendor_id
            WHERE m.property_id={pid}
            ORDER BY c.commodity_name,m.meter_number
        """)

    def property_account_data(self,property_id):
        q=self.qschema; pid=self._sql_string(property_id)
        return self.query(f"""
            SELECT a.utility_account_id,a.account_number,a.account_name,c.commodity_name,
                   v.vendor_name,r.rate_class_code,r.rate_class_name,a.account_open_date,
                   a.account_close_date,a.account_status,a.payment_method,a.payment_terms,
                   a.currency_code,a.cost_center,a.general_ledger_account,
                   a.billing_address,a.billing_city,a.billing_state,a.billing_postal_code
            FROM {q}.dim_utility_account a
            LEFT JOIN {q}.dim_commodity c ON a.commodity_id=c.commodity_id
            LEFT JOIN {q}.dim_vendor v ON a.utility_vendor_id=v.vendor_id
            LEFT JOIN {q}.dim_rate_class r ON a.rate_class_id=r.rate_class_id
            WHERE a.property_id={pid}
            ORDER BY c.commodity_name,a.account_number
        """)

    def property_vendor_data(self,property_id):
        q=self.qschema; pid=self._sql_string(property_id)
        return self.query(f"""
            SELECT DISTINCT v.vendor_id,v.vendor_code,v.vendor_name,v.vendor_type,
                   v.contact_name,v.contact_email,v.contact_phone,v.website,
                   v.payment_terms,v.vendor_status
            FROM {q}.dim_vendor v
            WHERE v.vendor_id IN (
                SELECT utility_vendor_id FROM {q}.dim_utility_account WHERE property_id={pid}
                UNION
                SELECT c.supplier_vendor_id FROM {q}.bridge_property_contract b
                JOIN {q}.dim_contract c ON b.contract_id=c.contract_id
                WHERE b.property_id={pid}
                UNION
                SELECT po.vendor_id FROM {q}.fact_purchase_order po WHERE po.property_id={pid}
            )
            ORDER BY v.vendor_name
        """)

    def property_rate_data(self,property_id):
        q=self.qschema; pid=self._sql_string(property_id)
        return self.query(f"""
            SELECT DISTINCT a.account_number,c.commodity_name,v.vendor_name,
                   rc.rate_class_code,rc.rate_class_name,rs.rate_schedule_id,rs.rate_code,
                   rs.rate_name,rs.rate_basis,rs.currency_code,rs.effective_start_date,
                   rs.effective_end_date,rs.rate_status,fc.component_code,fc.component_name,
                   fc.charge_type,fc.calculation_basis,fc.unit_rate,fc.unit_of_measure
            FROM {q}.dim_utility_account a
            JOIN {q}.dim_rate_class rc ON a.rate_class_id=rc.rate_class_id
            JOIN {q}.dim_rate_schedule rs ON rs.rate_class_id=rc.rate_class_id
                                           AND rs.commodity_id=a.commodity_id
            LEFT JOIN {q}.dim_commodity c ON rs.commodity_id=c.commodity_id
            LEFT JOIN {q}.dim_vendor v ON rs.utility_vendor_id=v.vendor_id
            LEFT JOIN {q}.fact_rate_component fc ON rs.rate_schedule_id=fc.rate_schedule_id
            WHERE a.property_id={pid}
            ORDER BY c.commodity_name,rs.rate_code,fc.component_code
        """)

    def property_contract_data(self,property_id):
        q=self.qschema; pid=self._sql_string(property_id)
        return self.query(f"""
            SELECT c.contract_id,c.contract_number,c.contract_name,c.contract_type,
                   supplier.vendor_name AS supplier_name,broker.vendor_name AS broker_name,
                   co.commodity_name,rc.rate_class_code,rs.rate_code,c.contract_start_date,
                   c.contract_end_date,c.auto_renewal_flag,c.renewal_notice_days,
                   c.termination_notice_days,c.pricing_type,c.currency_code,
                   c.estimated_annual_volume,c.volume_unit,c.estimated_annual_value,
                   c.payment_terms,c.contract_status,b.allocation_pct,
                   b.effective_start_date AS property_start_date,
                   b.effective_end_date AS property_end_date,
                   datediff(coalesce(b.effective_end_date,c.contract_end_date),
                            coalesce(b.effective_start_date,c.contract_start_date))+1 AS contract_duration_days,
                   datediff(coalesce(b.effective_end_date,c.contract_end_date),current_date()) AS days_remaining,
                   CASE
                     WHEN coalesce(b.effective_start_date,c.contract_start_date) > current_date() THEN 'Upcoming'
                     WHEN coalesce(b.effective_end_date,c.contract_end_date) < current_date() THEN 'Expired'
                     WHEN datediff(coalesce(b.effective_end_date,c.contract_end_date),current_date()) <= 90 THEN 'Expiring Soon'
                     ELSE 'Active'
                   END AS duration_status
            FROM {q}.bridge_property_contract b
            JOIN {q}.dim_contract c ON b.contract_id=c.contract_id
            LEFT JOIN {q}.dim_vendor supplier ON c.supplier_vendor_id=supplier.vendor_id
            LEFT JOIN {q}.dim_vendor broker ON c.broker_vendor_id=broker.vendor_id
            LEFT JOIN {q}.dim_commodity co ON c.commodity_id=co.commodity_id
            LEFT JOIN {q}.dim_rate_class rc ON c.rate_class_id=rc.rate_class_id
            LEFT JOIN {q}.dim_rate_schedule rs ON c.rate_schedule_id=rs.rate_schedule_id
            WHERE b.property_id={pid}
            ORDER BY c.contract_end_date
        """)

    def all_contracts_data(self):
        q=self.qschema
        return self.query(f"""
            WITH contract_links AS (
                SELECT b.contract_id,p.property_name,
                       'Property' AS linked_to,
                       CAST(NULL AS STRING) AS meter_number,
                       coalesce(b.effective_start_date,c.contract_start_date) AS start_date,
                       coalesce(b.effective_end_date,c.contract_end_date) AS end_date
                FROM {q}.bridge_property_contract b
                JOIN {q}.dim_property p ON b.property_id=p.property_id
                JOIN {q}.dim_contract c ON b.contract_id=c.contract_id

                UNION ALL

                SELECT b.contract_id,p.property_name,
                       'Meter' AS linked_to,
                       CAST(m.meter_number AS STRING) AS meter_number,
                       coalesce(b.effective_start_date,c.contract_start_date) AS start_date,
                       coalesce(b.effective_end_date,c.contract_end_date) AS end_date
                FROM {q}.bridge_meter_contract b
                JOIN {q}.dim_property p ON b.property_id=p.property_id
                JOIN {q}.dim_meter m ON b.meter_id=m.meter_id
                JOIN {q}.dim_contract c ON b.contract_id=c.contract_id
            )
            SELECT c.contract_id,c.contract_number,c.contract_name,
                   v.vendor_name AS supplier_name,co.commodity_name,
                   coalesce(ls.property_name,'Not Assigned') AS property_name,
                   CASE
                     WHEN ls.linked_to='Meter' THEN concat('Meter: ',coalesce(ls.meter_number,''))
                     ELSE coalesce(ls.linked_to,'Not Assigned')
                   END AS linked_to,
                   coalesce(ls.start_date,c.contract_start_date) AS contract_start_date,
                   coalesce(ls.end_date,c.contract_end_date) AS contract_end_date,
                   datediff(coalesce(ls.end_date,c.contract_end_date),
                            coalesce(ls.start_date,c.contract_start_date)) AS contract_duration_days,
                   datediff(coalesce(ls.end_date,c.contract_end_date),current_date()) AS days_remaining,
                   c.auto_renewal_flag,c.renewal_notice_days,c.contract_status,c.currency_code,
                   c.estimated_annual_value
            FROM {q}.dim_contract c
            LEFT JOIN contract_links ls ON c.contract_id=ls.contract_id
            LEFT JOIN {q}.dim_vendor v ON c.supplier_vendor_id=v.vendor_id
            LEFT JOIN {q}.dim_commodity co ON c.commodity_id=co.commodity_id
            ORDER BY days_remaining ASC NULLS LAST,c.contract_number,property_name,linked_to
        """)

    def contract_management_options(self):
        q=self.qschema
        vendors=self.query(f"""
            SELECT vendor_id,vendor_name FROM {q}.dim_vendor
            WHERE vendor_status IS NULL OR LOWER(vendor_status) NOT IN ('inactive','terminated')
            ORDER BY vendor_name
        """)
        commodities=self.query(f"""
            SELECT commodity_id,commodity_name FROM {q}.dim_commodity
            WHERE is_active IS NULL OR is_active = TRUE
            ORDER BY commodity_name
        """)
        return vendors, commodities

    def contract_management_data(self,property_id,scope):
        q=self.qschema; pid=self._sql_string(property_id)
        if scope == "Property":
            return self.query(f"""
                SELECT b.property_contract_id AS link_id,'Property' AS contract_scope,
                       p.property_name,NULL AS meter_id,NULL AS meter_number,
                       c.contract_id,c.contract_number,c.contract_name,
                       v.vendor_name AS supplier_name,co.commodity_name,
                       b.effective_start_date AS contract_start_date,
                       coalesce(b.effective_end_date,c.contract_end_date) AS contract_end_date,
                       datediff(coalesce(b.effective_end_date,c.contract_end_date),current_date()) AS days_remaining,
                       c.auto_renewal_flag,c.renewal_notice_days,c.contract_status
                FROM {q}.bridge_property_contract b
                JOIN {q}.dim_property p ON b.property_id=p.property_id
                JOIN {q}.dim_contract c ON b.contract_id=c.contract_id
                LEFT JOIN {q}.dim_vendor v ON c.supplier_vendor_id=v.vendor_id
                LEFT JOIN {q}.dim_commodity co ON c.commodity_id=co.commodity_id
                WHERE b.property_id={pid}
                ORDER BY contract_end_date
            """)
        return self.query(f"""
            SELECT b.meter_contract_id AS link_id,'Meter' AS contract_scope,
                   p.property_name,m.meter_id,m.meter_number,
                   c.contract_id,c.contract_number,c.contract_name,
                   v.vendor_name AS supplier_name,co.commodity_name,
                   b.effective_start_date AS contract_start_date,
                   b.effective_end_date AS contract_end_date,
                   datediff(b.effective_end_date,current_date()) AS days_remaining,
                   c.auto_renewal_flag,c.renewal_notice_days,c.contract_status
            FROM {q}.bridge_meter_contract b
            JOIN {q}.dim_property p ON b.property_id=p.property_id
            JOIN {q}.dim_meter m ON b.meter_id=m.meter_id
            JOIN {q}.dim_contract c ON b.contract_id=c.contract_id
            LEFT JOIN {q}.dim_vendor v ON c.supplier_vendor_id=v.vendor_id
            LEFT JOIN {q}.dim_commodity co ON m.commodity_id=co.commodity_id
            WHERE b.property_id={pid}
            ORDER BY contract_end_date,m.meter_number
        """)

    def property_contract_end_date_for_meter(self,link_id):
        q=self.qschema; lid=self._sql_string(link_id)
        result=self.query(f"""
            SELECT max(pb.effective_end_date) AS property_contract_end_date
            FROM {q}.bridge_meter_contract mb
            JOIN {q}.dim_meter m ON mb.meter_id=m.meter_id
            JOIN {q}.bridge_property_contract pb
              ON pb.property_id=mb.property_id
            JOIN {q}.dim_contract pc ON pc.contract_id=pb.contract_id
            JOIN {q}.dim_contract mc ON mc.contract_id=mb.contract_id
            WHERE mb.meter_contract_id={lid}
              AND pc.commodity_id=m.commodity_id
              AND mc.commodity_id=m.commodity_id
        """)
        if result.empty or pd.isna(result.iloc[0]["property_contract_end_date"]):
            return None
        return pd.to_datetime(result.iloc[0]["property_contract_end_date"]).date()

    def update_contract_link(self,scope,link_id,contract_number,contract_name,start_date,end_date):
        q=self.qschema; lid=self._sql_string(link_id)
        number=self._sql_string(contract_number); name=self._sql_string(contract_name)
        start=self._sql_string(str(start_date)); end=self._sql_string(str(end_date))
        if end_date < start_date:
            raise DataAccessError("Contract end date cannot be earlier than its start date.")
        table="bridge_property_contract" if scope == "Property" else "bridge_meter_contract"
        key="property_contract_id" if scope == "Property" else "meter_contract_id"
        # Dates are stored on the relationship; descriptive contract fields are
        # stored once on dim_contract and therefore update consistently in all views.
        self.execute(f"""
            UPDATE {q}.dim_contract
            SET contract_number={number}, contract_name={name},
                contract_start_date=CAST({start} AS DATE),
                contract_end_date=CAST({end} AS DATE),
                updated_at=current_timestamp()
            WHERE contract_id=(
                SELECT contract_id FROM {q}.{table} WHERE {key}={lid}
            )
        """)
        self.execute(f"""
            UPDATE {q}.{table}
            SET effective_start_date=CAST({start} AS DATE),
                effective_end_date=CAST({end} AS DATE)
            WHERE {key}={lid}
        """)

    def delete_contract_link(self,scope,link_id):
        q=self.qschema; lid=self._sql_string(link_id)
        table="bridge_property_contract" if scope == "Property" else "bridge_meter_contract"
        key="property_contract_id" if scope == "Property" else "meter_contract_id"
        result=self.query(f"SELECT contract_id FROM {q}.{table} WHERE {key}={lid}")
        if result.empty:
            raise DataAccessError("The selected contract link no longer exists.")
        contract_id=self._sql_string(result.iloc[0]["contract_id"])
        self.execute(f"DELETE FROM {q}.{table} WHERE {key}={lid}")
        self.execute(f"""
            DELETE FROM {q}.dim_contract
            WHERE contract_id={contract_id}
              AND NOT EXISTS (SELECT 1 FROM {q}.bridge_property_contract WHERE contract_id={contract_id})
              AND NOT EXISTS (SELECT 1 FROM {q}.bridge_meter_contract WHERE contract_id={contract_id})
        """)


    def create_contract_link(self,scope,property_id,meter_id,contract_number,contract_name,
                             supplier_vendor_id,commodity_id,start_date,end_date,currency_code,
                             auto_renewal,renewal_notice_days):
        import uuid
        q=self.qschema
        contract_id="CON-"+uuid.uuid4().hex[:16].upper()
        link_id=("PC-" if scope == "Property" else "MC-")+uuid.uuid4().hex[:16].upper()
        vals=[contract_id,contract_number,contract_name,supplier_vendor_id,commodity_id,
              str(start_date),str(end_date),currency_code]
        s=[self._sql_string(v) for v in vals]
        renewal="TRUE" if auto_renewal else "FALSE"
        notice=int(renewal_notice_days)
        self.execute(f"""
            INSERT INTO {q}.dim_contract
            (contract_id,contract_number,contract_name,supplier_vendor_id,commodity_id,
             contract_type,contract_start_date,contract_end_date,auto_renewal_flag,
             renewal_notice_days,currency_code,contract_status,created_at,updated_at)
            VALUES ({s[0]},{s[1]},{s[2]},{s[3]},{s[4]},'Utility Supply',
                    CAST({s[5]} AS DATE),CAST({s[6]} AS DATE),{renewal},{notice},
                    {s[7]},'Active',current_timestamp(),current_timestamp())
        """)
        if scope == "Property":
            self.execute(f"""
                INSERT INTO {q}.bridge_property_contract
                (property_contract_id,property_id,contract_id,allocation_pct,
                 effective_start_date,effective_end_date,created_at)
                VALUES ({self._sql_string(link_id)},{self._sql_string(property_id)},
                        {self._sql_string(contract_id)},100.0000,
                        CAST({s[5]} AS DATE),CAST({s[6]} AS DATE),current_timestamp())
            """)
        else:
            self.execute(f"""
                INSERT INTO {q}.bridge_meter_contract
                (meter_contract_id,property_id,meter_id,contract_id,
                 effective_start_date,effective_end_date,allocation_pct,created_at)
                VALUES ({self._sql_string(link_id)},{self._sql_string(property_id)},
                        {self._sql_string(meter_id)},{self._sql_string(contract_id)},
                        CAST({s[5]} AS DATE),CAST({s[6]} AS DATE),100.0000,current_timestamp())
            """)
        return contract_id

    def property_bill_data(self,property_id):
        q=self.qschema; pid=self._sql_string(property_id)
        return self.query(f"""
            SELECT b.energy_bill_id,b.bill_number,a.account_number,v.vendor_name,
                   b.bill_period_start,b.bill_period_end,b.invoice_date,b.due_date,
                   b.total_usage_quantity,b.usage_unit,b.subtotal_amount,b.tax_amount,
                   b.total_amount,b.currency_code,b.amount_paid,b.balance_amount,
                   b.payment_status,b.bill_status
            FROM {q}.fact_energy_bill b
            LEFT JOIN {q}.dim_utility_account a ON b.utility_account_id=a.utility_account_id
            LEFT JOIN {q}.dim_vendor v ON b.vendor_id=v.vendor_id
            WHERE b.property_id={pid}
            ORDER BY b.invoice_date DESC
        """)

    def property_procurement_data(self,property_id):
        q=self.qschema; pid=self._sql_string(property_id)
        return self.query(f"""
            SELECT po.purchase_order_number,po.order_date,po.requested_delivery_date,
                   v.vendor_name,c.contract_number,po.department,po.cost_center,
                   po.currency_code,po.subtotal_amount,po.tax_amount,po.total_amount,
                   po.approval_status,po.purchase_order_status,po.description,
                   vi.vendor_invoice_number,vi.invoice_date,vi.due_date,
                   vi.invoice_status,vi.approval_status AS invoice_approval_status,
                   vi.total_amount AS invoice_total,
                   pay.payment_date,pay.payment_reference,pay.payment_amount,pay.payment_status
            FROM {q}.fact_purchase_order po
            LEFT JOIN {q}.dim_vendor v ON po.vendor_id=v.vendor_id
            LEFT JOIN {q}.dim_contract c ON po.contract_id=c.contract_id
            LEFT JOIN {q}.fact_vendor_invoice vi ON po.purchase_order_id=vi.purchase_order_id
            LEFT JOIN {q}.fact_vendor_payment pay ON vi.vendor_invoice_id=pay.vendor_invoice_id
            WHERE po.property_id={pid}
            ORDER BY po.order_date DESC
        """)



    # Relationship-aware CRUD for property operations. Logical foreign keys are
    # validated here because Delta Lake does not enforce conventional FK constraints.
    CRUD_TABLES = {
        "meters": ("dim_meter", "meter_id"),
        "meter_readings": ("fact_meter_reading", "meter_reading_id"),
        "meter_contracts": ("bridge_meter_contract", "meter_contract_id"),
        "accounts": ("dim_utility_account", "utility_account_id"),
        "vendors": ("dim_vendor", "vendor_id"),
        "rate_classes": ("dim_rate_class", "rate_class_id"),
        "rate_schedules": ("dim_rate_schedule", "rate_schedule_id"),
        "rate_components": ("fact_rate_component", "rate_component_id"),
        "property_contracts": ("bridge_property_contract", "property_contract_id"),
        "bills": ("fact_energy_bill", "energy_bill_id"),
        "bill_lines": ("fact_energy_bill_line", "energy_bill_line_id"),
        "purchase_orders": ("fact_purchase_order", "purchase_order_id"),
        "purchase_order_lines": ("fact_purchase_order_line", "purchase_order_line_id"),
        "vendor_invoices": ("fact_vendor_invoice", "vendor_invoice_id"),
        "vendor_invoice_lines": ("fact_vendor_invoice_line", "vendor_invoice_line_id"),
        "vendor_payments": ("fact_vendor_payment", "vendor_payment_id"),
    }

    CRUD_RELATIONSHIPS = {
        "dim_vendor": {
            "parent_vendor_id": ("dim_vendor", "vendor_id", "vendor_name"),
        },
        "dim_meter": {
            "property_id": ("dim_property", "property_id", "property_name"),
            "property_service_id": ("bridge_property_commodity_service", "property_service_id", "service_location_code"),
            "utility_account_id": ("dim_utility_account", "utility_account_id", "account_number"),
            "commodity_id": ("dim_commodity", "commodity_id", "commodity_name"),
            "parent_meter_id": ("dim_meter", "meter_id", "meter_number"),
        },
        "fact_meter_reading": {
            "property_id": ("dim_property", "property_id", "property_name"),
            "meter_id": ("dim_meter", "meter_id", "meter_number"),
            "utility_account_id": ("dim_utility_account", "utility_account_id", "account_number"),
            "commodity_id": ("dim_commodity", "commodity_id", "commodity_name"),
        },
        "bridge_meter_contract": {
            "property_id": ("dim_property", "property_id", "property_name"),
            "meter_id": ("dim_meter", "meter_id", "meter_number"),
            "contract_id": ("dim_contract", "contract_id", "contract_number"),
        },
        "dim_utility_account": {
            "property_id": ("dim_property", "property_id", "property_name"),
            "property_service_id": ("bridge_property_commodity_service", "property_service_id", "service_location_code"),
            "commodity_id": ("dim_commodity", "commodity_id", "commodity_name"),
            "utility_vendor_id": ("dim_vendor", "vendor_id", "vendor_name"),
            "rate_class_id": ("dim_rate_class", "rate_class_id", "rate_class_name"),
        },
        "dim_rate_class": {
            "utility_vendor_id": ("dim_vendor", "vendor_id", "vendor_name"),
            "commodity_id": ("dim_commodity", "commodity_id", "commodity_name"),
        },
        "dim_rate_schedule": {
            "rate_class_id": ("dim_rate_class", "rate_class_id", "rate_class_name"),
            "utility_vendor_id": ("dim_vendor", "vendor_id", "vendor_name"),
            "commodity_id": ("dim_commodity", "commodity_id", "commodity_name"),
            "contract_id": ("dim_contract", "contract_id", "contract_number"),
        },
        "fact_rate_component": {
            "rate_schedule_id": ("dim_rate_schedule", "rate_schedule_id", "rate_code"),
        },
        "bridge_property_contract": {
            "property_id": ("dim_property", "property_id", "property_name"),
            "contract_id": ("dim_contract", "contract_id", "contract_number"),
            "property_service_id": ("bridge_property_commodity_service", "property_service_id", "service_location_code"),
        },
        "fact_energy_bill": {
            "property_id": ("dim_property", "property_id", "property_name"),
            "utility_account_id": ("dim_utility_account", "utility_account_id", "account_number"),
            "vendor_id": ("dim_vendor", "vendor_id", "vendor_name"),
            "contract_id": ("dim_contract", "contract_id", "contract_number"),
        },
        "fact_energy_bill_line": {
            "energy_bill_id": ("fact_energy_bill", "energy_bill_id", "bill_number"),
            "property_id": ("dim_property", "property_id", "property_name"),
            "meter_id": ("dim_meter", "meter_id", "meter_number"),
            "commodity_id": ("dim_commodity", "commodity_id", "commodity_name"),
            "rate_schedule_id": ("dim_rate_schedule", "rate_schedule_id", "rate_code"),
            "rate_component_id": ("fact_rate_component", "rate_component_id", "component_name"),
        },
        "fact_purchase_order": {
            "property_id": ("dim_property", "property_id", "property_name"),
            "vendor_id": ("dim_vendor", "vendor_id", "vendor_name"),
            "contract_id": ("dim_contract", "contract_id", "contract_number"),
        },
        "fact_purchase_order_line": {
            "purchase_order_id": ("fact_purchase_order", "purchase_order_id", "purchase_order_number"),
            "property_id": ("dim_property", "property_id", "property_name"),
            "commodity_id": ("dim_commodity", "commodity_id", "commodity_name"),
            "meter_id": ("dim_meter", "meter_id", "meter_number"),
        },
        "fact_vendor_invoice": {
            "vendor_id": ("dim_vendor", "vendor_id", "vendor_name"),
            "property_id": ("dim_property", "property_id", "property_name"),
            "contract_id": ("dim_contract", "contract_id", "contract_number"),
            "purchase_order_id": ("fact_purchase_order", "purchase_order_id", "purchase_order_number"),
        },
        "fact_vendor_invoice_line": {
            "vendor_invoice_id": ("fact_vendor_invoice", "vendor_invoice_id", "vendor_invoice_number"),
            "purchase_order_line_id": ("fact_purchase_order_line", "purchase_order_line_id", "item_description"),
            "property_id": ("dim_property", "property_id", "property_name"),
            "commodity_id": ("dim_commodity", "commodity_id", "commodity_name"),
        },
        "fact_vendor_payment": {
            "vendor_invoice_id": ("fact_vendor_invoice", "vendor_invoice_id", "vendor_invoice_number"),
            "vendor_id": ("dim_vendor", "vendor_id", "vendor_name"),
            "property_id": ("dim_property", "property_id", "property_name"),
        },
    }

    CRUD_UNIQUE_COLUMNS = {
        "dim_vendor": ["vendor_code"],
        "fact_purchase_order": ["purchase_order_number"],
    }

    CRUD_CHILDREN = {
        "dim_property": [("dim_meter","property_id"),("dim_utility_account","property_id"),
            ("bridge_property_contract","property_id"),("bridge_meter_contract","property_id"),
            ("fact_meter_reading","property_id"),("fact_property_energy_usage","property_id"),
            ("fact_energy_bill","property_id"),("fact_energy_bill_line","property_id"),
            ("fact_purchase_order","property_id"),("fact_purchase_order_line","property_id"),
            ("fact_vendor_invoice","property_id"),("fact_vendor_invoice_line","property_id"),
            ("fact_vendor_payment","property_id")],
        "dim_meter": [("fact_meter_reading","meter_id"),("fact_property_energy_usage","meter_id"),
            ("bridge_meter_contract","meter_id"),("fact_energy_bill_line","meter_id"),
            ("fact_purchase_order_line","meter_id"),("dim_meter","parent_meter_id")],
        "dim_utility_account": [("dim_meter","utility_account_id"),("fact_meter_reading","utility_account_id"),
            ("fact_property_energy_usage","utility_account_id"),("fact_energy_bill","utility_account_id")],
        "dim_vendor": [("dim_vendor","parent_vendor_id"),("bridge_property_commodity_service","utility_vendor_id"),("dim_utility_account","utility_vendor_id"),("dim_rate_class","utility_vendor_id"),
            ("dim_rate_schedule","utility_vendor_id"),("dim_contract","supplier_vendor_id"),
            ("dim_contract","broker_vendor_id"),("fact_energy_bill","vendor_id"),
            ("fact_purchase_order","vendor_id"),("fact_vendor_invoice","vendor_id"),
            ("fact_vendor_payment","vendor_id")],
        "dim_rate_class": [("dim_utility_account","rate_class_id"),("dim_rate_schedule","rate_class_id"),
            ("dim_contract","rate_class_id")],
        "dim_rate_schedule": [("fact_rate_component","rate_schedule_id"),
            ("fact_property_energy_usage","rate_schedule_id"),("fact_energy_bill_line","rate_schedule_id"),
            ("dim_contract","rate_schedule_id")],
        "fact_rate_component": [("fact_energy_bill_line","rate_component_id")],
        "dim_contract": [("bridge_property_contract","contract_id"),("bridge_meter_contract","contract_id"),
            ("fact_property_energy_usage","contract_id"),("fact_energy_bill","contract_id"),
            ("fact_purchase_order","contract_id"),("fact_vendor_invoice","contract_id"),
            ("dim_rate_schedule","contract_id")],
        "fact_energy_bill": [("fact_energy_bill_line","energy_bill_id")],
        "fact_purchase_order": [("fact_purchase_order_line","purchase_order_id"),
            ("fact_vendor_invoice","purchase_order_id")],
        "fact_purchase_order_line": [("fact_vendor_invoice_line","purchase_order_line_id")],
        "fact_vendor_invoice": [("fact_vendor_invoice_line","vendor_invoice_id"),
            ("fact_vendor_payment","vendor_invoice_id")],
    }

    def crud_table(self, entity):
        if entity not in self.CRUD_TABLES:
            raise DataAccessError("This data entity is not enabled for editing.")
        table, key = self.CRUD_TABLES[entity]
        return table, key

    def crud_columns(self, entity):
        table, key = self.crud_table(entity)
        rows = self.query(f"DESCRIBE TABLE {self.qschema}.{table}")
        cols = []
        for _, row in rows.iterrows():
            name = str(row.iloc[0]).strip()
            dtype = str(row.iloc[1]).strip().lower() if len(row) > 1 else ""
            if not name or name.startswith("#") or name.startswith("_"):
                continue
            cols.append({"name": name, "type": dtype})
        if not any(c["name"] == key for c in cols):
            raise DataAccessError(f"Expected key column {key} was not found in {table}.")
        return cols

    def crud_rows(self, entity, property_id=None, limit=1000):
        table, key = self.crud_table(entity)
        where = ""
        if property_id and "property_id" in [c["name"] for c in self.crud_columns(entity)]:
            where = f" WHERE property_id={self._sql_string(property_id)}"
        return self.query(f"SELECT * FROM {self.qschema}.{table}{where} ORDER BY {key} LIMIT {int(limit)}")

    def crud_choices(self, entity, column, property_id=None):
        table, key = self.crud_table(entity)
        relation = self.CRUD_RELATIONSHIPS.get(table, {}).get(column)
        if not relation:
            return []
        parent, parent_key, label = relation
        scope = ""
        if property_id and (parent == "dim_property" or "property_id" in [c["name"] for c in self.crud_columns_for_table(parent)]):
            scope = f" WHERE property_id={self._sql_string(property_id)}"
        df = self.query(f"SELECT {parent_key}, {label} FROM {self.qschema}.{parent}{scope} ORDER BY {label} LIMIT 2000")
        if df.empty:
            return []
        return [(str(row[parent_key]), str(row[label] if pd.notna(row[label]) else row[parent_key]))
                for _, row in df.iterrows()]

    def crud_columns_for_table(self, table):
        if table not in {v[0] for v in self.CRUD_TABLES.values()} and table not in {
            "dim_property","dim_commodity","bridge_property_commodity_service","dim_contract"
        }:
            raise DataAccessError("Relationship lookup table is not enabled.")
        rows = self.query(f"DESCRIBE TABLE {self.qschema}.{table}")
        return [{"name": str(r.iloc[0]).strip(), "type": str(r.iloc[1]).strip().lower()}
                for _, r in rows.iterrows()
                if str(r.iloc[0]).strip() and not str(r.iloc[0]).strip().startswith("#")]

    def _crud_literal(self, value, dtype):
        if value is None or (isinstance(value, float) and pd.isna(value)) or value == "":
            return "NULL"
        if "date" in dtype and "timestamp" not in dtype:
            return f"CAST({self._sql_string(str(value))} AS DATE)"
        if "timestamp" in dtype:
            return f"CAST({self._sql_string(str(value))} AS TIMESTAMP)"
        if any(t in dtype for t in ["int","bigint","smallint","tinyint","decimal","numeric","double","float"]):
            return str(float(value)) if isinstance(value, (int,float,np.number)) else str(value)
        if dtype == "boolean":
            return "TRUE" if bool(value) else "FALSE"
        return self._sql_string(value)

    def crud_save(self, entity, values, record_id=None):
        table, key = self.crud_table(entity)
        cols = self.crud_columns(entity)
        known = {c["name"]: c["type"] for c in cols}
        values = {k:v for k,v in values.items() if k in known and k != key and k not in ("created_at","ingestion_timestamp")}
        if not values:
            raise DataAccessError("No editable values were supplied.")
        for unique_col in self.CRUD_UNIQUE_COLUMNS.get(table, []):
            candidate = values.get(unique_col)
            if candidate not in (None, ""):
                condition = f"{unique_col}={self._crud_literal(candidate, known[unique_col])}"
                if record_id is not None:
                    condition += f" AND {key}<>{self._sql_string(record_id)}"
                duplicate = self.query(f"SELECT COUNT(*) AS n FROM {self.qschema}.{table} WHERE {condition}")
                if int(duplicate.iloc[0]["n"]) > 0:
                    raise DataAccessError(f"{unique_col.replace('_',' ').title()} already exists. Use a unique value.")
        for col, relation in self.CRUD_RELATIONSHIPS.get(table, {}).items():
            if col in values and values[col] not in (None,""):
                parent, parent_key, _ = relation
                found = self.query(f"SELECT COUNT(*) n FROM {self.qschema}.{parent} WHERE {parent_key}={self._crud_literal(values[col],'string')}")
                if int(found.iloc[0]["n"]) == 0:
                    raise DataAccessError(f"Invalid relationship: {col} does not exist in {parent}.")

        # Do not re-parent or re-classify a master record while dependent rows exist.
        if record_id is not None and table in self.CRUD_CHILDREN:
            protected_fields = {"property_id","commodity_id","utility_account_id","rate_class_id",
                                "rate_schedule_id","contract_id","supplier_vendor_id","utility_vendor_id"}
            current = self.query(f"SELECT * FROM {self.qschema}.{table} WHERE {key}={self._sql_string(record_id)}")
            if not current.empty:
                old_row = current.iloc[0]
                for field in protected_fields.intersection(values):
                    old_value, new_value = old_row.get(field), values.get(field)
                    old_text = None if pd.isna(old_value) else str(old_value)
                    new_text = None if new_value in (None,"") else str(new_value)
                    if old_text != new_text:
                        for child, fk in self.CRUD_CHILDREN.get(table, []):
                            child_count = self.query(f"SELECT COUNT(*) AS n FROM {self.qschema}.{child} WHERE {fk}={self._sql_string(record_id)}")
                            if not child_count.empty and int(child_count.iloc[0]["n"]) > 0:
                                raise DataAccessError(f"Cannot change {field} while dependent records exist in {child}. Reassign or remove the dependent records first.")

        # Enforce cross-table consistency in addition to simple FK existence.
        if table == "dim_meter":
            prop = values.get("property_id")
            acct = values.get("utility_account_id")
            commodity = values.get("commodity_id")
            if acct:
                checks = self.query(f"SELECT property_id,commodity_id FROM {self.qschema}.dim_utility_account WHERE utility_account_id={self._sql_string(acct)}")
                if not checks.empty and (str(checks.iloc[0]["property_id"]) != str(prop) or str(checks.iloc[0]["commodity_id"]) != str(commodity)):
                    raise DataAccessError("The selected utility account must belong to the same property and commodity as the meter.")
        elif table == "fact_meter_reading":
            meter = values.get("meter_id")
            if meter:
                checks = self.query(f"SELECT property_id,commodity_id,utility_account_id FROM {self.qschema}.dim_meter WHERE meter_id={self._sql_string(meter)}")
                if not checks.empty:
                    m = checks.iloc[0]
                    if str(m["property_id"]) != str(values.get("property_id")) or str(m["commodity_id"]) != str(values.get("commodity_id")):
                        raise DataAccessError("Reading property and commodity must match the selected meter.")
                    if values.get("utility_account_id") and pd.notna(m["utility_account_id"]) and str(m["utility_account_id"]) != str(values["utility_account_id"]):
                        raise DataAccessError("The reading utility account must match the selected meter's account.")
        elif table == "bridge_meter_contract":
            meter = values.get("meter_id")
            contract = values.get("contract_id")
            if meter and contract:
                check = self.query(f"""
                    SELECT m.property_id,m.commodity_id,c.commodity_id AS contract_commodity
                    FROM {self.qschema}.dim_meter m CROSS JOIN {self.qschema}.dim_contract c
                    WHERE m.meter_id={self._sql_string(meter)} AND c.contract_id={self._sql_string(contract)}
                """)
                if not check.empty:
                    row = check.iloc[0]
                    if str(row["property_id"]) != str(values.get("property_id")):
                        raise DataAccessError("Meter contract property must match the selected meter's property.")
                    if pd.notna(row["contract_commodity"]) and str(row["commodity_id"]) != str(row["contract_commodity"]):
                        raise DataAccessError("Meter and supplier contract must use the same commodity.")
        elif table == "dim_utility_account":
            prop, commodity, vendor = values.get("property_id"), values.get("commodity_id"), values.get("utility_vendor_id")
            service = values.get("property_service_id")
            if service:
                check = self.query(f"SELECT property_id,commodity_id,utility_vendor_id FROM {self.qschema}.bridge_property_commodity_service WHERE property_service_id={self._sql_string(service)}")
                if not check.empty:
                    row = check.iloc[0]
                    if str(row["property_id"]) != str(prop) or str(row["commodity_id"]) != str(commodity):
                        raise DataAccessError("Utility account property and commodity must match its property service.")
                    if pd.notna(row["utility_vendor_id"]) and str(row["utility_vendor_id"]) != str(vendor):
                        raise DataAccessError("Utility account vendor must match the selected property service.")
            rate_class = values.get("rate_class_id")
            if rate_class:
                check = self.query(f"SELECT commodity_id,utility_vendor_id FROM {self.qschema}.dim_rate_class WHERE rate_class_id={self._sql_string(rate_class)}")
                if not check.empty:
                    row = check.iloc[0]
                    if pd.notna(row["commodity_id"]) and str(row["commodity_id"]) != str(commodity):
                        raise DataAccessError("Utility account commodity must match its rate class.")
                    if pd.notna(row["utility_vendor_id"]) and str(row["utility_vendor_id"]) != str(vendor):
                        raise DataAccessError("Utility account vendor must match its rate class.")
        elif table == "dim_rate_schedule":
            rate_class, commodity, vendor = values.get("rate_class_id"), values.get("commodity_id"), values.get("utility_vendor_id")
            if rate_class:
                check = self.query(f"SELECT commodity_id,utility_vendor_id FROM {self.qschema}.dim_rate_class WHERE rate_class_id={self._sql_string(rate_class)}")
                if not check.empty:
                    row = check.iloc[0]
                    if pd.notna(row["commodity_id"]) and str(row["commodity_id"]) != str(commodity):
                        raise DataAccessError("Rate schedule commodity must match its rate class.")
                    if pd.notna(row["utility_vendor_id"]) and str(row["utility_vendor_id"]) != str(vendor):
                        raise DataAccessError("Rate schedule utility vendor must match its rate class.")
        elif table == "fact_energy_bill":
            account = values.get("utility_account_id")
            if account:
                check = self.query(f"SELECT property_id,utility_vendor_id FROM {self.qschema}.dim_utility_account WHERE utility_account_id={self._sql_string(account)}")
                if not check.empty:
                    row = check.iloc[0]
                    if str(row["property_id"]) != str(values.get("property_id")):
                        raise DataAccessError("Bill property must match the selected utility account.")
                    if str(row["utility_vendor_id"]) != str(values.get("vendor_id")):
                        raise DataAccessError("Bill vendor must match the selected utility account's utility vendor.")
        elif table == "fact_purchase_order_line":
            po = values.get("purchase_order_id")
            if po:
                check = self.query(f"SELECT property_id FROM {self.qschema}.fact_purchase_order WHERE purchase_order_id={self._sql_string(po)}")
                if not check.empty and pd.notna(check.iloc[0]["property_id"]) and str(check.iloc[0]["property_id"]) != str(values.get("property_id")):
                    raise DataAccessError("Purchase order line property must match its purchase order.")
        elif table == "bridge_property_contract":
            prop, contract = values.get("property_id"), values.get("contract_id")
            end_date = values.get("effective_end_date")
            if prop and contract:
                check = self.query(f"SELECT commodity_id FROM {self.qschema}.dim_contract WHERE contract_id={self._sql_string(contract)}")
                if not check.empty and pd.notna(check.iloc[0]["commodity_id"]) and end_date:
                    conflict = self.query(f"""
                        SELECT COUNT(*) AS n
                        FROM {self.qschema}.bridge_meter_contract mb
                        JOIN {self.qschema}.dim_meter m ON mb.meter_id=m.meter_id
                        WHERE mb.property_id={self._sql_string(prop)}
                          AND m.commodity_id={self._sql_string(check.iloc[0]["commodity_id"])}
                          AND mb.effective_end_date > CAST({self._sql_string(str(end_date))} AS DATE)
                    """)
                    if int(conflict.iloc[0]["n"]) > 0:
                        raise DataAccessError("Property contract end date cannot be earlier than a linked meter contract end date. Update the meter contract first.")
        elif table == "fact_energy_bill_line":
            bill, meter = values.get("energy_bill_id"), values.get("meter_id")
            if bill:
                check = self.query(f"SELECT property_id FROM {self.qschema}.fact_energy_bill WHERE energy_bill_id={self._sql_string(bill)}")
                if not check.empty and str(check.iloc[0]["property_id"]) != str(values.get("property_id")):
                    raise DataAccessError("Bill line property must match its bill header.")
            if meter:
                check = self.query(f"SELECT property_id,commodity_id FROM {self.qschema}.dim_meter WHERE meter_id={self._sql_string(meter)}")
                if not check.empty:
                    if str(check.iloc[0]["property_id"]) != str(values.get("property_id")):
                        raise DataAccessError("Bill line meter must belong to the selected property.")
                    if values.get("commodity_id") and str(check.iloc[0]["commodity_id"]) != str(values.get("commodity_id")):
                        raise DataAccessError("Bill line commodity must match the selected meter.")
        elif table == "fact_vendor_invoice_line":
            invoice, po_line = values.get("vendor_invoice_id"), values.get("purchase_order_line_id")
            if invoice and po_line:
                check = self.query(f"""
                    SELECT vi.purchase_order_id,pol.purchase_order_id AS line_po
                    FROM {self.qschema}.fact_vendor_invoice vi
                    CROSS JOIN {self.qschema}.fact_purchase_order_line pol
                    WHERE vi.vendor_invoice_id={self._sql_string(invoice)}
                      AND pol.purchase_order_line_id={self._sql_string(po_line)}
                """)
                if not check.empty and pd.notna(check.iloc[0]["purchase_order_id"]) and str(check.iloc[0]["purchase_order_id"]) != str(check.iloc[0]["line_po"]):
                    raise DataAccessError("Invoice line must belong to the purchase order linked to the selected invoice.")
        elif table == "fact_vendor_invoice":
            po = values.get("purchase_order_id")
            if po:
                check = self.query(f"SELECT vendor_id,property_id,contract_id FROM {self.qschema}.fact_purchase_order WHERE purchase_order_id={self._sql_string(po)}")
                if not check.empty:
                    row = check.iloc[0]
                    if str(row["vendor_id"]) != str(values.get("vendor_id")):
                        raise DataAccessError("Invoice vendor must match the purchase order vendor.")
                    if pd.notna(row["property_id"]) and str(row["property_id"]) != str(values.get("property_id")):
                        raise DataAccessError("Invoice property must match the purchase order property.")
        elif table == "fact_vendor_payment":
            invoice = values.get("vendor_invoice_id")
            if invoice:
                check = self.query(f"SELECT vendor_id,property_id FROM {self.qschema}.fact_vendor_invoice WHERE vendor_invoice_id={self._sql_string(invoice)}")
                if not check.empty:
                    row = check.iloc[0]
                    if str(row["vendor_id"]) != str(values.get("vendor_id")):
                        raise DataAccessError("Payment vendor must match the selected invoice vendor.")
                    if pd.notna(row["property_id"]) and str(row["property_id"]) != str(values.get("property_id")):
                        raise DataAccessError("Payment property must match the selected invoice property.")

        for date_col in ("effective_start_date","contract_start_date","account_open_date","bill_period_start","invoice_date","order_date","reading_start_ts","reading_date"):
            end_col = {"effective_start_date":"effective_end_date","contract_start_date":"contract_end_date",
                       "account_open_date":"account_close_date","bill_period_start":"bill_period_end",
                       "invoice_date":"due_date","order_date":"requested_delivery_date","reading_start_ts":"reading_end_ts",
                       "reading_date":None}.get(date_col)
            if date_col in values and end_col and values.get(end_col) and values[date_col] and str(values[end_col]) < str(values[date_col]):
                raise DataAccessError(f"{end_col} cannot be earlier than {date_col}.")
        if record_id is None:
            key_value = values.get(key)
            if not key_value:
                import uuid
                key_value = f"{entity[:4].upper()}-{uuid.uuid4().hex[:16].upper()}"
            values[key] = key_value
            insert_cols = list(values.keys())
            literals = [self._crud_literal(values[c], known[c]) for c in insert_cols]
            self.execute(f"INSERT INTO {self.qschema}.{table} ({','.join(insert_cols)}) VALUES ({','.join(literals)})")
            return str(key_value)
        else:
            assignments = [f"{c}={self._crud_literal(v,known[c])}" for c,v in values.items()]
            if "updated_at" in known:
                assignments.append("updated_at=current_timestamp()")
            self.execute(f"UPDATE {self.qschema}.{table} SET {','.join(assignments)} WHERE {key}={self._sql_string(record_id)}")
            return str(record_id)

    def crud_delete(self, entity, record_id):
        table, key = self.crud_table(entity)
        checks = self.CRUD_CHILDREN.get(table, [])
        for child, fk in checks:
            result = self.query(f"SELECT COUNT(*) AS n FROM {self.qschema}.{child} WHERE {fk}={self._sql_string(record_id)}")
            if not result.empty and int(result.iloc[0]["n"]) > 0:
                raise DataAccessError(
                    f"Cannot delete this {table} record because {int(result.iloc[0]['n'])} related records exist in {child}. "
                    "Remove or reassign those related records first."
                )
        self.execute(f"DELETE FROM {self.qschema}.{table} WHERE {key}={self._sql_string(record_id)}")
        return True

    def property_meter_contract_data(self,property_id):
        q=self.qschema; pid=self._sql_string(property_id)
        return self.query(f"""
            SELECT p.property_name,m.meter_id,m.meter_number,m.meter_name,
                   co.commodity_name,c.contract_id,c.contract_number,c.contract_name,
                   v.vendor_name AS supplier_name,
                   b.effective_start_date AS contract_start_date,
                   b.effective_end_date AS contract_end_date,
                   datediff(b.effective_end_date,b.effective_start_date)+1 AS contract_duration_days,
                   datediff(b.effective_end_date,current_date()) AS days_remaining,
                   CASE
                     WHEN b.effective_start_date > current_date() THEN 'Upcoming'
                     WHEN b.effective_end_date < current_date() THEN 'Expired'
                     WHEN datediff(b.effective_end_date,current_date()) <= 90 THEN 'Expiring Soon'
                     ELSE 'Active'
                   END AS duration_status,
                   c.auto_renewal_flag,c.renewal_notice_days,c.termination_notice_days,
                   c.pricing_type,c.currency_code,c.estimated_annual_value,
                   b.allocation_pct
            FROM {q}.bridge_meter_contract b
            JOIN {q}.dim_property p ON b.property_id=p.property_id
            JOIN {q}.dim_meter m ON b.meter_id=m.meter_id
            JOIN {q}.dim_contract c ON b.contract_id=c.contract_id
            LEFT JOIN {q}.dim_commodity co ON m.commodity_id=co.commodity_id
            LEFT JOIN {q}.dim_vendor v ON c.supplier_vendor_id=v.vendor_id
            WHERE b.property_id={pid}
            ORDER BY m.meter_number,b.effective_end_date
        """)
