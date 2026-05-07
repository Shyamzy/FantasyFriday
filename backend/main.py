from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
import requests
from dotenv import load_dotenv
import os

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
supabase_admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

app = FastAPI(title="FantasyFriday API")

# This allows your React frontend to talk to FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "FantasyIQ API is running"}


@app.get("/gameweek/")
def get_gameweek():
    response = (requests.get("https://fantasy.premierleague.com/api/bootstrap-static/")).json()
    events = response.get("events")
    for event in events:
        if event.get("is_current") == True:
            return {"gameweek": event.get("id")}
    raise HTTPException(status_code=404, detail="Gameweek not found")


@app.get("/squad/{user_id}/")
def get_squad(user_id: str):
    try:
        gameweek = get_gameweek()
        squad = supabase_admin.table("squads").select("*").eq("user_id" , user_id).eq("gameweek", gameweek.get("gameweek")).execute()
        if not squad.data:
                raise HTTPException(status_code=404, detail="No squad found")
        return {"squad" : squad.data}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/import-squad/")
def import_squad(user_id: str, fpl_team_id: int):
    try:
        gameweek = get_gameweek()

        response = (requests.get(f"https://fantasy.premierleague.com/api/entry/{fpl_team_id}/event/{gameweek.get('gameweek')}/picks/")).json()
        squad = response.get("picks")
        if not squad:
            raise HTTPException(status_code=404, detail="No squad found for this FPL team")

        position_map = {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}

        supabase_admin.table("squads").delete().eq("user_id", user_id).eq("gameweek", gameweek.get("gameweek")).execute()

        squad_list = [{
            "user_id" : user_id,
            "player_fpl_id" : player.get("element"),
            "position" : position_map.get(player.get("element_type")),
            "is_captain" : player.get("is_captain"),
            "is_vice_captain" : player.get("is_vice_captain"),
            "gameweek" : gameweek.get("gameweek")
            } for player in squad]
        supabase_admin.table("squads").insert(squad_list).execute()

        return {"message": "success"} 
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    