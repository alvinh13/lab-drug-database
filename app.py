from flask import Flask, render_template, request, jsonify
from sqlalchemy import create_engine, text

app = Flask(__name__)

DB_PATH = "drugage.db"
TABLE = "tox_data"

engine = create_engine(f"sqlite:///{DB_PATH}", future=True)


@app.get("/")
def home():
    return render_template("index.html")


@app.get("/api/tox")
def api_tox():
    draw = int(request.args.get("draw", 1))
    start = int(request.args.get("start", 0))
    length = int(request.args.get("length", 25))
    search_value = request.args.get("search[value]", "").strip()

    chemical_name = request.args.get("chemical_name", "").strip()
    class_of_chemical = request.args.get("class_of_chemical", "").strip()
    exposure_time = request.args.get("exposure_time", "").strip()
    media_used = request.args.get("media_used", "").strip()
    hardware = request.args.get("hardware", "").strip()
    source = request.args.get("source", "").strip()

    lc50_min = request.args.get("lc50_min", None)
    lc50_max = request.args.get("lc50_max", None)

    cols = [
        "chemical_name",
        "class_of_chemical",
        "lc50_mm",
        "exposure_time",
        "media_used",
        "sample_size",
        "conc_range_mm",
        "hardware",
        "source",
        "source_link",
    ]

    where = []
    params = {}

    def add_like(col, value, key):
        if value:
            where.append(f"{col} LIKE :{key}")
            params[key] = f"%{value}%"

    add_like("chemical_name", chemical_name, "chemical_name")
    add_like("class_of_chemical", class_of_chemical, "class_of_chemical")
    add_like("exposure_time", exposure_time, "exposure_time")
    add_like("media_used", media_used, "media_used")
    add_like("hardware", hardware, "hardware")
    add_like("source", source, "source")

    if search_value:
        params["q"] = f"%{search_value}%"
        where.append("""
            (
              chemical_name LIKE :q OR
              class_of_chemical LIKE :q OR
              exposure_time LIKE :q OR
              media_used LIKE :q OR
              hardware LIKE :q OR
              source LIKE :q
            )
        """)

    def add_between(col, lo, hi, lo_key, hi_key):
        try:
            if lo is not None and hi is not None and lo != "" and hi != "":
                where.append(f"{col} BETWEEN :{lo_key} AND :{hi_key}")
                params[lo_key] = float(lo)
                params[hi_key] = float(hi)
        except ValueError:
            pass

    add_between("lc50_mm", lc50_min, lc50_max, "lc50_min", "lc50_max")

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    order_col_index = int(request.args.get("order[0][column]", 0))
    order_dir = request.args.get("order[0][dir]", "asc").lower()
    if order_dir not in ("asc", "desc"):
        order_dir = "asc"
    order_col = cols[order_col_index] if 0 <= order_col_index < len(cols) else cols[0]

    total_sql = text(f"SELECT COUNT(*) FROM {TABLE}")
    filtered_sql = text(f"SELECT COUNT(*) FROM {TABLE} {where_sql}")
    data_sql = text(f"""
        SELECT {", ".join(cols)}
        FROM {TABLE}
        {where_sql}
        ORDER BY {order_col} {order_dir}
        LIMIT :limit OFFSET :offset
    """)

    params["limit"] = length
    params["offset"] = start

    with engine.connect() as conn:
        records_total = conn.execute(total_sql).scalar_one()
        records_filtered = conn.execute(filtered_sql, params).scalar_one()
        rows = conn.execute(data_sql, params).fetchall()

    data = [list(r) for r in rows]

    return jsonify({
        "draw": draw,
        "recordsTotal": records_total,
        "recordsFiltered": records_filtered,
        "data": data
    })


@app.get("/api/summary")
def api_summary():
    with engine.connect() as conn:
        total_rows = conn.execute(text(f"SELECT COUNT(*) FROM {TABLE}")).scalar_one()
        total_chemicals = conn.execute(
            text(f"SELECT COUNT(DISTINCT chemical_name) FROM {TABLE}")
        ).scalar_one()

        class_rows = conn.execute(text(f"""
            SELECT class_of_chemical, COUNT(*) as n
            FROM {TABLE}
            WHERE class_of_chemical IS NOT NULL AND TRIM(class_of_chemical) != ''
            GROUP BY class_of_chemical
            ORDER BY n DESC
        """)).fetchall()

    class_counts = [{"class": r[0], "count": r[1]} for r in class_rows]

    return jsonify({
        "total_rows": total_rows,
        "total_unique_chemicals": total_chemicals,
        "class_counts": class_counts
    })


@app.get("/api/options")
def api_options():
    def get_distinct(col):
        with engine.connect() as conn:
            rows = conn.execute(text(f"""
                SELECT DISTINCT {col}
                FROM {TABLE}
                WHERE {col} IS NOT NULL AND TRIM({col}) != ''
                ORDER BY {col} ASC
            """)).fetchall()
        return [r[0] for r in rows]

    return jsonify({
        "class_of_chemical": get_distinct("class_of_chemical"),
        "exposure_time": get_distinct("exposure_time"),
        "media_used": get_distinct("media_used"),
        "hardware": get_distinct("hardware"),
    })

@app.get("/api/ranges")
def api_ranges():
    with engine.connect() as conn:
        row = conn.execute(text(f"""
            SELECT
              MIN(lc50_mm) as min_lc50,
              MAX(lc50_mm) as max_lc50
            FROM {TABLE}
            WHERE lc50_mm IS NOT NULL
        """)).fetchone()

    min_lc50 = row[0] if row and row[0] is not None else 0
    max_lc50 = row[1] if row and row[1] is not None else 0

    return jsonify({
        "lc50_mm": {
            "min": float(min_lc50),
            "max": float(max_lc50)
        }
    })

if __name__ == "__main__":
    app.run(debug=True)