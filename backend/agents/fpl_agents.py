from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing import TypedDict, Annotated       
from supabase import create_client 
import requests                            
import os                                   
from dotenv import load_dotenv 


load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
supabase_admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        


class AgentState(TypedDict):
    user_id: str
    gameweek: int
    squad_ids: list
    player_data: list
    analysis: str
    injury_report: str
    recommendations: list



def scout_node(state: AgentState):
    squad = state["squad_ids"]
    response = (requests.get("https://fantasy.premierleague.com/api/bootstrap-static/")).json()
    elements = response.get("elements")
    player_data = [
        {
        "id": element.get("id"),
        "name": element.get("first_name") + " " + element.get("second_name"),
        "total_points": element.get("total_points"),
        "form": element.get("form"),
        "minutes": element.get("minutes"),
        "goals_scored": element.get("goals_scored"),
        "assists": element.get("assists"),
        "clean_sheets": element.get("clean_sheets"),
        "now_cost": element.get("now_cost"),
        "selected_by_percent": element.get("selected_by_percent"),
        "chance_of_playing_next_round": element.get("chance_of_playing_next_round"),
        "news": element.get("news"),
        "yellow_cards": element.get("yellow_cards"),
        "expected_goal_involvements_per_90": element.get("expected_goal_involvements_per_90"),
        "expected_goals_conceded_per_90": element.get("expected_goals_conceded_per_90"),
        "saves_per_90": element.get("saves_per_90"),
        "defcon_per_90": element.get("defensive_contribution_per_90"),
        "position": element.get("element_type")
        }
        for element in elements if element.get("id") in squad
    ]

    return {"player_data" : player_data}



def injury_monitor_node(state: AgentState):
    player_data = state["player_data"]
    injury_risks = [player for player in player_data if player.get("news")]
    yellow_card_risks = [player for player in player_data if player.get("yellow_cards") in [4,9,14,19]]

    prompt = f"""
    You are an FPL injury and risk analyst. Your job is to ONLY report risks — do not make transfer recommendations.
    INJURY/SUSPENSION CONCERNS:
    {injury_risks}
    YELLOW CARD ACCUMULATION RISKS (Accumulating 5 yellow cards means a 1 game suspension. This resets every 5 yellow cards so if you then get another 5 yellow cards, another 1 game ban):
    {yellow_card_risks}
    For each player provide:
    - Their situation
    - Risk level (High/Medium/Low)
    - Why they are flagged
    """

    llm = ChatGroq(model="llama-3.1-8b-instant", api_key=GROQ_API_KEY)
    response = llm.invoke(prompt)

    return {"injury_report" : response.content}




graph = StateGraph(AgentState)
#graph.add_node("supervisor", supervisor_node)
graph.add_node("scout", scout_node)
graph.add_node("injury_monitor", injury_monitor_node)











if __name__ == "__main__":
    test_state = {
        "user_id": "b91086f9-ad6b-4100-88d6-c7892424bce9",
        "gameweek": 36,
        "squad_ids": [253, 256, 6, 411, 417, 261, 242, 21, 47, 449, 430, 691, 1, 151, 178],  # replace with real IDs from your squads table
        "player_data": [],
        "analysis": "",
        "injury_report": "",
        "recommendations": []
    }
    
    # Test scout node first
    state_after_scout = scout_node(test_state)
    #print("Scout output:", state_after_scout)
    
    # Update state with scout output
    test_state.update(state_after_scout)
    
    # Test injury monitor node
    state_after_injury = injury_monitor_node(test_state)
    print("Injury report:", state_after_injury)