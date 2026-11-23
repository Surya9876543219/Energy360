import os
import re
from datetime import date
import pandas as pd

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

    def extend_contract_link(self,scope,link_id,new_end_date):
        q=self.qschema; lid=self._sql_string(link_id)
        end=self._sql_string(str(new_end_date))
        if scope == "Meter":
            property_end=self.property_contract_end_date_for_meter(link_id)
            if property_end is None:
                raise DataAccessError(
                    "This meter has no matching property-level contract for its commodity. "
                    "Create or extend the property contract before extending the meter contract."
                )
            if new_end_date > property_end:
                raise DataAccessError(
                    f"Meter contract end date cannot be later than the property contract end date "
                    f"({property_end}). Extend the property contract first."
                )
        table="bridge_property_contract" if scope == "Property" else "bridge_meter_contract"
        key="property_contract_id" if scope == "Property" else "meter_contract_id"
        self.execute(f"""
            UPDATE {q}.{table}
            SET effective_end_date=CAST({end} AS DATE)
            WHERE {key}={lid}
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
