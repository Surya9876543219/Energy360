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
        if not state or state == "All India":
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
