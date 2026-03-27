from fastapi import FastAPI,Request, BackgroundTasks, HTTPException
from fastapi_sso.sso.google import GoogleSSO
from contextlib import asynccontextmanager
from starlette.middleware.sessions import SessionMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.encoders import jsonable_encoder
from fastapi.staticfiles import StaticFiles 
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
import os, json
from db import pool, app_sql, script_sql
from helpers import LoggedIn
from baseModels import abusive_ips_adapter, AbusiveIp, abusive_country_adapter, AbusiveCountry
from ipaddress import IPv4Address, IPv6Address

# 2. Create the logger object
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP: LogiLogicc before the app starts
    await pool.open() 
    yield # <--- This is where the app runs and serves users
    # SHUTDOWN: Logic after the app stops
    await pool.close()

app = FastAPI(lifespan=lifespan)

# templates.env.filters["tojson"] = lambda obj: json.dumps(obj)

app.add_middleware(
SessionMiddleware,
secret_key=os.getenv("SECRET_HEADER_KEY"),
same_site="lax",  # CSRF protection
https_only=False
)

google_sso = GoogleSSO(
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    redirect_uri="http://localhost:8000/callback", # Make sure this matches Google Console
)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = "0"
    response.headers["Pragma"] = "no-cache"
    return response

# fix this to accept all 
@app.api_route("/login", methods= ["GET", "POST"])
async def login(request : Request):
    request.session.clear()
    
    if request.method == "POST":
        return await google_sso.get_login_redirect()
    
    return templates.TemplateResponse(
       request = request, 
       name = "login.html"
    )

@app.get("/callback")
async def callback(request: Request):
    user : object = await google_sso.verify_and_process(request)
    # add user into the database, if they exist, update their name to match
    # their google_name, google_id is a primary key that is constant for each user 
    sql:str = """ 
              INSERT INTO app_users (google_id, name, email, total_logins) VALUES (%s, %s, %s, 0)
              ON CONFLICT (google_id)
              DO UPDATE
                    SET name = EXCLUDED.name,
                    total_logins = app_users.total_logins + 1
              RETURNING id  """
              # ON CONFLICT ensures only the affected rows are updated
              # Don't have to manually provide a WHERE clause.    
    
    parameters: tuple[str, str, str] = (str(user.id), user.display_name, user.email)
    
    result = await app_sql(sql, parameters)

    # assign database primary_key to session_id
    session_id : int = result[0]["id"]
    request.session["session_id"] : int = session_id
    
    return RedirectResponse("/dashboard", status_code=303)


@app.api_route("/dashboard", methods=['GET','POST'])
async def dashboard(request: Request, session_id: LoggedIn):
    
    sql: str = """ SELECT name, total_logins FROM app_users WHERE "id" = %s
    """

    parameters:tuple[int] = (session_id,)

    result: list[dict[str,any]] = await app_sql(sql, parameters=parameters)

    username: str = result[0]['name']

    del sql

    sql = """SELECT * FROM users_countries_view LIMIT 3"""

    recent_logs = await app_sql(sql)

    return {
        "username" : username,
        "session_id" : session_id,
        "recent_logs" : recent_logs
        } 

@app.api_route("/logout", methods=['GET', 'POST'])
async def logout(request:Request, _ = LoggedIn):
    request.session.clear()

@app.api_route("/heatmap", methods=['GET'])
async def show_global_heatmap(request : Request, session_id = LoggedIn):
    
    sql: str = """ SELECT ip_address, longitude, latitude 
              FROM abusive_ips
              ORDER BY last_reported_at
              LIMIT 10000
    """

    rows_abusive_ips: list[dict[str, IPv4Address | IPv6Address | float]] = await app_sql(sql)
    # use the TypeAdapter to validate 10k rows of data, matches every dict item to the pydantic class (abusive_ips)
    validated_ips: list[AbusiveIp] = abusive_ips_adapter.validate_python(rows_abusive_ips) 
    # turns that validated python dict into json to be sent to frontend
    json_abusive_ips: str = abusive_ips_adapter.dump_json(validated_ips).decode('utf-8')

    # de reference sql value to reuse it again
    del sql
    
    sql: str = """ SELECT COUNT(*) AS attack_count, country_code FROM top_countries GROUP BY country_code
    """

    # get the countries grouped by how many attacks happened
    abusive_countries: list[dict[str, str | int ]] = await app_sql(sql)

    # pass the list of abusive countries to rust so it serializes it based on the pydantic model
    validated_abusive_countries: list[AbusiveCountry] = abusive_country_adapter.validate_python(abusive_countries)

    # dump it to json and parse it to frontend
    json_abusive_countries: str = abusive_country_adapter.dump_json(validated_abusive_countries).decode('utf-8')

    return {
            "session_id" : session_id,
            "data": json_abusive_ips,
            "data_countries": json_abusive_countries
        }


