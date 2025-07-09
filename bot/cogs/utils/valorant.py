from datetime import datetime
import logging
from zoneinfo import ZoneInfo
from discord import Embed
import requests

log = logging.getLogger(__name__)


def build_rank_embed(name, icon_url, rank_icon, current_rank, rr, elo, rr_change, peak_rank) -> Embed:
    embed = Embed()
    embed.set_author(name=name, icon_url=icon_url)
    embed.set_thumbnail(url=rank_icon)
    embed.title = f'{current_rank} ({rr} RR)'
    embed.description = f'RR last game: `{rr_change}`\nElo: `{elo}`'
    embed.set_footer(text=f'Peak: {peak_rank}')
    embed.color = 0x7289DA
    return embed


def build_match_embed(match_data: dict, player_card: str) -> Embed:
    win = match_data["win"] == match_data["player_team"]

    player_team = match_data["player_team"]
    opponent_team = "Red" if player_team == "Blue" else "Blue"
    player_score = match_data["score"][player_team]
    opponent_score = match_data["score"][opponent_team]

    score_display = f"{player_score} - {opponent_score}"

    title = f"🔺 Victory ({score_display})" if win else f"🔻 Defeat ({score_display})"
    color = 0x00FF00 if win else 0xFF0000
    embed = Embed(title=title, color=color)
    embed.set_footer(text=_get_datetime_footer(match_data))

    player = f"{match_data['player']['name']}#{match_data['player']['tag']}"
    embed.set_author(name=player, icon_url=player_card)

    _map = match_data['map']
    _agent = match_data['agent'].lower()
    embed.set_image(url=MAP_ICONS[_map])
    embed.set_thumbnail(
        url=f"https://media.valorant-api.com/agents/{_agent}/displayicon.png")

    _rounds_played = match_data['score']['Red'] + match_data['score']['Blue']

    teams = ["red_team", "blue_team"]
    team_is_winner = {
        "red_team": match_data["win"] == "Red",
        "blue_team": match_data["win"] == "Blue"
    }

    for idx, team in enumerate(teams):
        players = sorted(
            match_data[team], key=lambda x: x['stats']['score'], reverse=True)
        is_winning_team = team_is_winner[team]

        for i, player in enumerate(players):
            _agent = AGENT_ICONS.get(player['character'], "")
            _rank = RANK_ICONS.get(player['currenttier_patched'].upper(), "")

            kda = f"{player['stats']['kills']}/{player['stats']['deaths']}/{player['stats']['assists']}"
            acs = round(player['stats']['score'] / _rounds_played)
            hs_percent = _get_headshot_percentage(player)

            star = ""
            if i == 0:
                star = "⭐" if is_winning_team else "☆"

            name = f"{_agent} {_rank} {player['name']}#{player['tag']} {star}"
            value = f"`KDA: {kda:<7} | ACS: {acs:<3} | HS: {hs_percent:<5}`"
            embed.add_field(name=name, value=value, inline=False)

        if idx == 0:
            embed.add_field(name="`" + "-" * 39 + "`", value="", inline=False)

    return embed


def _get_headshot_percentage(player: dict) -> str:
    headshots = player['stats']['headshots']
    bodyshots = player['stats']['bodyshots']
    legshots = player['stats']['headshots']

    hs_percent = (headshots / (headshots + bodyshots + legshots)) * 100
    return f'{hs_percent:.1f}%'


def _get_datetime_footer(match_data: dict) -> str:
    try:
        date_str = match_data['datetime'].strftime("%b %-d, %-I:%M %p")
    except ValueError:
        date_str = match_data['datetime'].strftime("%b %#d, %#I:%M %p")

    total_minutes = match_data['game_length'] // 60
    hours = total_minutes // 60
    minutes = total_minutes % 60

    if hours > 0:
        duration_str = f"{hours}h {minutes}m"
    else:
        duration_str = f"{minutes}m"

    _map = match_data['map']
    mode = match_data['game_mode']
    return f"Played on {date_str} ({duration_str})\nMap: {_map} | Mode: {mode}"


def get_match_data(match: dict, puuid: str) -> dict:
    metadata = match.get('metadata', {})
    all_players = match.get('players', {}).get('all_players', [])

    player = next((p for p in all_players if p['puuid'] == puuid), None)
    if not player:
        raise ValueError("Player not found in match")

    player_team = player.get('team')
    red_team = [p for p in all_players if p.get('team') == 'Red']
    blue_team = [p for p in all_players if p.get('team') == 'Blue']

    red_score = match['teams'].get('red', {}).get('rounds_won', 0)
    blue_score = match['teams'].get('blue', {}).get('rounds_won', 0)

    winning_team = 'Red' if match['teams']['red']['has_won'] else 'Blue'

    game_start_str = metadata.get('game_start_patched', None)
    if game_start_str:
        game_datetime = datetime.strptime(
            game_start_str, "%A, %B %d, %Y %I:%M %p").astimezone(ZoneInfo("Asia/Kolkata"))

    return {
        "map": metadata.get("map", "Unknown"),
        "game_mode": metadata.get("mode", "Unknown"),
        "game_length": metadata.get("game_length", 0),
        "datetime": game_datetime or "Unknown",
        "score": {
            "Red": red_score,
            "Blue": blue_score,
        },
        "win": winning_team,
        "player_team": player_team,
        "agent": player.get("character", "Unknown"),
        "red_team": red_team,
        "blue_team": blue_team,
        "player": player,
    }


def _get_puuid(data: dict, name: str) -> str:
    """
    Extracts the PUUID from the provided data based on the player's name.
    """
    players = data.get('data', [{}])[0].get(
        'players', {}).get('all_players', [])
    for player in players:
        if player.get('name', '').lower() == name.lower():
            return player.get('puuid')
    return None


def _get_map_icons() -> dict:
    resp = requests.get("https://valorant-api.com/v1/maps")

    if resp.status_code != 200:
        log.warning('Unable to fetch valorant map icons')
        return {}

    _map_icons = {x['displayName']: x["listViewIcon"]
                  for x in resp.json()['data']}
    return _map_icons


async def _add_default_crosshair(db, user_id) -> None:
    """
    Adds a default crosshair when user doesnt have any crosshairs in database
    """

    query = "INSERT INTO valorant_crosshairs (user_id, label, code) VALUES (%s, %s, %s) AS new"
    await db.execute(query, user_id, "default" ,"0;P;h;0;f;0;0l;4;0o;2;0a;1;0f;0;1b;0")

MAP_ICONS = _get_map_icons()
AGENT_ICONS = {
    'Gekko': '<:gekko:1391997619185782897>',
    'Fade': '<:fade:1391997621706428427>',
    'Breach': '<:breach:1391997626274025634>',
    'Deadlock': '<:deadlock:1391997630468329472>',
    'Tejo': '<:tejo:1391997634037682206>',
    'Raze': '<:raze:1391997636562653184>',
    'Chamber': '<:chamber:1391997640660615198>',
    'Skye': '<:skye:1391997648956817448>',
    'Cypher': '<:cypher:1391997653713158215>',
    'Sova': '<:sova:1391997657995677696>',
    'Killjoy': '<:killjoy:1391997661954965605>',
    'Harbor': '<:harbor:1391997664421216346>',
    'Vyse': '<:vyse:1391997667093119146>',
    'Viper': '<:viper:1391997670750683257>',
    'Phoenix': '<:phoenix:1391997673116270635>',
    'Astra': '<:astra:1391997677008584745>',
    'Brimstone': '<:brimstone:1391997682502996099>',
    'Iso': '<:iso:1391997687049621514>',
    'Clove': '<:clove:1391997690103206038>',
    'Neon': '<:neon:1391997695119458304>',
    'Yoru': '<:yoru:1391997700047765544>',
    'Waylay': '<:waylay:1391997703176851467>',
    'Sage': '<:sage:1391997707484397728>',
    'Reyna': '<:reyna:1391997711716192267>',
    'Omen': '<:omen:1391997715637866517>',
    'Jett': '<:jett:1391997719748415561>',
    'KAY/O': '<kayo:1392007591093342280>'
}
RANK_ICONS = {
    'UNRATED': '<:unranked:1391997725897392258>',
    'IRON 1': '<:iron_1:1391997728204132443>',
    'IRON 2': '<:iron_2:1391997730825568379>',
    'IRON 3': '<:iron_3:1391997733526700082>',
    'BRONZE 1': '<:bronze_1:1391997735766458388>',
    'BRONZE 2': '<:bronze_2:1391997739222437978>',
    'BRONZE 3': '<:bronze_3:1391997744704524368>',
    'SILVER 1': '<:silver_1:1391997746617254003>',
    'SILVER 2': '<:silver_2:1391997750584934461>',
    'SILVER 3': '<:silver_3:1391997754376454225>',
    'GOLD 1': '<:gold_1:1391997756331135028>',
    'GOLD 2': '<:gold_2:1391997759267143821>',
    'GOLD 3': '<:gold_3:1391997763302195311>',
    'PLATINUM 1': '<:platinum_1:1391997766166642768>',
    'PLATINUM 2': '<:platinum_2:1391997769127825430>',
    'PLATINUM 3': '<:platinum_3:1391997772797972522>',
    'DIAMOND 1': '<:diamond_1:1391997775603826749>',
    'DIAMOND 2': '<:diamond_2:1391997778225270826>',
    'DIAMOND 3': '<:diamond_3:1391997781505347646>',
    'ASCENDANT 1': '<:ascendant_1:1391997784025989222>',
    'ASCENDANT 2': '<:ascendant_2:1391997787033309317>',
    'ASCENDANT 3': '<:ascendant_3:1391997789839298691>',
    'IMMORTAL 1': '<:immortal_1:1391997792762855425>',
    'IMMORTAL 2': '<:immortal_2:1391997797225730160>',
    'IMMORTAL 3': '<:immortal_3:1391997799872069633>',
    'RADIANT': '<:radiant:1391997803131306034>'
}
