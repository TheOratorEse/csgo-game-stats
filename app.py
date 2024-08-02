import os
from flask import Flask, jsonify, request #using Flask framework for web interface
import requests
from datetime import datetime, timedelta
import numpy as np

app = Flask(__name__)

# Pandascore API configuration and token
PANDASCORE_API_TOKEN = 'qE-G3OQJ2q_tyOK_uJS-KHDDdcBCpCobJao0W0ry4_r6mbKUJiQ'
PANDASCORE_BASE_URL = 'https://api.pandascore.co'

def get_pandascore_data(endpoint, params=None):
    headers = {'Authorization': f'Bearer {PANDASCORE_API_TOKEN}'}
    response = requests.get(f'{PANDASCORE_BASE_URL}{endpoint}', headers=headers, params=params)
    response.raise_for_status()
    return response.json()

def get_player_stats(player_id):
    try:
        matches = get_pandascore_data(f'/players/{player_id}/matches', {'per_page': 10})
        
        last_10_matches = []
        for match in matches:
            player_stats = next((p for p in match['players'] if str(p['id']) == str(player_id)), None)
            if player_stats:
                last_10_matches.append({
                    "match_id": match['id'],
                    "date": match['begin_at'],
                    "kills": player_stats.get('kills', 0),
                    "assists": player_stats.get('assists', 0),
                    "headshots": player_stats.get('headshots', 0)
                })
        
        num_matches = len(last_10_matches)
        avg_stats = {
            "avg_kills": sum(m['kills'] for m in last_10_matches) / num_matches if num_matches else 0,
            "avg_assists": sum(m['assists'] for m in last_10_matches) / num_matches if num_matches else 0,
            "avg_headshots": sum(m['headshots'] for m in last_10_matches) / num_matches if num_matches else 0
        }
        
        return {
            "last_10_matches": last_10_matches,
            "average_stats": avg_stats
        }
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

@app.route('/api/players', methods=['GET'])
def get_all_players():
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        sort_by = request.args.get('sort_by', 'name')
        order = request.args.get('order', 'asc')
        
        params = {
            'page': page,
            'per_page': per_page,
            'sort': f"{'-' if order == 'desc' else ''}{sort_by}"
        }
        
        players = get_pandascore_data('/players', params)
        
        return jsonify({
            "players": [{
                "id": player['id'],
                "name": player['name'],
                "team": player['current_team']['name'] if player['current_team'] else None
            } for player in players],
            "page": page,
            "per_page": per_page,
            "total": len(players)
        })
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/players/stats', methods=['GET'])
def get_all_players_stats():
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        sort_by = request.args.get('sort_by', 'name')
        order = request.args.get('order', 'asc')
        
        params = {
            'page': page,
            'per_page': per_page,
            'sort': f"{'-' if order == 'desc' else ''}{sort_by}"
        }
        
        players = get_pandascore_data('/players', params)
        
        players_stats = []
        for player in players:
            stats = get_player_stats(player['id'])
            players_stats.append({
                "id": player['id'],
                "name": player['name'],
                "team": player['current_team']['name'] if player['current_team'] else None,
                "stats": stats
            })
        
        return jsonify({
            "players_stats": players_stats,
            "page": page,
            "per_page": per_page,
            "total": len(players_stats)
        })
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/player/<player_id>/stats', methods=['GET'])
def get_single_player_stats(player_id):
    try:
        player_data = get_pandascore_data(f'/players/{player_id}')
        stats = get_player_stats(player_id)
        
        return jsonify({
            "player_id": player_id,
            "name": player_data['name'],
            "team": player_data['current_team']['name'] if player_data['current_team'] else None,
            "last_10_matches": stats['last_10_matches'],
            "average_stats": stats['average_stats']
        })
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 400


@app.route('/api/matches/current', methods=['GET'])
def get_current_matches():
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        params = {
           # 'range[begin_at]': today,
           # 'filter[videogame]': 'cs-go',
           #  'sort': 'begin_at',
           # 'per_page': 100  # Adjust as needed
        }
        
        matches = get_pandascore_data('/csgo/matches', params)
        
        current_matches = [{
            "id": match['id'],
            "league": match['league']['name'],
            "series": match['serie']['full_name'],
            "team1": match['opponents'][0]['opponent']['name'] if match['opponents'] else 'TBD',
            "team2": match['opponents'][1]['opponent']['name'] if len(match['opponents']) > 1 else 'TBD',
            "start_time": match['begin_at'],
            "status": match['status']
        } for match in matches]
        
        return jsonify({
            "current_matches": current_matches,
            "total": len(current_matches)
        })
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/matches/previous', methods=['GET'])
def get_previous_matches():
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        
        params = {
            'filter[videogame]': 'cs-go',
            'filter[status]': 'finished',
            'sort': '-begin_at',
            'page': page,
            'per_page': per_page
        }
        
        matches = get_pandascore_data('/csgo/matches', params)
        
        previous_matches = [{
            "id": match['id'],
            "league": match['league']['name'],
            "series": match['serie']['full_name'],
            "team1": match['opponents'][0]['opponent']['name'] if match['opponents'] else 'Unknown',
            "team2": match['opponents'][1]['opponent']['name'] if len(match['opponents']) > 1 else 'Unknown',
            "score": f"{match['results'][0]['score']}-{match['results'][1]['score']}" if match['results'] else 'N/A',
            "winner": match['winner']['name'] if match['winner'] else 'N/A',
            "start_time": match['begin_at'],
            "end_time": match['end_at']
        } for match in matches]
        
        return jsonify({
            "previous_matches": previous_matches,
            "page": page,
            "per_page": per_page,
            "total": len(previous_matches)
        })
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 400

def get_team_player_stats(team_id):
    try:
        # Fetch team data
        team_data = get_pandascore_data(f'/teams/{team_id}')
        
        # Fetch last 10 matches for the team
        matches = get_pandascore_data(f'/teams/{team_id}/matches', {'per_page': 10})
        
        team_stats = {
            "team_name": team_data.get('name', 'Unknown Team'),
            "players": []
        }
        
        # Check if 'players' key exists and is not None
        if 'players' in team_data and team_data['players']:
            for player in team_data['players']:
                player_stats = {
                    "player_name": player.get('name', 'Unknown Player'),
                    "kills": [],
                    "assists": [],
                    "headshots": []
                }
                
                for match in matches:
                    player_match_stats = next((p for p in match.get('players', []) if p['id'] == player['id']), None)
                    if player_match_stats:
                        player_stats["kills"].append(player_match_stats.get('kills', 0))
                        player_stats["assists"].append(player_match_stats.get('assists', 0))
                        player_stats["headshots"].append(player_match_stats.get('headshots', 0))
                
                # Ensure we have exactly 10 entries for each stat
                for stat in ["kills", "assists", "headshots"]:
                    player_stats[stat] = player_stats[stat][:10]
                    while len(player_stats[stat]) < 10:
                        player_stats[stat].append(0)
                
                team_stats["players"].append(player_stats)
        else:
            # If no players data, add a placeholder
            team_stats["players"].append({
                "player_name": "No Player Data",
                "kills": [0] * 10,
                "assists": [0] * 10,
                "headshots": [0] * 10
            })
        
        return team_stats
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

@app.route('/api/csgo/team_stats', methods=['GET'])
def get_csgo_team_stats():
    try:
        # Fetch all CS:GO teams
        teams = get_pandascore_data('/csgo/teams', {'per_page': 100})  # Adjust per_page as needed
        
        all_team_stats = []
        
        for team in teams:
            team_stats = get_team_player_stats(team['id'])
            if isinstance(team_stats, dict) and 'error' not in team_stats:
                all_team_stats.append(team_stats)
            else:
                print(f"Error fetching stats for team {team['id']}: {team_stats.get('error', 'Unknown error')}")
        
        return jsonify({
            "team_stats": all_team_stats,
            "total_teams": len(all_team_stats)
        })
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

def project_team_stats(team_stats):
    projected_stats = {
        "team_name": team_stats["team_name"],
        "team_projections": {
            "kills": 0,
            "assists": 0,
            "headshots": 0
        },
        "players": []
    }
    
    for player in team_stats["players"]:
        player_projection = {
            "player_name": player["player_name"],
            "projected_kills": 0,
            "projected_assists": 0,
            "projected_headshots": 0
        }
        
        for stat in ["kills", "assists", "headshots"]:
            # Calculate weighted average (more recent matches have higher weight)
            weights = np.linspace(0.5, 1.5, num=10)
            weighted_avg = np.average(player[stat], weights=weights)
            
            # Calculate trend (positive or negative)
            trend = np.polyfit(range(10), player[stat], 1)[0]
            
            # Project next value (weighted average + trend adjustment)
            projected_value = weighted_avg + (trend * 0.5)  # Adjust trend impact as needed
            
            # Ensure projected value is non-negative
            projected_value = max(0, projected_value)
            
            player_projection[f"projected_{stat}"] = round(projected_value, 2)
            projected_stats["team_projections"][stat] += projected_value
        
        projected_stats["players"].append(player_projection)
    
    # Round team projections
    for stat in projected_stats["team_projections"]:
        projected_stats["team_projections"][stat] = round(projected_stats["team_projections"][stat], 2)
    
    return projected_stats

@app.route('/api/csgo/team_stats_projections', methods=['GET'])
def get_csgo_team_stats_projections():
    try:
        # Fetch all CS:GO teams
        teams = get_pandascore_data('/csgo/teams', {'per_page': 100})  # Adjust per_page as needed
        
        all_team_projections = []
        
        for team in teams:
            team_stats = get_team_player_stats(team['id'])
            if 'error' not in team_stats:
                team_projections = project_team_stats(team_stats)
                all_team_projections.append(team_projections)
        
        return jsonify({
            "team_projections": all_team_projections,
            "total_teams": len(all_team_projections)
        })
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 400


if __name__ == '__main__':
    if not PANDASCORE_API_TOKEN:
        raise ValueError("PANDASCORE_API_TOKEN environment variable is not set")
    app.run(debug=True)