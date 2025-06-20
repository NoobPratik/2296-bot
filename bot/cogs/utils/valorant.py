from discord import Embed


RANKS = {'UNRANKED': 'https://media.valorant-api.com/competitivetiers/03621f52-342b-cf4e-4f86-9350a49c6d04/0/largeicon.png', 'IRON 1': 'https://media.valorant-api.com/competitivetiers/03621f52-342b-cf4e-4f86-9350a49c6d04/3/largeicon.png', 'IRON 2': 'https://media.valorant-api.com/competitivetiers/03621f52-342b-cf4e-4f86-9350a49c6d04/4/largeicon.png', 'IRON 3': 'https://media.valorant-api.com/competitivetiers/03621f52-342b-cf4e-4f86-9350a49c6d04/5/largeicon.png', 'BRONZE 1': 'https://media.valorant-api.com/competitivetiers/03621f52-342b-cf4e-4f86-9350a49c6d04/6/largeicon.png', 'BRONZE 2': 'https://media.valorant-api.com/competitivetiers/03621f52-342b-cf4e-4f86-9350a49c6d04/7/largeicon.png', 'BRONZE 3': 'https://media.valorant-api.com/competitivetiers/03621f52-342b-cf4e-4f86-9350a49c6d04/8/largeicon.png', 'SILVER 1': 'https://media.valorant-api.com/competitivetiers/03621f52-342b-cf4e-4f86-9350a49c6d04/9/largeicon.png', 'SILVER 2': 'https://media.valorant-api.com/competitivetiers/03621f52-342b-cf4e-4f86-9350a49c6d04/10/largeicon.png', 'SILVER 3': 'https://media.valorant-api.com/competitivetiers/03621f52-342b-cf4e-4f86-9350a49c6d04/11/largeicon.png', 'GOLD 1': 'https://media.valorant-api.com/competitivetiers/03621f52-342b-cf4e-4f86-9350a49c6d04/12/largeicon.png', 'GOLD 2': 'https://media.valorant-api.com/competitivetiers/03621f52-342b-cf4e-4f86-9350a49c6d04/13/largeicon.png', 'GOLD 3': 'https://media.valorant-api.com/competitivetiers/03621f52-342b-cf4e-4f86-9350a49c6d04/14/largeicon.png', 'PLATINUM 1': 'https://media.valorant-api.com/competitivetiers/03621f52-342b-cf4e-4f86-9350a49c6d04/15/largeicon.png',
            'PLATINUM 2': 'https://media.valorant-api.com/competitivetiers/03621f52-342b-cf4e-4f86-9350a49c6d04/16/largeicon.png', 'PLATINUM 3': 'https://media.valorant-api.com/competitivetiers/03621f52-342b-cf4e-4f86-9350a49c6d04/17/largeicon.png', 'DIAMOND 1': 'https://media.valorant-api.com/competitivetiers/03621f52-342b-cf4e-4f86-9350a49c6d04/18/largeicon.png', 'DIAMOND 2': 'https://media.valorant-api.com/competitivetiers/03621f52-342b-cf4e-4f86-9350a49c6d04/19/largeicon.png', 'DIAMOND 3': 'https://media.valorant-api.com/competitivetiers/03621f52-342b-cf4e-4f86-9350a49c6d04/20/largeicon.png', 'IMMORTAL 1': 'https://media.valorant-api.com/competitivetiers/03621f52-342b-cf4e-4f86-9350a49c6d04/24/largeicon.png', 'IMMORTAL 2': 'https://media.valorant-api.com/competitivetiers/03621f52-342b-cf4e-4f86-9350a49c6d04/25/largeicon.png', 'IMMORTAL 3': 'https://media.valorant-api.com/competitivetiers/03621f52-342b-cf4e-4f86-9350a49c6d04/26/largeicon.png', 'RADIANT': 'https://media.valorant-api.com/competitivetiers/03621f52-342b-cf4e-4f86-9350a49c6d04/27/largeicon.png', 'IMMORTAL': 'https://media.valorant-api.com/competitivetiers/23eb970e-6408-bc0b-3f20-d8fb0e0354ea/21/largeicon.png', 'ASCENDANT 1': 'https://media.valorant-api.com/competitivetiers/03621f52-342b-cf4e-4f86-9350a49c6d04/21/largeicon.png', 'ASCENDANT 2': 'https://media.valorant-api.com/competitivetiers/03621f52-342b-cf4e-4f86-9350a49c6d04/22/largeicon.png', 'ASCENDANT 3': 'https://media.valorant-api.com/competitivetiers/03621f52-342b-cf4e-4f86-9350a49c6d04/23/largeicon.png'}
RANK_COLORS = {
    "IRON 1": 0x3e3e3e,
    "IRON 2": 0x4b4b4b,
    "IRON 3": 0x5a5a5a,

    "BRONZE 1": 0x976b30,
    "BRONZE 2": 0xa7773a,
    "BRONZE 3": 0xb88344,

    "SILVER 1": 0xbcbcbc,
    "SILVER 2": 0xc8c8c8,
    "SILVER 3": 0xd4d4d4,

    "GOLD 1": 0xe4b93b,
    "GOLD 2": 0xeac24d,
    "GOLD 3": 0xf0cb5f,

    "PLATINUM 1": 0x38b9ad,
    "PLATINUM 2": 0x4bc8bc,
    "PLATINUM 3": 0x5fd7cc,

    "DIAMOND 1": 0xb65aff,
    "DIAMOND 2": 0xc273ff,
    "DIAMOND 3": 0xcd8cff,

    "ASCENDANT 1": 0x4fd161,
    "ASCENDANT 2": 0x62dc74,
    "ASCENDANT 3": 0x75e786,

    "IMMORTAL 1": 0xbd2fae,
    "IMMORTAL 2": 0xc748b6,
    "IMMORTAL 3": 0xd161be,

    "RADIANT": 0xffff64
}
MAP_ICONS = {
    "Ascent": "https://media.valorant-api.com/maps/7eaecc1b-4337-bbf6-6ab9-04b8f06b3319/listviewicon.png",
    "Split": "https://media.valorant-api.com/maps/d960549e-485c-e861-8d71-aa9d1aed12a2/listviewicon.png",
    "Fracture": "https://media.valorant-api.com/maps/b529448b-4d60-346e-e89e-00a4c527a405/listviewicon.png",
    "Bind": "https://media.valorant-api.com/maps/2c9d57ec-4431-9c5e-2939-8f9ef6dd5cba/listviewicon.png",
    "Breeze": "https://media.valorant-api.com/maps/2fb9a4fd-47b8-4e7d-a969-74b4046ebd53/listviewicon.png",
    "District": "https://media.valorant-api.com/maps/690b3ed2-4dff-945b-8223-6da834e30d24/listviewicon.png",
    "Kasbah": "https://media.valorant-api.com/maps/12452a9d-48c3-0b02-e7eb-0381c3520404/listviewicon.png",
    "Drift": "https://media.valorant-api.com/maps/2c09d728-42d5-30d8-43dc-96a05cc7ee9d/listviewicon.png",
    "Glitch": "https://media.valorant-api.com/maps/d6336a5a-428f-c591-98db-c8a291159134/listviewicon.png",
    "Piazza": "https://media.valorant-api.com/maps/de28aa9b-4cbe-1003-320e-6cb3ec309557/listviewicon.png",
    "Abyss": "https://media.valorant-api.com/maps/224b0a95-48b9-f703-1bd8-67aca101a61f/listviewicon.png",
    "Lotus": "https://media.valorant-api.com/maps/2fe4ed3a-450a-948b-6d6b-e89a78e680a9/listviewicon.png",
    "Sunset": "https://media.valorant-api.com/maps/92584fbe-486a-b1b2-9faa-39b0f486b498/listviewicon.png",
    "Basic Training": "https://media.valorant-api.com/maps/1f10dab3-4294-3827-fa35-c2aa00213cf3/listviewicon.png",
    "Pearl": "https://media.valorant-api.com/maps/fd267378-4d1d-484f-ff52-77821ed10dc2/listviewicon.png",
    "Icebox": "https://media.valorant-api.com/maps/e2ad5c54-4114-a870-9641-8ea21279579a/listviewicon.png",
    "The Range": "https://media.valorant-api.com/maps/5914d1e0-40c4-cfdd-6b88-eba06347686c/listviewicon.png",
    "Haven": "https://media.valorant-api.com/maps/2bee0dc9-4ffe-519b-1cbd-7fbe763a6047/listviewicon.png"
}
AGENT_ICONS = {
    "Gekko": "https://media.valorant-api.com/agents/e370fa57-4757-3604-3648-499e1f642d3f/killfeedportrait.png",
    "Fade": "https://media.valorant-api.com/agents/dade69b4-4f5a-8528-247b-219e5a1facd6/killfeedportrait.png",
    "Breach": "https://media.valorant-api.com/agents/5f8d3a7f-467b-97f3-062c-13acf203c006/killfeedportrait.png",
    "Deadlock": "https://media.valorant-api.com/agents/cc8b64c8-4b25-4ff9-6e7f-37b4da43d235/killfeedportrait.png",
    "Tejo": "https://media.valorant-api.com/agents/b444168c-4e35-8076-db47-ef9bf368f384/killfeedportrait.png",
    "Raze": "https://media.valorant-api.com/agents/f94c3b30-42be-e959-889c-5aa313dba261/killfeedportrait.png",
    "Chamber": "https://media.valorant-api.com/agents/22697a3d-45bf-8dd7-4fec-84a9e28c69d7/killfeedportrait.png",
    "KAY/O": "https://media.valorant-api.com/agents/601dbbe7-43ce-be57-2a40-4abd24953621/killfeedportrait.png",
    "Skye": "https://media.valorant-api.com/agents/6f2a04ca-43e0-be17-7f36-b3908627744d/killfeedportrait.png",
    "Cypher": "https://media.valorant-api.com/agents/117ed9e3-49f3-6512-3ccf-0cada7e3823b/killfeedportrait.png",
    "Sova": "https://media.valorant-api.com/agents/320b2a48-4d9b-a075-30f1-1f93a9b638fa/killfeedportrait.png",
    "Killjoy": "https://media.valorant-api.com/agents/1e58de9c-4950-5125-93e9-a0aee9f98746/killfeedportrait.png",
    "Harbor": "https://media.valorant-api.com/agents/95b78ed7-4637-86d9-7e41-71ba8c293152/killfeedportrait.png",
    "Vyse": "https://media.valorant-api.com/agents/efba5359-4016-a1e5-7626-b1ae76895940/killfeedportrait.png",
    "Viper": "https://media.valorant-api.com/agents/707eab51-4836-f488-046a-cda6bf494859/killfeedportrait.png",
    "Phoenix": "https://media.valorant-api.com/agents/eb93336a-449b-9c1b-0a54-a891f7921d69/killfeedportrait.png",
    "Astra": "https://media.valorant-api.com/agents/41fb69c1-4189-7b37-f117-bcaf1e96f1bf/killfeedportrait.png",
    "Brimstone": "https://media.valorant-api.com/agents/9f0d8ba9-4140-b941-57d3-a7ad57c6b417/killfeedportrait.png",
    "Iso": "https://media.valorant-api.com/agents/0e38b510-41a8-5780-5e8f-568b2a4f2d6c/killfeedportrait.png",
    "Clove": "https://media.valorant-api.com/agents/1dbf2edd-4729-0984-3115-daa5eed44993/killfeedportrait.png",
    "Neon": "https://media.valorant-api.com/agents/bb2a4828-46eb-8cd1-e765-15848195d751/killfeedportrait.png",
    "Yoru": "https://media.valorant-api.com/agents/7f94d92c-4234-0a36-9646-3a87eb8b5c89/killfeedportrait.png",
    "Waylay": "https://media.valorant-api.com/agents/df1cb487-4902-002e-5c17-d28e83e78588/killfeedportrait.png",
    "Sage": "https://media.valorant-api.com/agents/569fdd95-4d10-43ab-ca70-79becc718b46/killfeedportrait.png",
    "Reyna": "https://media.valorant-api.com/agents/a3bfb853-43b2-7238-a4f1-ad90e9e46bcc/killfeedportrait.png",
    "Omen": "https://media.valorant-api.com/agents/8e253930-4c05-31dd-1b6c-968525494517/killfeedportrait.png",
    "Jett": "https://media.valorant-api.com/agents/add6443a-41bd-e414-f6ad-e58d267f4e95/killfeedportrait.png"
}


def build_rank_embed(name, icon_url, rank_icon, current_rank, rr, elo, rr_change, peak_rank):
    embed = Embed()
    embed.set_author(name=name, icon_url=icon_url)
    embed.set_thumbnail(url=rank_icon)
    embed.title = f'{current_rank} ({rr} RR)'
    embed.description = f'RR last game: `{rr_change}`\nElo: `{elo}`'
    embed.set_footer(text=f'Peak: {peak_rank}')
    embed.color = 0x7289DA
    return embed

def build_match_embed(name, card_icon, agent, map_name, win, score, players):
    embed = Embed(
        title=("Victory" if win else "Defeat") + f" ({score})",
        color=0x00FF00 if win else 0xFF0000
    )
    embed.set_author(name=name, icon_url=card_icon)
    embed.set_image(url=f"https://media.valorant-api.com/maps/{map_name.lower().replace(' ', '-')}/splash.png")
    embed.set_thumbnail(url=f"https://media.valorant-api.com/agents/{agent.lower()}/displayicon.png")

    for team in ["Red", "Blue"]:
        team_players = [p for p in players if p["team"].lower() == team.lower()]
        value = "\n".join(
            f"`{p['name']} | {p['stats']['kills']}/{p['stats']['deaths']}/{p['stats']['assists']} | {p.get('currenttier_patched', 'Unranked')}`"
            for p in team_players
        )
        embed.add_field(name=f"`{team} Team`", value=value, inline=False)

    return embed

def get_match_data(match, name):
    metadata = match.get('metadata', {})
    players = match.get('players', {}).get('all_players', [])
    map_name = metadata.get('map', 'Unknown')
    rounds = match.get('teams', {})
    blue_score = rounds.get('blue', {}).get('rounds_won', 0)
    red_score = rounds.get('red', {}).get('rounds_won', 0)
    score = f"{blue_score} - {red_score}"
    win = (match['teams'][players[0]['team'].lower()]['has_won'])
    player = next((p for p in players if p['name'] == name), players[0])
    agent = player.get('character', 'Unknown')

    return { "agent": agent, "map_name": map_name, "win": win, "score": score, "players": players}